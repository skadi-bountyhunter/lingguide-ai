"""情感分析模块"""
import asyncio
import re
from typing import Tuple

from loguru import logger

EMOTION_AVAILABLE = False
try:
    from snownlp import SnowNLP
    EMOTION_AVAILABLE = True
except ImportError:
    logger.warning("snownlp 未安装，情感分析使用规则模式")

# 纯信息查询句（怎么走/门票多少钱等）不带说话人情绪，命中且无情绪词时直接判中性，
# 避免 SnowNLP 对问句系统性偏置（实测"灵山大佛怎么走"被打到 0.91 正向）
_INQUIRY_PATTERN = re.compile(
    "怎么走|怎么去|如何去|在哪|哪里|路线|多少钱|门票|多久|几点|开放时间|"
    "营业时间|怎么预约|停车|地图|电话|地址|开门|关门|时长|多长时间|怎么坐|坐几路"
)

_NEGATIONS = ("不", "没", "无", "别", "非")
# "好"单独出现时是强化词而非情绪词（好无聊/好累/好烦 = "很无聊/很累/很烦"），
# 不放进 _POS_WORDS，避免和"好"作为褒义词冲突；含"好"的固定褒义搭配单独列在 _POS_WORDS
_INTENSIFIERS = ("一点都", "非常", "特别", "太", "完全", "根本", "极其", "十分", "很", "好")

# 景区服务场景优先规则：投诉/感谢等短句比通用模型更可靠
_STRONG_NEG = {"垃圾", "太差", "差评", "投诉", "坑人", "退票", "骗", "生气", "愤怒", "态度差", "服务差"}
_NEG_WORDS = {
    "不好", "差", "失望", "无聊", "坑", "讨厌", "贵", "排队", "等太久", "找不到",
    "不满意", "不舒服", "累", "热", "冷", "走不动", "腿疼", "晒死了", "烦",
    "拥挤", "人太多", "看不清", "听不清", "一般",
}
_STRONG_POS = {"太棒", "非常好", "特别好", "很棒", "惊艳", "满意", "感谢", "谢谢", "太震撼", "太美了"}
_POS_WORDS = {
    "棒", "喜欢", "美丽", "壮观", "精彩", "不错", "厉害", "赞", "方便", "清楚", "舒服",
    "好玩", "好看", "好吃", "好听", "好棒",
    "哇", "居然", "没想到", "第一次见", "值得",
}


def _scan(text: str, words: set, weight: float) -> float:
    """扫描词表命中，按否定词/强化词调整极性和幅度；weight 符号代表该词表的基础极性。"""
    magnitude = abs(weight)
    polarity = 1 if weight > 0 else -1
    total = 0.0
    for word in words:
        start = 0
        while True:
            idx = text.find(word, start)
            if idx == -1:
                break
            prefix = text[max(0, idx - 4):idx]
            negated = any(neg in prefix for neg in _NEGATIONS)
            intensified = any(i in prefix for i in _INTENSIFIERS)
            amount = magnitude * (1.6 if intensified else 1.0)
            total += -amount * polarity if negated else amount * polarity
            start = idx + len(word)
    return total


def _rule_score(text: str) -> Tuple[float, bool]:
    """规则打分：命中词表的短句判断力优于通用情感模型。"""
    delta = 0.0
    delta += _scan(text, _STRONG_POS, 0.2)
    delta += _scan(text, _POS_WORDS, 0.1)
    delta += _scan(text, _STRONG_NEG, -0.25)
    delta += _scan(text, _NEG_WORDS, -0.12)
    hit = delta != 0.0

    score = 0.5 + delta
    if hit and text.endswith(("吗", "呢", "嘛", "么")):
        # 疑问句尾情绪线索较弱（"这里好玩吗"不代表说话人已有倾向），向中性收拢
        score = 0.5 + (score - 0.5) * 0.5
    return score, hit


def analyze_emotion(text: str) -> Tuple[str, float]:
    """分析用户文本情绪，返回标签和 0-1 分数。"""
    clean = (text or "").strip()
    if not clean:
        return "neutral", 0.5

    rule_score, hit_rule = _rule_score(clean)

    if not hit_rule and _INQUIRY_PATTERN.search(clean):
        return "neutral", 0.5

    if EMOTION_AVAILABLE:
        try:
            model_score = SnowNLP(clean).sentiments
        except Exception:
            model_score = rule_score
    else:
        model_score = rule_score

    # 规则命中时以规则为主：SnowNLP 对短句/口语化负面表达经常判反
    score = rule_score * 0.9 + model_score * 0.1 if hit_rule else model_score
    score = max(0.0, min(1.0, score))

    if score > 0.60:
        return "positive", round(score, 3)
    if score < 0.38:
        return "negative", round(score, 3)
    return "neutral", round(score, 3)


