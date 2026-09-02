"""景区天气 API — 给前端天气卡片用，复用高德 Skill 底层（不走 LLM）"""
from fastapi import APIRouter, Query

from app.config import settings
from app.core.locales import normalize_locale, translate_weather_value
from app.core.tools import amap_tools

router = APIRouter(prefix="/api/weather", tags=["天气"])


@router.get("")
async def scenic_weather(
    locale: str = Query(default="zh-CN", description="界面语言"),
):
    """查询无锡灵山胜境天气（今日实况 + 未来几日预报）。"""
    data = await amap_tools.amap_weather_raw(
        settings.weather_default_city,
        settings.weather_default_scope,
    )
    lang = normalize_locale(locale)
    if not isinstance(data, dict) or lang == "zh-CN":
        return data

    projected = dict(data)
    live = dict(projected.get("live") or {})
    if live:
        live["weather"] = translate_weather_value(str(live.get("weather") or ""), lang)
        live["winddirection"] = translate_weather_value(str(live.get("winddirection") or ""), lang)
        projected["live"] = live
    casts = []
    for raw_cast in projected.get("casts") or []:
        cast = dict(raw_cast)
        for key in ("dayweather", "nightweather", "daywind", "nightwind"):
            cast[key] = translate_weather_value(str(cast.get(key) or ""), lang)
        casts.append(cast)
    projected["casts"] = casts
    projected["locale"] = lang
    return projected