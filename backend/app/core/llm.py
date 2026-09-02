"""LLM 调用模块 — 支持本地/API/离线Mock三种模式"""
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, AsyncGenerator, Optional

import httpx
from loguru import logger

from app.config import settings
from app.core.tools import amap_tools
from app.core.locales import language_instruction, matches_target_language, message, normalize_locale

LLM_AVAILABLE = False
try:
    from openai import AsyncOpenAI
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("openai 未安装，使用内置应答模式")


def _create_client():
    # 分项 timeout 只是 HTTP 防护；请求总预算由 generate_response 统一控制。
    total = max(1.0, float(settings.llm_timeout_seconds))
    timeout = httpx.Timeout(
        connect=min(5.0, total),
        read=min(40.0, total),
        write=min(10.0, total),
        pool=min(5.0, total),
    )
    if settings.llm_provider == "deepseek_api":
        return AsyncOpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com/v1", timeout=timeout, max_retries=0)
    return AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=timeout, max_retries=0)


_client = None


class LLMGenerationError(RuntimeError):
    """LLM 客户端不可用或生成失败。"""

    def __init__(self, message: str, *, category: str = "unexpected_error", retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.retryable = retryable


@dataclass
class LLMExecutionReport:
    """不包含用户原文的单次 LLM 执行诊断。"""

    status: str = "skipped"
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    attempt_count: int = 0
    retry_count: int = 0
    tool_round_count: int = 0
    error_category: str | None = None
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _classify_llm_error(error: BaseException) -> tuple[str, bool]:
    """把 provider/网络异常映射为稳定、低基数的诊断类别。"""
    if isinstance(error, asyncio.TimeoutError) or isinstance(error, httpx.TimeoutException):
        return "timeout", True

    status_code = getattr(error, "status_code", None)
    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
    if status_code == 408:
        return "http_408", True
    if status_code == 429:
        return "http_429", True
    if isinstance(status_code, int) and 500 <= status_code <= 599:
        return "http_5xx", True
    if isinstance(status_code, int) and 400 <= status_code <= 499:
        return "http_4xx", False

    name = type(error).__name__.lower()
    if "timeout" in name:
        return "timeout", True
    if "connection" in name or "connect" in name:
        return "connection_error", True
    return "unexpected_error", False


def _error(category: str, *, retryable: bool = False) -> LLMGenerationError:
    return LLMGenerationError(f"LLM {category}", category=category, retryable=retryable)


def _remaining_seconds(deadline: float) -> float:
    return deadline - time.monotonic()


async def _create_completion_with_policy(client, request: dict[str, Any], deadline: float, report: LLMExecutionReport):
    """在统一 deadline 内执行一次模型请求，最多进行两次重试。"""
    max_attempts = 3
    for attempt in range(max_attempts):
        remaining = _remaining_seconds(deadline)
        if remaining <= 0:
            raise _error("deadline_exceeded")
        report.attempt_count += 1
        try:
            return await asyncio.wait_for(
                client.chat.completions.create(**request),
                timeout=remaining,
            )
        except asyncio.TimeoutError as exc:
            # wait_for 到达总预算时是 deadline；provider 主动抛出的 timeout 仍可重试。
            category = "deadline_exceeded" if _remaining_seconds(deadline) <= 0.01 else "timeout"
            retryable = category == "timeout"
        except Exception as exc:
            category, retryable = _classify_llm_error(exc)

        report.error_category = category
        report.retryable = retryable
        if not retryable or attempt >= max_attempts - 1:
            raise _error(category, retryable=retryable)

        delay = min(0.1 * (2 ** attempt), max(0.0, _remaining_seconds(deadline)))
        if delay <= 0:
            raise _error("deadline_exceeded")
        report.retry_count += 1
        await asyncio.sleep(delay)


def _get_client():
    global _client
    if _client is None and LLM_AVAILABLE:
        try:
            _client = _create_client()
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")
    return _client


def _build_prompt(context: str, interests: Optional[list] = None, history_context: str = "", locale: str = "zh-CN") -> str:
    locale = normalize_locale(locale)
    interest_hint = ""
    if interests:
        interest_hint = f"\n游客兴趣偏好：{', '.join(interests)}。在相关内容上可适当多着墨，但不必生硬点出。"
    return f"""你是灵山胜境景区的金牌AI导游"小灵"，博学多识、亲切热情，像真人导游面对面为游客讲解。

【景区知识库】（请严格基于以下片段回答，片段中未提及的信息不得编造）：
{context if context else "（本次未检索到相关知识片段）"}

【本轮会话上下文】（用于理解“它、那里、刚才那个、再详细点”等连续追问）：
{history_context if history_context else "无"}

回答要求：
0. 目标语言：{language_instruction(locale)} 除专有名词和引用原文外，不得混用中文；保留 citations 的 quote 原文，不要翻译或改写引用内容。
1. 必须且只能基于上方【景区知识库】中的信息作答，不得编造、不得臆测、不得用片段外的常识填补。片段中没有相关内容时，诚实告知目标语言的未知，并引导游客换个问题或询问官方。
   例外：涉及实时气象、出行路况等时效性信息时，若已配置外部工具会自动调用，可基于工具返回的实时结果作答。
2. 口吻像真人导游：自然、生动、有亲和力，可适度使用"您看""值得一提的是""悄悄告诉您"等引导语，避免生硬的百科式罗列。
3. 简洁：控制在200字以内，直击游客关心的信息，不堆砌冗余。
4. 若游客表达了兴趣偏好，自然地往其感兴趣的方向引导一两句。{interest_hint}
5. 若用户是连续追问，优先结合【本轮会话上下文】判断指代对象，但景点事实仍必须以【景区知识库】或工具结果为准。
6. 【输出格式硬约束 · 违反会导致语音播报异常】
   - 纯文本，禁止任何 Markdown 符号（*、**、#、- 等）。
   - 禁止添加括号内的语气/动作提示，如"（热情地）""（微笑）"等，用自然语气本身表达。
   - 回复末尾不要附加任何表情或动作描述，如"嘴角含笑""眨眼""双手合十"等。"""


# 内置应答模板（离线开发用）
MOCK_RESPONSES = {
    "高": "灵山大佛高达88米，加上基座总高度达101.5米，是目前世界上最高的青铜立佛像之一，非常壮观！",
    "佛": "灵山大佛位于无锡太湖之滨的灵山胜境，高88米，是中国著名的青铜佛像，每年吸引数百万游客前来朝拜。",
    "梵宫": "灵山梵宫是灵山胜境的核心建筑之一，被誉为'东方卢浮宫'，内部穹顶壁画精美绝伦，融合了佛教艺术与现代建筑美学。",
    "九龙": "九龙灌浴是灵山胜境的标志性景观，每天有定时表演，展示'九龙浴佛'的壮观场景，是游客最喜爱的打卡点之一。",
    "时间": "灵山胜境景区开放时间为每日08:00-17:30，建议游览4-5小时。九龙灌浴表演时间为10:00、11:30、14:00和15:30。",
    "门票": "灵山胜境门票价格约210元/人（旺季），具体以官方公布为准。建议提前网上购票，60岁以上老人和学生可享受优惠。",
    "路线": "推荐路线：入口→灵山大佛→梵宫→九龙灌浴→五印坛城→曼飞龙塔→出口，全程约4小时。",
    "历史": "灵山胜境始建于唐代，祥符禅寺有千年历史，是佛教禅宗的重要道场，文化底蕴深厚。",
    "素斋": "灵山梵宫内设有素斋餐厅，推荐品尝'罗汉斋'和'素面'，口味清淡雅致，人均消费约50-80元。",
    "交通": "从无锡市区可乘坐88路、89路公交直达灵山胜境，车程约40分钟。自驾游客可导航至'灵山胜境停车场'。",
}


def _clean_response(text: str) -> str:
    """清理 LLM 响应中的多余内容：语气提示、Markdown 符号、表情描述"""
    import re
    # 1. 移除中文括号内语气/动作提示：如（热情地）、（微微一笑）、（认真道）
    text = re.sub(r'（[^）]{1,15}?(?:地|着|道|说|笑|情|意|叹|点头|摇头|眨眼|摆手|鞠躬|挥手|合十|抱拳|双手|嘴角|躬身)[^）]{0,8}?）', '', text)
    # 2. 移除英文括号中的 stage direction：如 (smiling), (nodding)
    text = re.sub(r'\([^)]{1,20}?(?:smil|nod|gesture|bow|wave|wink|laugh)[^)]{0,8}?\)', '', text, flags=re.IGNORECASE)
    # 3. Markdown 加粗 **text** → text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 4. Markdown 斜体 *text*（两侧非星号，防止误伤）
    text = re.sub(r'(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)', r'\1', text)
    # 5. Markdown 标题符号 ## ### → 移除
    text = re.sub(r'^#{1,4}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+#{2,4}\s+', '，', text)  # 行中的 ## 替换为逗号
    # 6. 移除末尾独立的表情/动作描述括号
    text = re.sub(r'\s*[（(][^）)]{2,14}?(?:含笑|微笑|点头|摆手|鞠躬|挥手|合十|抱拳|眨眼|躬身|伸手|摊手|拍拍|指指)[^）)]{0,6}?[）)]\s*$', '', text)
    # 7. 移除零宽/不可见字符
    text = re.sub(r'[​‌‍⁠﻿]', '', text)
    # 8. 移除常见 Emoji（基于 Unicode 属性，TTS 无法朗读）
    try:
        # 编译后的 pattern 避免每次调用重新编译
        import unicodedata
        cleaned = []
        for ch in text:
            cat = unicodedata.category(ch)
            # So (Symbol, Other) = emoji 类字符
            # Sk (Symbol, Modifier) = 修饰符
            if cat not in ('So', 'Sk') and ord(ch) > 127:
                cleaned.append(ch)
            elif ord(ch) <= 127:
                cleaned.append(ch)
        text = ''.join(cleaned)
    except Exception:
        pass  # 降级：跳过 emoji 清理
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _mock_reply(query: str, context: str, locale: str = "zh-CN") -> str:
    """离线应答：中文保持旧模板，其他语言使用稳定的本地化开发回退。"""
    locale = normalize_locale(locale)
    text = query or ''
    if locale != "zh-CN":
        fallback = {
            "en": "Hello! I am Xiaoling, the AI guide for Lingshan Scenic Area. Please ask about attractions, weather, or a suggested route.",
            "ja": "こんにちは。霊山勝境のAIガイド、小霊です。観光スポットや天気、おすすめルートについてお尋ねください。",
            "ko": "안녕하세요. 영산승경 AI 가이드 샤오링입니다. 관광지, 날씨 또는 추천 코스를 질문해 주세요.",
        }
        return fallback[locale]
    route_terms = ('路线', '规划', '游览顺序', '怎么走', '几个景点', '一日游', '半日游', '半天游', '全天游')
    if '九龙灌浴' in text or '九龙浴佛' in text:
        if any(term in text for term in ('几点', '什么时候', '几时', '表演时间', '几场', '场次')):
            return _clean_response('九龙灌浴每天有四场表演：上午10:00、11:30，下午14:00、15:30。每场约15分钟，建议提前10分钟到达。')
        if any(term in text for term in route_terms):
            return _clean_response('九龙灌浴是灵山胜境的重要景点，适合与灵山大佛、梵宫等景点一起规划游览。')
        return _clean_response('九龙灌浴是灵山胜境的标志性景观，通过九龙喷水为浴中的佛像祈福，现场气氛庄严而有特色。')

    if '梵宫' in text and any(term in text for term in ('特色', '特点', '看点', '里面', '是什么')):
        return _clean_response(MOCK_RESPONSES['梵宫'])
    if ('灵山大佛' in text or '大佛' in text) and any(term in text for term in ('多高', '高度', '多少米')):
        return _clean_response(MOCK_RESPONSES['高'])
    if '灵山大佛' in text or '大佛' in text:
        return _clean_response(MOCK_RESPONSES['佛'])
    for keyword, reply in MOCK_RESPONSES.items():
        if keyword in text and keyword not in ('高', '佛', '九龙', '梵宫'):
            return _clean_response(f"{reply} 您还想了解什么？")

    if context:
        # 取第一个上下文片段的前100字作为参考
        first_chunk = context.split("\n\n")[0][:200]
        return _clean_response(f"根据景区资料，{first_chunk}... 请问您想深入了解哪个方面呢？")

    return _clean_response("您好！我是灵山胜境的AI导游小灵。您可以问我关于灵山大佛、梵宫、九龙灌浴、五印坛城等景点的问题，也可以让我为您推荐游览路线哦~")


async def generate_response(
    query: str,
    context: str,
    interests: Optional[list] = None,
    history_context: str = "",
    stream: bool = True,
    *,
    allow_mock_fallback: bool = True,
    report: LLMExecutionReport | None = None,
    locale: str = "zh-CN",
) -> AsyncGenerator[str, None]:
    """调用 LLM 生成回复（优先 API，降级到内置应答）

    当 llm_provider == deepseek_api 时启用 function calling：模型可自主决定调用
    高德工具（天气/导航）查实时信息，框架执行后把结果回灌，再生成最终回答。
    其余 provider 不启用工具，行为与旧版一致（向后兼容）。
    """
    execution_report = report or LLMExecutionReport()
    execution_report.provider = settings.llm_provider
    execution_report.model = settings.deepseek_model if settings.llm_provider == "deepseek_api" else settings.llm_model
    started = time.monotonic()
    client = _get_client()

    try:
        if not client:
            execution_report.status = "failed"
            execution_report.error_category = "client_unavailable"
            if not allow_mock_fallback:
                raise _error("client_unavailable")
            yield _mock_reply(query, context, locale)
            return

        # 工具在 deepseek_api 且配置了高德 key 时启用；其余情况关闭以保持兼容
        use_tools = settings.llm_provider == "deepseek_api" and bool(settings.amap_web_key)
        model = execution_report.model
        locale = normalize_locale(locale)
        messages = [
            {"role": "system", "content": _build_prompt(context, interests, history_context, locale)},
            {"role": "user", "content": query},
        ]
        tools = amap_tools.AMAP_TOOLS if use_tools else None
        deadline = time.monotonic() + max(0.01, float(settings.llm_timeout_seconds))

        async def call_model(*, include_tools: bool):
            return await _create_completion_with_policy(
                client,
                {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 512,
                    "tools": tools if include_tools else None,
                },
                deadline,
                execution_report,
            )

        # 工具调用循环：最多 3 轮；模型请求、工具执行和收尾共享同一 deadline。
        max_tool_rounds = 3
        for _ in range(max_tool_rounds + 1):
            response = await call_model(include_tools=True)
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                content = (msg.content or "").strip()
                if not content:
                    raise _error("empty_response")
                if not matches_target_language(content, locale):
                    messages.append(msg)
                    messages.append({
                        "role": "user",
                        "content": f"Your previous answer used the wrong language. {language_instruction(locale)} Rewrite the complete answer now; preserve factual content and citation IDs.",
                    })
                    response = await call_model(include_tools=False)
                    content = (response.choices[0].message.content or "").strip()
                    if not content or not matches_target_language(content, locale):
                        raise _error("wrong_response_language")
                execution_report.status = "ok"
                execution_report.error_category = None
                yield content
                return

            execution_report.tool_round_count += 1
            messages.append(msg)
            for tc in tool_calls:
                fn = tc.function
                try:
                    args = json.loads(fn.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                logger.info("工具调用 name=%s arg_keys=%s", fn.name, sorted(args))
                remaining = _remaining_seconds(deadline)
                if remaining <= 0:
                    raise _error("deadline_exceeded")
                result = await asyncio.wait_for(
                    amap_tools.execute_tool(fn.name, args),
                    timeout=remaining,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # 超出轮次仍有 tool_calls → 让模型基于已有结果收尾。
        logger.warning("工具调用触及上限 %s，强制收尾", max_tool_rounds)
        response = await call_model(include_tools=False)
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise _error("empty_response")
        execution_report.status = "ok"
        execution_report.error_category = None
        yield content
    except LLMGenerationError as exc:
        execution_report.status = "failed"
        execution_report.error_category = exc.category
        execution_report.retryable = exc.retryable
        if not allow_mock_fallback:
            logger.warning("LLM 生成失败，交由调用方处理 category=%s", exc.category)
            raise
        logger.warning("LLM 生成失败，使用内置应答模式 category=%s", exc.category)
        yield _mock_reply(query, context, locale)
    except Exception as exc:
        if _remaining_seconds(deadline) <= 0.01:
            category, retryable = "deadline_exceeded", False
        else:
            category, retryable = _classify_llm_error(exc)
        execution_report.status = "failed"
        execution_report.error_category = category
        execution_report.retryable = retryable
        if not allow_mock_fallback:
            logger.warning("LLM 生成失败，交由调用方处理 category=%s", category)
            raise _error(category, retryable=retryable) from exc
        logger.warning("LLM 生成失败，使用内置应答模式 category=%s", category)
        yield _mock_reply(query, context, locale)
    finally:
        execution_report.latency_ms = int((time.monotonic() - started) * 1000)


async def generate_response_simple(query: str) -> str:
    """简单问答（离线可用）"""
    return _mock_reply(query, "")
