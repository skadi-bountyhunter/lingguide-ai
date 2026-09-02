"""游客问答 API — 核心对话接口"""
import asyncio
import re
import time
import uuid
import json
import os
from collections import defaultdict, deque
from typing import Optional
from loguru import logger

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.core.rag import rag_service
from app.core.retrieval_types import RAGResult
from app.core.llm import (
    LLMExecutionReport,
    LLMGenerationError,
    generate_response,
    _clean_response,
)
from app.core.tts import VOICE_OPTIONS, synthesize
from app.core.emotion import analyze_emotion, analyze_voice_emotion, fuse_voice_text_emotion, get_expression
from app.core.asr import transcribe_audio
from app.core.locales import (
    SPOT_TRANSLATIONS,
    canonicalize_query,
    language_instruction,
    localize_duration,
    matches_target_language,
    message,
    normalize_locale,
)
from app.services.chat_service import log_interaction, get_session_history, build_history_context
from app.services.query_coordinator import (
    QueryResult,
    query_coordinator,
    build_citations,
    match_faq,
    faq_to_query_result,
)
from app.services.answer_orchestrator import NO_EVIDENCE_REPLY, generate_answer
from app.api.dependencies import get_optional_current_user, resolve_user_token
from app.core.database import async_session
from sqlalchemy import select
from app.models import User
from app.models.spot import Spot

router = APIRouter(prefix="/api/chat", tags=["对话"])
_ws_rate_windows: dict[str, deque[float]] = defaultdict(deque)
_ws_connections_by_ip: dict[str, int] = defaultdict(int)
_ws_session_tokens: dict[str, str] = {}
_ws_connection_lock = asyncio.Lock()


def _origin_allowed(origin: str | None) -> bool:
    """仅在启用来源校验时限制 WebSocket Origin。"""
    if not settings.websocket_require_origin:
        return True
    allowed = {item.strip() for item in settings.websocket_allowed_origins.split(",") if item.strip()}
    return bool(origin) and origin in allowed


def _client_ip(websocket: WebSocket) -> str:
    forwarded = websocket.headers.get("x-forwarded-for", "")
    return forwarded.split(",", 1)[0].strip() or (websocket.client.host if websocket.client else "unknown")


def _allow_ws_message(session_id: str, client_ip: str) -> bool:
    now = time.time()
    keys = (f"session:{session_id}", f"ip:{client_ip}")
    for key in keys:
        window = _ws_rate_windows[key]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= settings.websocket_rate_limit_per_minute:
            return False
    for key in keys:
        _ws_rate_windows[key].append(now)
    return True


async def _bind_ws_session(session_id: str, token: str) -> bool:
    async with _ws_connection_lock:
        owner = _ws_session_tokens.get(session_id)
        if owner is None:
            _ws_session_tokens[session_id] = token
            return True
        return owner == token


async def _acquire_ws_connection(client_ip: str) -> bool:
    async with _ws_connection_lock:
        if _ws_connections_by_ip[client_ip] >= settings.websocket_max_connections_per_ip:
            return False
        _ws_connections_by_ip[client_ip] += 1
        return True


async def _release_ws_connection(client_ip: str) -> None:
    async with _ws_connection_lock:
        current = _ws_connections_by_ip.get(client_ip, 0)
        if current <= 1:
            _ws_connections_by_ip.pop(client_ip, None)
        else:
            _ws_connections_by_ip[client_ip] = current - 1


# ===== 检索-生成复用工具 =====


