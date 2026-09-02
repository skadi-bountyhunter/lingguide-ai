"""语音合成模块 — Edge-TTS 为主，CosyVoice 为可选增强"""
import io
from typing import Optional
from loguru import logger

from app.config import settings
from app.core.locales import normalize_locale


async def synthesize_edge(text: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: float = 1.0) -> bytes:
    """使用 Edge-TTS 合成语音（免费、稳定）

    Args:
        text: 要合成的文本
        voice: 语音角色
        rate: 语速倍数

    Returns:
        MP3 音频字节流
    """
    import edge_tts

    delta = int((rate - 1) * 100)
    rate_str = f"+{delta}%" if delta >= 0 else f"{delta}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)

    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    return b"".join(audio_chunks)


EDGE_VOICE_BY_LOCALE = {
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-JennyNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


def voice_for_locale(locale: str | None, requested: str | None = None) -> str:
    """按 locale 选白名单 Edge voice；未知/非法 voice 不直接透传。"""
    lang = normalize_locale(locale)
    allowed = set(EDGE_VOICE_BY_LOCALE.values()) | set(VOICE_OPTIONS.values())
    if requested in allowed and (lang == "zh-CN" or str(requested).startswith(lang)):
        return requested
    return EDGE_VOICE_BY_LOCALE[lang]


async def synthesize(text: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: float = 1.0, locale: str = "zh-CN") -> bytes:
    """统一 TTS 接口；locale 决定默认白名单音色。"""
    voice = voice_for_locale(locale, voice)
    if settings.tts_provider == "cosyvoice":
        try:
            return await synthesize_cosyvoice(text, voice, rate)
        except Exception as e:
            logger.warning(f"CosyVoice 不可用，降级到 Edge-TTS: {e}")

    return await synthesize_edge(text, voice, rate)


async def synthesize_cosyvoice(text: str, voice: str = "default", rate: float = 1.0) -> bytes:
    """CosyVoice TTS（需要独立部署）"""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.cosyvoice_url}/tts",
            json={"text": text, "voice": voice, "speed": rate},
        )
        resp.raise_for_status()
        return resp.content


# 可选的声音角色映射
VOICE_OPTIONS = {
    "温柔女声": "zh-CN-XiaoxiaoNeural",      # 晓晓 - 温柔女声
    "知性女声": "zh-CN-XiaohanNeural",       # 晓涵 - 知性女声
    "稳重男声": "zh-CN-YunxiNeural",         # 云希 - 稳重男声
    "亲切男声": "zh-CN-YunyangNeural",       # 云扬 - 亲切男声
}