# ---------- 语音情感（A方案：百炼平台 paraformer-realtime） ----------

_VOICE_POSITIVE = {"happy", "joy", "excited", "surprise", "喜悦", "高兴"}
_VOICE_NEGATIVE = {"angry", "sad", "fearful", "disgusted", "fear", "disgust",
                   "anger", "sadness", "悲伤", "愤怒", "恐惧"}


def _aggregate_emotions(labels: list) -> Tuple[str, float]:
    if not labels:
        return "neutral", 0.5
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for raw in labels:
        key = str(raw).lower().strip()
        if key in _VOICE_POSITIVE or any(p in key for p in ("hap", "joy", "pos")):
            counts["positive"] += 1
        elif key in _VOICE_NEGATIVE or any(p in key for p in ("neg", "ang", "sad", "fear")):
            counts["negative"] += 1
        else:
            counts["neutral"] += 1
    total = sum(counts.values()) or 1
    dominant = max(counts, key=counts.get)
    ratio = counts[dominant] / total
    base = {"positive": 0.75, "neutral": 0.5, "negative": 0.25}[dominant]
    return dominant, round(max(0.0, min(1.0, 0.5 + (base - 0.5) * ratio)), 3)


def _voice_emotion_sync(audio_bytes: bytes, fmt: str, sample_rate: int, api_key: str) -> Tuple[str, float]:
    from dashscope.audio.asr import Recognition

    collected: list = []

    class _Cb(Recognition.Callback):
        def on_event(self, result, *args, **kwargs):
            try:
                sentence = result.output.sentence
                emo = getattr(sentence, "emotion", None)
                if emo:
                    collected.append(emo)
                    return
                for w in getattr(sentence, "words", None) or []:
                    w_emo = getattr(w, "emotion", None)
                    if w_emo:
                        collected.append(w_emo)
            except Exception:
                pass

        def on_complete(self):
            pass

        def on_error(self, result, *args, **kwargs):
            logger.warning(f"DashScope ASR error: {result}")

    rec = Recognition(
        model="paraformer-realtime-v2",
        format=fmt,
        sample_rate=sample_rate,
        emotion_channel="all",
        api_key=api_key,
        callback=_Cb(),
    )
    rec.start()
    for i in range(0, len(audio_bytes), 3200):
        rec.send_audio_frame(audio_bytes[i:i + 3200])
    rec.stop()
    return _aggregate_emotions(collected)


async def analyze_voice_emotion(
    audio_bytes: bytes, fmt: str = "wav", sample_rate: int = 16000
) -> Tuple[str, float] | None:
    """调用百炼平台语音情感识别；未配置或失败时返回 None（调用方回退文本情感）。"""
    from app.config import settings
    if not getattr(settings, "dashscope_api_key", "") or not audio_bytes:
        return None
    try:
        import dashscope  # noqa: F401
    except ImportError:
        logger.warning("dashscope 未安装，跳过语音情感识别")
        return None
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _voice_emotion_sync, audio_bytes, fmt, sample_rate, settings.dashscope_api_key
        )
    except Exception as e:
        logger.warning(f"语音情感识别失败: {e}")
        return None


def fuse_voice_text_emotion(
    voice: Tuple[str, float], text: Tuple[str, float]
) -> Tuple[str, float]:
    """双通道融合：标签一致取高置信度；不一致时语音权重 70%。"""
    v_label, v_score = voice
    t_label, t_score = text
    if v_label == t_label:
        return v_label, round(max(v_score, t_score), 3)
    fused = max(0.0, min(1.0, v_score * 0.7 + t_score * 0.3))
    if fused > 0.60:
        return "positive", round(fused, 3)
    if fused < 0.38:
        return "negative", round(fused, 3)
    return "neutral", round(fused, 3)


def get_expression(label: str) -> str:
    """情感标签 → 数字人表情"""
    return {"positive": "happy", "neutral": "neutral", "negative": "concerned"}.get(label, "neutral")


def analyze_interaction_sentiment(query: str, response: str) -> dict:
    user_label, user_score = analyze_emotion(query)
    ai_label, ai_score = analyze_emotion(response)
    return {
        "user_emotion": user_label,
        "user_score": user_score,
        "ai_emotion": ai_label,
        "ai_score": ai_score,
        "overall": user_label,
    }