async def _generate_with_deadline(
    query: str,
    result: QueryResult,
    interests: list[str] | None,
    history_context: str,
    timeout: float,
    locale: str = "zh-CN",
) -> str:
    """统一三条问答入口的生成超时语义。"""
    try:
        return await asyncio.wait_for(
            generate_answer(query, result, interests, history_context, locale),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        result.mark_generation_failure("llm_deadline_exceeded", "generation_timeout")
        return message("no_evidence", locale)


def _result_payload(result: QueryResult) -> tuple[list[str], list[dict], dict]:
    """从最终查询状态构造响应证据，避免超时后遗留候选 Citation。"""
    citations = [item.to_dict() for item in result.citations]
    retrieval = result.trace.to_dict()
    retrieval["status"] = "ready" if citations else "empty"
    return result.sources, citations, retrieval


def build_context(rag_results) -> str:
    """把 RAG 检索结果构造成带来源标注的结构化上下文，供 LLM 引用。

    格式：
      【知识片段1 · 来源: xxx.docx · 相关度0.82】
      <内容>
    无结果返回空串（调用方据此走通用应答）。
    """
    if not rag_results:
        return ""
    parts = []
    for i, r in enumerate(rag_results, 1):
        parts.append(f"【知识片段{i} · 来源: {r.source} · 相关度{r.score}】\n{r.content}")
    return "\n\n".join(parts)


class ChatRequest(BaseModel):
    """文本对话请求"""
    query: str
    session_id: Optional[str] = None
    interests: list[str] = []
    locale: str = "zh-CN"
    spot_id: Optional[str] = None

    @field_validator("locale")
    @classmethod
    def normalize_request_locale(cls, value: str) -> str:
        return normalize_locale(value)


class ChatResponse(BaseModel):
    """文本对话响应；新增字段保持可选，兼容旧客户端。"""
    session_id: str
    reply: str
    emotion: str
    expression: str
    sources: list[str]
    thinking_time_ms: int
    citations: list[dict] = []
    retrieval: dict = {}
    trace_id: str = ""


class RouteRequest(BaseModel):
    """路线推荐请求"""
    interests: list[str] = []
    duration: str = "半天"  # 半天 / 全天
    chat_query: str = ""    # 用户最近提问，作为最高优先级路线需求
    chat_reply: str = ""    # 被点击的导游回复，用于恢复已讨论的景点语境
    locale: str = "zh-CN"

    @field_validator("locale")
    @classmethod
    def normalize_request_locale(cls, value: str) -> str:
        return normalize_locale(value)


class RouteSpot(BaseModel):
    """路线景点；name 保持 canonical 中文，display_name 仅用于展示。"""
    name: str
    display_name: str = ""
    description: str = ""
    duration_min: int = 0  # 该景点实际游览时长（分钟），来自 Spot.duration；前端按此精确求和替代固定估算


def _parse_duration_minutes(duration: str) -> int:
    """把 Spot.duration（如 "1.5h"/"0.5h"/"30min"）解析为分钟，缺失或无法解析时按 30 分钟兜底。"""
    text = (duration or "").strip().lower()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*h(?:our)?s?$', text)
    if match:
        return round(float(match.group(1)) * 60)
    match = re.match(r'^(\d+(?:\.\d+)?)\s*m(?:in)?(?:ute)?s?$', text)
    if match:
        return round(float(match.group(1)))
    return 30

class RouteResponse(BaseModel):
    """路线推荐响应"""
    title: str = ""
    duration: str = ""
    spots: list[RouteSpot] = []
    tips: str = ""
    route_text: str = ""   # 纯文本摘要，兼容旧版
    sources: list[str] = []
    citations: list[dict] = []
    retrieval: dict = {}
    trace_id: str = ""
    alternatives: list[dict] = []  # 备选方案列表


def _is_route_request(query: str, spot_names: list[str] | None = None) -> bool:
    """只识别明确的路线规划请求，避免普通景点讲解误生成路线。"""
    text = (query or '').strip()
    if any(term in text for term in ('介绍', '讲解', '历史', '特色', '特点', '寓意', '在哪里', '几点')):
        return False
    strong_route_terms = ('路线', '规划', '顺序', '怎么走', '半天游', '半日游', '全天游', '一日游')
    if any(term in text for term in strong_route_terms):
        return True
    if any(term in text for term in ('推荐', '安排', '设计')) and any(term in text for term in ('游览', '行程', '景点')):
        return True
    names = [name for name in (spot_names or []) if name and name in text]
    return len(names) >= 2 and any(term in text for term in ('先', '再', '最后', '然后'))


def _route_plan_payload(route: RouteResponse, interests: list[str], duration_mode: str) -> dict:
    """把路线响应转换为前端可直接消费的有序快照。"""
    return {
        "schema_version": 1,
        "source": "chat",
        "title": route.title,
        "duration": route.duration,
        "duration_mode": duration_mode,
        "spots": [spot.model_dump() for spot in route.spots],
        "tips": route.tips,
        "interests": interests,
        "sources": route.sources,
        "citations": route.citations,
        "retrieval": route.retrieval,
        "trace_id": route.trace_id,
    }


@router.post("/text", response_model=ChatResponse)
async def chat_text(
    req: ChatRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """文本问答接口；认证可选，登录时绑定账号。"""
    t0 = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    history_context = build_history_context(
        await get_session_history(session_id, user_id=user_id)
    )
    query_result = await query_coordinator.retrieve_async(req.query, top_k=5, locale=req.locale)
    trace_id = query_result.trace_id
    if query_result.route == "faq" and query_result.results and req.locale == "zh-CN":
        reply = query_result.results[0].content
    else:
        reply = await _generate_with_deadline(
            req.query,
            query_result,
            req.interests,
            history_context,
            settings.llm_timeout_seconds + 0.5,
            req.locale,
        )
    sources = query_result.sources

    # 情感分析
    emotion_label, emotion_score = analyze_emotion(req.query)
    expression = get_expression(emotion_label)

    thinking_time = int((time.time() - t0) * 1000)

    await log_interaction(session_id, req.query, reply, query_mode="text",
                          user_id=user_id,
                          rag_sources=sources, emotion_label=emotion_label,
                          emotion_score=emotion_score,
                          thinking_time_ms=thinking_time,
                          citations=[item.to_dict() for item in query_result.citations],
                          retrieval=query_result.trace.to_dict(),
                          trace_id=query_result.trace_id,
                          spot_id=req.spot_id)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        emotion=emotion_label,
        expression=expression,
        sources=sources,
        thinking_time_ms=thinking_time,
        citations=[item.to_dict() for item in query_result.citations],
        retrieval=query_result.trace.to_dict(),
        trace_id=trace_id,
    )


@router.post("/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    interests: Optional[str] = Form("[]"),
    locale: str = Form("zh-CN"),
    spot_id: Optional[str] = Form(None),
    current_user: User | None = Depends(get_optional_current_user),
):
    """语音问答接口；认证可选，登录时绑定账号。"""
    t0 = time.time()
    session_id = session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    interests_list = json.loads(interests) if isinstance(interests, str) else interests
    locale = normalize_locale(locale)

    # 1. 语音识别
    audio_bytes = await audio.read()
    logger.info(f"收到语音: {len(audio_bytes)} bytes")
    query_text = await transcribe_audio(audio_bytes, locale=locale)
    logger.info(f"语音识别完成: text_chars={len(query_text)}")

    route_plan = None
    if _is_route_request(query_text):
        # 语音路线复用结构化路线生成，保证与文本 WebSocket 使用同一快照协议。
        duration_mode = "全天" if any(term in query_text for term in ("全天", "一日游")) else "半天"
        route_result = await asyncio.wait_for(
            generate_route(RouteRequest(
                interests=interests_list,
                duration=duration_mode,
                chat_query=query_text,
                locale=locale,
            )),
            timeout=settings.websocket_retrieval_timeout_seconds + settings.websocket_llm_timeout_seconds,
        )
        reply = route_result.route_text or message("route_ready", locale)
        sources = route_result.sources
        citations = route_result.citations
        retrieval = route_result.retrieval
        trace_id = route_result.trace_id
        route_plan = _route_plan_payload(route_result, interests_list, duration_mode)
    else:
        # 普通语音继续走 FAQ + 混合检索 + LLM，不改变原有响应语义。
        history_context = build_history_context(
            await get_session_history(session_id, user_id=user_id)
        )
        query_result = await query_coordinator.retrieve_async(query_text, top_k=5, locale=locale)
        if query_result.route == "faq" and query_result.results and locale == "zh-CN":
            reply = query_result.results[0].content
        else:
            reply = await _generate_with_deadline(
                query_text,
                query_result,
                interests_list,
                history_context,
                settings.llm_timeout_seconds + 0.5,
                locale,
            )
        sources = query_result.sources
        citations = [item.to_dict() if hasattr(item, "to_dict") else item for item in query_result.citations]
        retrieval = query_result.trace.to_dict()
        trace_id = query_result.trace_id

    # TTS 使用最终回复；路线语音与文字回复保持一致。
    audio_output = await synthesize(reply, locale=locale)

    text_emotion = analyze_emotion(query_text)
    voice_emotion = await analyze_voice_emotion(audio_bytes)
    emotion_label, emotion_score = (
        fuse_voice_text_emotion(voice_emotion, text_emotion) if voice_emotion is not None
        else text_emotion
    )
    expression = get_expression(emotion_label)
    thinking_time = int((time.time() - t0) * 1000)

    await log_interaction(session_id, query_text, reply, query_mode="voice",
                          user_id=user_id,
                          rag_sources=sources,
                          emotion_label=emotion_label, emotion_score=emotion_score,
                          thinking_time_ms=thinking_time,
                          citations=citations,
                          retrieval=retrieval, trace_id=trace_id,
                          spot_id=spot_id)

    from urllib.parse import quote
    response = {
        "session_id": session_id,
        "query_text": query_text,
        "reply": reply,
        "emotion": emotion_label,
        "expression": expression,
        "audio_url": f"/api/chat/audio/{session_id}?reply={quote(reply[:100])}",
        "thinking_time_ms": thinking_time,
        "sources": sources,
        "citations": citations,
        "retrieval": retrieval,
        "trace_id": trace_id,
    }
    if route_plan is not None:
        response["route_plan"] = route_plan
    return response


class TTSRequest(BaseModel):
    """受控音色和语速的 TTS 请求。"""

    text: str
    voice_key: str = "温柔女声"
    rate: float = Field(default=1.0, ge=0.75, le=1.25)
    locale: str = "zh-CN"

    @field_validator("locale")
    @classmethod
    def normalize_request_locale(cls, value: str) -> str:
        return normalize_locale(value)

    @field_validator("voice_key")
    @classmethod
    def validate_voice_key(cls, value: str) -> str:
        if value not in VOICE_OPTIONS:
            raise ValueError("不支持的音色")
        return value

@router.get("/audio/{session_id}")
async def get_audio_get(session_id: str, reply: str = "", locale: str = "zh-CN"):
    """获取 TTS 音频（GET 兼容语音端点短文本）"""
    clean_text = _clean_response(reply) if reply else "您好，我是小灵"
    locale = normalize_locale(locale)
    audio_data = await synthesize(clean_text, locale=locale)
    return Response(content=audio_data, media_type="audio/mpeg", headers={"Content-Language": locale})

@router.post("/audio/{session_id}")
async def get_audio_post(session_id: str, req: TTSRequest):
    """获取 TTS 音频，音色只接受服务端白名单键。"""
    clean_text = _clean_response(req.text) if req.text else "您好，我是小灵"
    requested_voice = VOICE_OPTIONS[req.voice_key] if req.locale == "zh-CN" else None
    audio_data = await synthesize(
        clean_text,
        voice=requested_voice,
        rate=req.rate,
        locale=req.locale,
    )
    return Response(content=audio_data, media_type="audio/mpeg", headers={"Content-Language": req.locale})


# ===== 路线推荐 =====

@router.post("/route", response_model=RouteResponse)
async def generate_route(req: RouteRequest, trace_id: str | None = None):
    """AI 个性化路线推荐；异常时基于真实景点生成确定性降级路线。"""
    import re as _re

    locale = normalize_locale(req.locale)
    spot_items: list[dict] = []
    try:
        async with async_session() as db:
            result = await db.execute(select(Spot).order_by(Spot.sort_order.asc()))
            for spot in result.scalars().all():
                spot_items.append({
                    "name": spot.name,
                    "tags": spot.tags_list,
                    "desc": spot.desc or "",
                    "full_desc": getattr(spot, "full_desc", "") or "",
                    "id": getattr(spot, "id", None),
                    "duration_min": _parse_duration_minutes(spot.duration or ""),
                })
    except Exception as e:
        logger.warning(f"route 取景点失败，退回 fallback 列表：{e}")
        fallback_names = [
            "灵山大佛", "梵宫", "九龙灌浴", "五印坛城", "降魔浮雕", "菩提大道",
            "灵山大照壁", "五明桥", "佛足坛", "五智门", "阿育王柱", "百子戏弥勒",
            "祥符禅寺", "佛教文化博览馆", "曼飞龙塔", "无尽意斋", "拈花广场",
            "梵天花海", "香月花街", "拈花堂", "五灯湖", "鹿鸣谷",
        ]
        spot_items = [{"name": name, "tags": [], "desc": "", "full_desc": "", "id": None, "duration_min": 30} for name in fallback_names]

    req_interests = [item.strip() for item in req.interests if item.strip()]
    interest_items = [
        item for item in spot_items
        if any(tag in req_interests for tag in item["tags"])
    ]
    spot_names = [item["name"] for item in spot_items]
    item_by_name = {item["name"]: item for item in spot_items}
    interest_str = "、".join(req_interests) if req_interests else "综合游览"
    chat_query = (req.chat_query or "").strip()
    chat_reply = (req.chat_reply or "").strip()
    query = chat_query or chat_reply or f"请为偏好{interest_str}的游客规划一条{req.duration}的灵山胜境游览路线"

    query_result = await query_coordinator.retrieve_async(query, top_k=5, trace_id=trace_id, locale=locale)
    trace_id = query_result.trace_id
    rag_results = query_result.results
    context = build_context(rag_results)
    sources = query_result.sources
    spot_list_str = "\n".join(
        f"- {item['name']}｜标签：{'、'.join(item['tags']) or '综合'}｜简介：{item['desc'][:45]}"
        for item in spot_items
    )
    route_prompt = f"""你是灵山胜境的资深导游。{language_instruction(locale)} 请根据以下景区知识，为游客规划一条{req.duration}的游览路线。
游客兴趣偏好：{interest_str}
游客本次需求：{chat_query or '无'}
导游刚才的回复（仅供识别已讨论景点，用户需求优先）：{chat_reply or '无'}

【可选景点（必须且只能从这些景点中挑选，不得编造其他名字）】
{spot_list_str}

【景区知识】
{context if context else "灵山胜境主要景点见上方候选清单"}

请严格按照以下 JSON 格式输出（只输出 JSON，不要任何前后缀说明、不要 markdown 代码块包裹）：
{{"title":"一个吸引人的路线名字","duration":"约X小时","spots":[{{"name":"景点1","description":"一句话亮点说明"}},{{"name":"景点2","description":"一句话亮点说明"}}],"tips":"1-2句贴心建议"}}

要求：
- spots 中的 name 必须且只能是上方候选清单里的中文 canonical 景点名，逐字一致；name 不翻译，title/duration/description/tips 按目标语言输出
- 优先保持游客本次需求中明确点名景点的先后顺序，再结合兴趣偏好补充景点
- 路线安排合理，考虑景点间距离与游览节奏
- 每个景点描述控制在15字以内，亲切如真人导游口吻
- tips 要实用具体
- 景点数量：半天5个，全天6-8个；若候选景点不足则全部列出
- spots 不得重复同一个景点"""

    reply_parts: list[str] = []
    llm_report = LLMExecutionReport()
    try:
        async for chunk in generate_response(
            route_prompt,
            context if context else "灵山胜境景区",
            req.interests,
            allow_mock_fallback=False,
            report=llm_report,
            locale=locale,
        ):
            reply_parts.append(chunk)
    except LLMGenerationError as e:
        logger.warning("route LLM 生成失败，使用真实景点降级路线 category=%s", e.category)
    query_result.trace.channels["llm"] = llm_report.to_dict()
    if llm_report.status == "failed":
        query_result.trace.degraded = True
        query_result.degraded = True
        existing_reason = query_result.trace.fallback_reason or ""
        reason = f"llm_{llm_report.error_category or 'generation_failed'}"
        query_result.trace.fallback_reason = ";".join(dict.fromkeys(filter(None, [existing_reason, reason])))
        query_result.fallback_reason = query_result.trace.fallback_reason
    raw_text = "".join(reply_parts)

    def _normalize_name(name: str) -> str:
        n = _re.sub(r'^[\s]*[#*\-•·]+', '', str(name or ""))
        n = _re.sub(r'^\*{1,2}(.*?)\*{1,2}$', r'\1', n)
        return _clean_response(n).strip(' *•·').strip()

    def _match_spot(name: str) -> str | None:
        n = _normalize_name(name)
        if not n:
            return None
        if n in item_by_name:
            return n
        for spot_name in spot_names:
            if spot_name in n or (len(n) >= 2 and n in spot_name):
                return spot_name
        return None

    def _extract_mentions(text: str) -> list[str]:
        positions = [
            (text.find(name), index, name)
            for index, name in enumerate(spot_names)
            if name in text
        ]
        positions.sort(key=lambda value: (value[0], value[1]))
        return [name for _, _, name in positions]

    parsed_spots: list[RouteSpot] = []
    title = message("route_fallback_title", locale)
    duration_str = localize_duration(f"约{req.duration}", locale)
    tips = ""
    route_data: dict | None = None

    if raw_text.strip():
        try:
            json_text = raw_text.strip()
            code_block = _re.search(r'```(?:json)?\s*(.*?)\s*```', json_text, _re.DOTALL)
            if code_block:
                json_text = code_block.group(1)
            first_brace = json_text.find('{')
            last_brace = json_text.rfind('}')
            if first_brace != -1 and last_brace > first_brace:
                json_text = json_text[first_brace:last_brace + 1]
            route_data = json.loads(json_text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"route JSON 解析失败，使用正则回退：{e}")

    if isinstance(route_data, dict):
        generated_title = _clean_response(str(route_data.get("title", "")))
        generated_duration = _clean_response(str(route_data.get("duration", "")))
        generated_tips = _clean_response(str(route_data.get("tips", "")))
        if locale == "zh-CN" or matches_target_language(generated_title, locale):
            title = generated_title or title
        if locale == "zh-CN" or matches_target_language(generated_duration, locale):
            duration_str = generated_duration or duration_str
        if locale == "zh-CN" or matches_target_language(generated_tips, locale):
            tips = generated_tips
        raw_spots = route_data.get("spots", [])
        if isinstance(raw_spots, list):
            for spot in raw_spots:
                if not isinstance(spot, dict):
                    continue
                matched = _match_spot(spot.get("name", ""))
                if matched:
                    parsed_spots.append(RouteSpot(
                        name=matched,
                        description=_clean_response(str(spot.get("description", ""))),
                    ))
    elif raw_text.strip():
        # 结构解析前保留换行，避免编号路线被压成一行后只识别第一项。
        structured_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        title_match = _re.search(r'路线名称[：:]\s*(.+?)(?:\n|##|\#|$)', structured_text)
        if title_match:
            title = _clean_response(title_match.group(1)) or title
        duration_match = _re.search(r'(?:游览时长|约|时长)[：:]*\s*(\S+小时|\S+天)', structured_text)
        if duration_match:
            duration_str = _clean_response(duration_match.group(1)) or duration_str

        seq_section = structured_text
        seq_match = _re.search(
            r'路线顺序[：:]?\s*(.+?)(?=(?:贴心提示|温馨提示|提示|$))',
            structured_text,
            _re.DOTALL,
        )
        if seq_match:
            seq_section = seq_match.group(1)
        segments = _re.split(r'(?:📍\s*)?第.{1,3}站[：:]?\s*', seq_section)
        if len(segments) <= 1:
            segments = _re.split(
                r'(?:(?:^|\n)\s*(?:\d+[\.、．)）]|[①-⑳]|[-*•·])\s*)',
                seq_section,
            )
        for segment in segments:
            segment = segment.strip()
            if len(segment) < 2:
                continue
            pair = _re.split(r'\s*(?:[—–-]|[：:])\s*', segment, maxsplit=1)
            matched = _match_spot(pair[0])
            if matched:
                description = _clean_response(pair[1]) if len(pair) > 1 else ""
                parsed_spots.append(RouteSpot(name=matched, description=description))

        tip_match = _re.search(
            r'(?:贴心提示|温馨提示|提示)[：:]\s*(.+?)(?=(?:贴心提示|温馨提示|提示)[：:]|$)',
            structured_text,
            _re.DOTALL | _re.IGNORECASE,
        )
        if tip_match:
            tips = _clean_response(tip_match.group(1))

    parsed_by_name: dict[str, RouteSpot] = {}
    parsed_order: list[str] = []
    for spot in parsed_spots:
        if spot.name not in parsed_by_name:
            parsed_by_name[spot.name] = spot
            parsed_order.append(spot.name)

    priority_names = (
        _extract_mentions(chat_query)
        + parsed_order
        + _extract_mentions(chat_reply)
        + [item["name"] for item in interest_items]
        + spot_names
    )
    ordered_names: list[str] = []
    seen: set[str] = set()
    for name in priority_names:
        if name in item_by_name and name not in seen:
            seen.add(name)
            ordered_names.append(name)

    is_all_day = "全天" in req.duration
    target_count = 6 if is_all_day else 5
    max_count = 8 if is_all_day else 5
    selected_count = min(max_count, max(target_count, len(parsed_order)))
    selected_names = ordered_names[:selected_count]
    final_spots = []
    for name in selected_names:
        parsed_description = (
            parsed_by_name[name].description
            if name in parsed_by_name and parsed_by_name[name].description
            else ""
        )
        if parsed_description and (
            locale == "zh-CN" or matches_target_language(parsed_description, locale)
        ):
            description = parsed_description
        elif locale == "zh-CN":
            description = item_by_name[name]["desc"][:15].strip() or message(
                "route_fallback_description", locale
            )
        else:
            description = SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get(
                "desc", message("route_fallback_description", locale)
            )
        display_name = (
            SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get("name", name)
            if locale != "zh-CN" else name
        )
        final_spots.append(RouteSpot(
            name=name,
            display_name=display_name,
            description=description,
            duration_min=item_by_name.get(name, {}).get("duration_min", 30),
        ))
    route_evidence = list(query_result.results)
    seen_evidence_ids = {item.chunk_id for item in route_evidence}
    for spot in final_spots:
        item = item_by_name.get(spot.name) or {}
        spot_id = item.get("id")
        if not spot_id:
            continue
        chunk_id = f"spot:{spot_id}"
        if chunk_id in seen_evidence_ids:
            continue
        route_evidence.append(RAGResult(
            content=item.get("full_desc") or item.get("desc") or spot.description,
            source=spot.name,
            score=1.0,
            chunk_id=chunk_id,
            document_id=chunk_id,
            source_type="spot",
            retrieval_method="structured_spot",
            confidence=1.0,
            quality_reason="structured_spot_candidate",
            index_version="spot-live",
        ))
        seen_evidence_ids.add(chunk_id)
    route_citations = build_citations(route_evidence)

    if len(final_spots) > len(parsed_order):
        tips = tips or message("route_fallback_tips", locale)
        logger.warning(
            f"route 使用真实景点补足路线：解析 {len(parsed_order)} 个，最终 {len(final_spots)} 个"
        )

    # 生成备选方案：基于不同的景点组合
    alternatives = []
    if len(ordered_names) >= selected_count + 2:
        # 方案2：保留核心景点，替换1-2个景点
        alt2_names = selected_names[:-2] + ordered_names[selected_count:selected_count+2]
        alt2_spots = []
        for name in alt2_names:
            parsed_description = (
                parsed_by_name[name].description
                if name in parsed_by_name and parsed_by_name[name].description
                else ""
            )
            if parsed_description and (locale == "zh-CN" or matches_target_language(parsed_description, locale)):
                description = parsed_description
            elif locale == "zh-CN":
                description = item_by_name[name]["desc"][:15].strip() or message("route_fallback_description", locale)
            else:
                description = SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get("desc", message("route_fallback_description", locale))
            display_name = (
                SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get("name", name)
                if locale != "zh-CN" else name
            )
            alt2_spots.append({
                "name": name,
                "display_name": display_name,
                "description": description,
                "duration_min": item_by_name.get(name, {}).get("duration_min", 30),
            })

        alternatives.append({
            "title": message("route_alternative_2_title", locale) if locale != "zh-CN" else f"{title}（方案二）",
            "duration": duration_str,
            "spots": alt2_spots,
            "tips": message("route_alternative_2_tips", locale) if locale != "zh-CN" else "调整部分景点，体验更多元化",
        })

        # 方案3：如果还有更多景点，生成第三个方案
        if len(ordered_names) >= selected_count + 4:
            alt3_names = selected_names[:2] + ordered_names[selected_count+2:selected_count+2+selected_count-2]
            alt3_spots = []
            for name in alt3_names:
                parsed_description = (
                    parsed_by_name[name].description
                    if name in parsed_by_name and parsed_by_name[name].description
                    else ""
                )
                if parsed_description and (locale == "zh-CN" or matches_target_language(parsed_description, locale)):
                    description = parsed_description
                elif locale == "zh-CN":
                    description = item_by_name[name]["desc"][:15].strip() or message("route_fallback_description", locale)
                else:
                    description = SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get("desc", message("route_fallback_description", locale))
                display_name = (
                    SPOT_TRANSLATIONS.get(name, {}).get(locale, {}).get("name", name)
                    if locale != "zh-CN" else name
                )
                alt3_spots.append({
                    "name": name,
                    "display_name": display_name,
                    "description": description,
                    "duration_min": item_by_name.get(name, {}).get("duration_min", 30),
                })

            alternatives.append({
                "title": message("route_alternative_3_title", locale) if locale != "zh-CN" else f"{title}（方案三）",
                "duration": duration_str,
                "spots": alt3_spots,
                "tips": message("route_alternative_3_tips", locale) if locale != "zh-CN" else "探索更多小众景点",
            })

    return RouteResponse(
        title=title,
        duration=duration_str,
        spots=final_spots,
        tips=tips,
        route_text="\n".join(
            f"{index + 1}. {spot.display_name or spot.name} — {spot.description}"
            for index, spot in enumerate(final_spots)
        ),
        sources=sources,
        citations=[item.to_dict() for item in route_citations],
        retrieval=query_result.trace.to_dict(),
        trace_id=trace_id,
        alternatives=alternatives,
    )


# ===== WebSocket 实时对话 =====

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """WebSocket 实时对话，按临时令牌绑定会话并支持任务取消。"""
    client_ip = _client_ip(websocket)
    if not _origin_allowed(websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="不允许的来源")
        return
    if not await _acquire_ws_connection(client_ip):
        await websocket.close(code=1013, reason="连接数过多")
        return

    await websocket.accept()
    bound = False
    user_id: str | None = None
    message_count = 0
    active_tasks: set[asyncio.Task] = set()
    send_lock = asyncio.Lock()

    async def send_json(payload: dict) -> None:
        await asyncio.wait_for(
            _send_ws_json(websocket, payload, send_lock),
            timeout=settings.websocket_send_timeout_seconds,
        )

    async def process_message(data: dict) -> None:
        query = str(data.get("query", ""))
        if len(query) > 500:
            await websocket.close(code=1009, reason="问题过长")
            return
        mode = data.get("mode", "text")
        interests = data.get("interests", [])
        locale = normalize_locale(data.get("locale", "zh-CN"))
        spot_id = data.get("spot_id")
        t0 = time.time()
        request_id = f"req_{uuid.uuid4().hex}"
        message_id = f"msg_{uuid.uuid4().hex}"
        trace_id = f"trace_{uuid.uuid4().hex}"
        event_seq = 0

        async def send_event(event_type: str, **payload):
            nonlocal event_seq
            event_seq += 1
            await send_json({
                **payload,
                "type": event_type,
                "request_id": request_id,
                "message_id": message_id,
                "trace_id": trace_id,
                "locale": locale,
                "seq": event_seq,
            })

        async def send_error(error_message: str, *, reason: str = "websocket_error"):
            error_retrieval = {
                "status": "error",
                "route": "none",
                "degraded": True,
                "fallback_reason": reason,
            }
            await send_event(
                "error", status="error", message=error_message,
                sources=[], citations=[], retrieval=error_retrieval,
            )
            await send_event(
                "message_done", status="error", reply_text=error_message,
                sources=[], citations=[], retrieval=error_retrieval,
            )

        try:
            if not query.strip():
                await send_error(message("empty_query", locale), reason="empty_query")
                return

            await send_event("rag_started", status="started")
            query_result = await asyncio.wait_for(
                query_coordinator.retrieve_async(query, top_k=5, trace_id=trace_id, locale=locale),
                timeout=settings.websocket_retrieval_timeout_seconds,
            )
            if query_result.route == "faq" and query_result.results and locale == "zh-CN":
                clean_answer = query_result.results[0].content
                faq_citation = query_result.citations[0].to_dict()
                faq_retrieval = query_result.trace.to_dict()
                faq_retrieval.update({"route": "faq", "degraded": False, "status": "ready"})
                await send_event("rag_done", status="ready", sources=["FAQ 精确匹配"], citations=[faq_citation], retrieval=faq_retrieval)
                await send_event("llm_stream", chunk=clean_answer)
                emotion_label, emotion_score = analyze_emotion(query)
                expression = get_expression(emotion_label)
                thinking = int((time.time() - t0) * 1000)
                await log_interaction(session_id, query, clean_answer, query_mode=mode,
                                      user_id=user_id, rag_sources=["FAQ 精确匹配"], emotion_label=emotion_label,
                                      emotion_score=emotion_score, thinking_time_ms=thinking,
                                      citations=[faq_citation], retrieval=faq_retrieval,
                                      trace_id=trace_id, spot_id=spot_id)
                await send_event("llm_done", status="ready", reply_text=clean_answer,
                                 emotion=emotion_label, expression=expression,
                                 thinking_time_ms=thinking, sources=["FAQ 精确匹配"],
                                 citations=[faq_citation], retrieval=faq_retrieval)
                await send_event("message_done", status="ready", reply_text=clean_answer,
                                 emotion=emotion_label, expression=expression,
                                 thinking_time_ms=thinking, sources=["FAQ 精确匹配"],
                                 citations=[faq_citation], retrieval=faq_retrieval)
                return

            if mode == "voice":
                await send_event("asr_done", asr_text=query)

            canonical_query = canonicalize_query(query, locale)
            if _is_route_request(canonical_query):
                duration_mode = "全天" if any(term in canonical_query for term in ("全天", "一日游")) else "半天"
                route_result = await asyncio.wait_for(
                    generate_route(RouteRequest(
                        interests=interests,
                        duration=duration_mode,
                        chat_query=query,
                        locale=locale,
                    ), trace_id=trace_id),
                    timeout=settings.websocket_retrieval_timeout_seconds + settings.websocket_llm_timeout_seconds,
                )
                reply = route_result.route_text or message("route_ready", locale)
                route_plan = _route_plan_payload(route_result, interests, duration_mode)
                emotion_label, emotion_score = analyze_emotion(query)
                expression = get_expression(emotion_label)
                thinking = int((time.time() - t0) * 1000)
                await send_event("rag_done", status="ready", sources=route_result.sources,
                                 citations=route_result.citations, retrieval=route_result.retrieval)
                await send_event("llm_stream", chunk=reply)
                await log_interaction(session_id, query, reply, query_mode=mode,
                                      user_id=user_id,
                                      rag_sources=route_result.sources, emotion_label=emotion_label,
                                      emotion_score=emotion_score, thinking_time_ms=thinking,
                                      citations=route_result.citations, retrieval=route_result.retrieval,
                                      trace_id=trace_id, spot_id=spot_id)
                await send_event("llm_done", status="ready", reply_text=reply,
                                 emotion=emotion_label, expression=expression,
                                 thinking_time_ms=thinking, sources=route_result.sources,
                                 citations=route_result.citations, retrieval=route_result.retrieval,
                                 route_plan=route_plan)
                await send_event("message_done", status="ready", reply_text=reply,
                                 emotion=emotion_label, expression=expression,
                                 thinking_time_ms=thinking, sources=route_result.sources,
                                 citations=route_result.citations, retrieval=route_result.retrieval,
                                 route_plan=route_plan)
                return

            history_context = build_history_context(
                await get_session_history(session_id, user_id=user_id)
            )
            sources, citation_data, retrieval_data = _result_payload(query_result)
            await send_event("rag_done", status=retrieval_data["status"],
                             sources=sources, citations=citation_data,
                             retrieval=retrieval_data)
            reply = await _generate_with_deadline(
                query,
                query_result,
                interests,
                history_context,
                settings.websocket_llm_timeout_seconds,
                locale,
            )
            await send_event("llm_stream", chunk=reply)
            emotion_label, emotion_score = analyze_emotion(query)
            expression = get_expression(emotion_label)
            thinking = int((time.time() - t0) * 1000)
            reply = reply or "暂时无法生成回复，请稍后重试。"
            sources, citation_data, retrieval_data = _result_payload(query_result)
            await log_interaction(session_id, query, reply, query_mode=mode,
                                  user_id=user_id,
                                  rag_sources=sources, emotion_label=emotion_label,
                                  emotion_score=emotion_score, thinking_time_ms=thinking,
                                  citations=citation_data, retrieval=retrieval_data,
                                  trace_id=query_result.trace_id, spot_id=spot_id)
            await send_event("llm_done", status=retrieval_data["status"],
                             reply_text=reply, emotion=emotion_label, expression=expression,
                             thinking_time_ms=thinking, sources=sources,
                             citations=citation_data, retrieval=retrieval_data)
            await send_event("message_done", status=retrieval_data["status"],
                             reply_text=reply, emotion=emotion_label, expression=expression,
                             thinking_time_ms=thinking, sources=sources,
                             citations=citation_data, retrieval=retrieval_data)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            await send_error(message("timeout", locale), reason="websocket_deadline_exceeded")
        except WebSocketDisconnect:
            raise
        except Exception as exc:
            logger.exception(f"WebSocket 对话处理失败: {exc}")
            try:
                await send_error(message("service_unavailable", locale))
            except Exception:
                pass

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.websocket_receive_timeout_seconds,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1001, reason="接收超时")
                break
            if len(json.dumps(data, ensure_ascii=False)) > settings.websocket_max_message_bytes:
                await websocket.close(code=1009, reason="消息过大")
                break
            if not isinstance(data, dict):
                await websocket.close(code=1003, reason="消息格式错误")
                break
            if not bound:
                token = str(data.get("session_token", "")).strip()
                if len(token) < 16 or not await _bind_ws_session(session_id, token):
                    await websocket.close(code=1008, reason="会话绑定失败")
                    break
                auth_token = str(data.get("auth_token", "")).strip()
                if auth_token:
                    try:
                        async with async_session() as db:
                            user = await resolve_user_token(auth_token, db)
                        user_id = user.id
                    except Exception:
                        await websocket.close(code=1008, reason="账号认证失败")
                        break
                bound = True
                if "query" not in data:
                    continue
            message_count += 1
            if message_count > settings.websocket_max_messages_per_connection:
                await websocket.close(code=1008, reason="单连接消息数超限")
                break
            if not _allow_ws_message(session_id, client_ip):
                await websocket.close(code=1008, reason="请求过于频繁")
                break
            if len(active_tasks) >= settings.websocket_max_concurrent_messages:
                await websocket.close(code=1008, reason="并发消息数超限")
                break
            task = asyncio.create_task(process_message(data))
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)
    except WebSocketDisconnect:
        pass
    finally:
        for task in active_tasks:
            task.cancel()
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
        await _release_ws_connection(client_ip)


async def _send_ws_json(websocket: WebSocket, payload: dict, send_lock: asyncio.Lock) -> None:
    """串行发送事件，避免并发消息交错写入同一连接。"""
    async with send_lock:
        await websocket.send_json(payload)
