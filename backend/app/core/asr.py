"""语音识别模块 — 科大讯飞语音听写"""
import json
import base64
import hmac
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlencode
from loguru import logger

from app.config import settings
from app.core.locales import message, normalize_locale

IFLYTEK_HOST = "iat-api.xfyun.cn"
IFLYTEK_PATH = "/v2/iat"
IFLYTEK_URL = f"wss://{IFLYTEK_HOST}{IFLYTEK_PATH}"


def _build_iflytek_url() -> str:
    """构建科大讯飞鉴权 URL"""
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    # 签名字符串：host + date + method + path
    sign_str = f"host: {IFLYTEK_HOST}\ndate: {date}\nGET {IFLYTEK_PATH} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(
            settings.iflytek_api_secret.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()
    # 组装 authorization
    auth = base64.b64encode(
        f"api_key=\"{settings.iflytek_api_key}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{signature}\"".encode()
    ).decode()
    params = urlencode({
        "host": IFLYTEK_HOST,
        "date": date,
        "authorization": auth,
    })
    return f"{IFLYTEK_URL}?{params}"


def _wav_to_pcm(wav_bytes: bytes) -> bytes:
    """从 WAV 文件中提取 PCM 数据（跳过 44 字节头）"""
    # WAV: RIFF(4)+size(4)+WAVE(4)+fmt(4)+fmtSize(4)+fmtData(变长)+data(4)+dataSize(4)+data
    if wav_bytes[:4] == b'RIFF' and wav_bytes[8:12] == b'WAVE':
        # 找到 data chunk
        off = 12
        while off < len(wav_bytes) - 8:
            chunk_id = wav_bytes[off:off+4]
            chunk_size = int.from_bytes(wav_bytes[off+4:off+8], 'little')
            if chunk_id == b'data':
                return wav_bytes[off+8:off+8+chunk_size]
            off += 8 + chunk_size
    # 非 WAV 格式，当作裸 PCM
    return wav_bytes


async def _transcribe_iflytek(audio_bytes: bytes, language: str = "zh", locale: str = "zh-CN") -> str:
    """科大讯飞语音听写 WebSocket API — 分帧发送。讯飞当前实现仅兼容中文。"""
    if normalize_locale(locale) != "zh-CN":
        return f"[{message('asr_locale_unsupported', locale)}]"
    try:
        import websockets

        pcm = _wav_to_pcm(audio_bytes)
        if len(pcm) == 0:
            return ""

        url = _build_iflytek_url()
        results: list[str] = []
        business_args = {
            "language": "zh_cn",
            "domain": "iat",
            "accent": "mandarin",
            "ptt": 0,   # 不添加标点（前端自己处理）
        }

        async with websockets.connect(url, ping_interval=10, close_timeout=5) as ws:
            # 分帧发送 (每帧 1280 bytes)
            FRAME_SIZE = 1280
            frames = [pcm[i:i+FRAME_SIZE] for i in range(0, len(pcm), FRAME_SIZE)]

            for i, chunk in enumerate(frames):
                status = 0 if i == 0 else (2 if i == len(frames) - 1 else 1)
                frame_data: dict = {
                    "data": {
                        "status": status,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(chunk).decode(),
                    }
                }
                if i == 0:
                    frame_data["common"] = {"app_id": settings.iflytek_app_id}
                    frame_data["business"] = business_args

                await ws.send(json.dumps(frame_data))

            # 接收结果
            async for msg in ws:
                data = json.loads(msg)
                code = data.get("code", 0)
                d = data.get("data", {})
                if code != 0:
                    logger.error(f"讯飞 API 错误: code={code}, msg={data.get('message','')}")
                    break
                # 先提取结果，再检查是否结束（结果和status=2可能在同一帧）
                if "result" in d:
                    result = d["result"]
                    if result:
                        text = "".join(
                            w.get("cw", [{}])[0].get("w", "")
                            for w in result.get("ws", [])
                        )
                        if text:
                            results.append(text)
                if d.get("status") == 2:
                    break

        final = "".join(results) if results else ""
        logger.info(f"讯飞识别完成: chunks={len(frames)}, pcm_bytes={len(pcm)}, text_chars={len(final)}")
        return final if final else "[未识别到语音，请重试]"

    except Exception as e:
        logger.error(f"讯飞 ASR 错误: {e}")
        return f"[语音识别失败: {str(e)[:80]}]"


async def transcribe_audio(audio_bytes: bytes, language: str = "zh", locale: str = "zh-CN", **provider_options) -> str:
    """统一转录入口；locale 不再静默忽略，讯飞暂只支持中文并稳定返回提示。"""
    locale = normalize_locale(locale or language)
    if settings.asr_provider == "iflytek" and settings.iflytek_app_id:
        return await _transcribe_iflytek(audio_bytes, language, locale)
    return f"[{message('asr_not_configured', locale)}]"


async def transcribe_audio_stream(audio_bytes: bytes, locale: str = "zh-CN", **provider_options) -> str:
    return await transcribe_audio(audio_bytes, locale=locale, **provider_options)
