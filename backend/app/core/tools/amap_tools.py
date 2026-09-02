"""高德开放平台 Skill 工具集

把高德 REST 能力封装成 OpenAI function-calling (tool calling) 兼容的单元，
供 LLM agent 自主决定调用时机。底层走 Web 服务 REST（非前端 JS API key）。

依赖配置：settings.amap_web_key（Web 服务类型 key）；未配置时工具返回提示，不抛异常。
"""
from typing import Any, Optional
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
import asyncio
import re
import time
import uuid
import httpx
from loguru import logger

from app.config import settings
from app.core.timing import elapsed_ms, started

AMAP_REST = "https://restapi.amap.com/v3"
AMAP_REST_V5 = "https://restapi.amap.com/v5"


class AmapRequestError(RuntimeError):
    """高德请求失败，仅保留可安全用于诊断的字段。"""

    def __init__(
        self,
        reason: str,
        status_code: int | None = None,
        *,
        provider_code: str | None = None,
        stage: str | None = None,
    ):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.provider_code = provider_code
        self.stage = stage


def _safe_provider_code(value: object) -> str | None:
    """仅接受高德非敏感的短错误码。"""
    code = str(value or "").strip()
    return code[:32] if code and re.fullmatch(r"[A-Za-z0-9_-]+", code) else None


_http_client: httpx.AsyncClient | None = None
_weather_cache: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()


def _get_http_client() -> httpx.AsyncClient:
    """懒加载共享 HTTP 客户端，避免每次天气请求重复建立连接池。"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
    return _http_client


async def close_http_client() -> None:
    """关闭共享客户端；应用关闭或测试清理时调用。"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def clear_weather_cache() -> None:
    """清理进程内天气缓存，供测试和配置变更使用。"""
    _weather_cache.clear()


# ---------------------------------------------------------------------------
# OpenAI tool schema —— LLM 据此判断"何时调用、传什么参数"
# ---------------------------------------------------------------------------
AMAP_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "amap_weather",
            "description": (
                "查询指定城市/景区的实况天气与近期预报。当游客询问天气、温度、是否需要带伞/加衣、"
                "适合不适合出行、体感冷热等与气象相关的问题时调用。"
                "参数 city 可传城市名、区县名或景点名（如'无锡'、'无锡滨湖区'、'灵山胜境'），内部会自动解析为区域编码。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市/区县/景点名称，如 '无锡'、'杭州西湖区'、'灵山胜境'。询问本景区天气时统一传 '灵山胜境'，不要传福建同名地点。",
                    },
                    "scope": {
                        "type": "string",
                        "description": "可选的上级城市约束。查询本项目景区灵山胜境时传 '无锡'，避免高德把同名/近似地点解析到福建。",
                    },
                    "extensions": {
                        "type": "string",
                        "enum": ["base", "all"],
                        "description": "base=仅实况；all=实况+未来三天预报。默认 all。",
                    },
                },
                "required": ["city"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# 底层调用
# ---------------------------------------------------------------------------
async def _amap_get(
    url: str,
    params: dict[str, str],
    timeout: float = 8.0,
    *,
    stage: str | None = None,
) -> Optional[dict]:
    """GET 高德 REST，失败时仅暴露非敏感诊断信息。"""
    started_at = time.perf_counter()
    request_stage = stage or url.rsplit("/", 1)[-1]
    client = _get_http_client()
    try:
        response = await client.get(url, params=params, timeout=timeout)
        if response.status_code == 429:
            raise AmapRequestError("http_429", response.status_code, stage=request_stage)
        if response.status_code >= 500:
            raise AmapRequestError(f"http_{response.status_code}", response.status_code, stage=request_stage)
        if response.status_code >= 400:
            raise AmapRequestError(f"http_{response.status_code}", response.status_code, stage=request_stage)
        try:
            data = response.json()
        except (ValueError, TypeError) as exc:
            raise AmapRequestError("invalid_json", stage=request_stage) from exc
        if not isinstance(data, dict):
            raise AmapRequestError("invalid_response", stage=request_stage)
        if "status" in data and str(data.get("status")) != "1":
            raise AmapRequestError(
                "provider_error",
                provider_code=_safe_provider_code(data.get("infocode")),
                stage=request_stage,
            )
        return data
    except AmapRequestError:
        raise
    except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
        raise AmapRequestError("timeout", stage=request_stage) from exc
    except httpx.RequestError as exc:
        raise AmapRequestError("connection_error", stage=request_stage) from exc
    finally:
        logger.debug(
            f"高德请求完成 stage={request_stage} "
            f"elapsed_ms={int((time.perf_counter() - started_at) * 1000)}"
        )


SCENIC_ALIASES = (
    "灵山", "灵山景区", "灵山胜境", "灵山胜境景区", "灵山大佛", "灵山大佛景区", "无锡灵山",
)
FOREIGN_LINGSHAN_PREFIXES = (
    "福建", "福州", "闽侯", "贵州", "广西", "北京", "河南", "浙江", "山东", "安徽", "湖北", "湖南",
    "四川", "重庆", "云南", "陕西", "山西", "河北", "辽宁", "吉林", "黑龙江", "广东", "海南",
    "甘肃", "青海", "宁夏", "新疆", "西藏", "内蒙古", "天津", "上海",
)
SCENIC_CONTEXT_TERMS = frozenset({
    "景区", "本景区", "该景区", "此景区", "当前景区", "这个景区", "我们景区", "景区内",
    "这里", "这儿", "这边", "那里", "那儿", "那边", "当地", "本地", "当前位置", "所在地",
    "现场", "附近", "周边", "园区", "本园区", "园内", "本园内", "景点", "本景点", "当前景点",
})
_LOCATION_CONTEXT_SUFFIXES = (
    "会不会", "要不要", "不适合", "今天", "明天", "后天", "现在", "当前", "此刻", "近日",
    "适合", "需要", "是否", "可以", "附近", "周边", "会", "要",
)


def is_foreign_lingshan(value: str) -> bool:
    """识别明确外地灵山，避免误改用户指定的外地地点。"""
    compact = str(value or "").strip().replace(" ", "")
    return any(f"{prefix}灵山" in compact for prefix in FOREIGN_LINGSHAN_PREFIXES)


def _strip_location_context(value: str) -> str:
    """反复清理地点后的时间、语气和位置泛称。"""
    candidate = value.rstrip("的").strip()
    changed = True
    while candidate and changed:
        changed = False
        for suffix in _LOCATION_CONTEXT_SUFFIXES:
            if candidate.endswith(suffix):
                candidate = candidate[:-len(suffix)].rstrip("的").strip()
                changed = True
                break
    return candidate


def is_scenic_context(city: str) -> bool:
    """判断地点是否为本景区语境中的泛称，而非可独立地理编码的城市。"""
    compact = str(city or "").strip().replace(" ", "")
    return compact in SCENIC_CONTEXT_TERMS or _strip_location_context(compact) in SCENIC_CONTEXT_TERMS


def _normalize_location(city: str, scope: Optional[str] = None) -> tuple[str, Optional[str], bool]:
    """规范化地点；返回查询名、城市约束和是否为本项目景区。"""
    query = str(city or "").strip()
    compact = query.replace(" ", "")
    if is_scenic_context(compact):
        return settings.weather_default_city, settings.weather_default_scope, True
    # 只有明确的本项目别名才强制使用无锡约束，保留外地同名地点查询能力。
    candidate = _strip_location_context(compact)
    is_scenic = not is_foreign_lingshan(candidate) and (
        candidate in SCENIC_ALIASES
        or candidate.startswith("无锡灵山")
        or any(candidate == f"{alias}附近" for alias in SCENIC_ALIASES)
    )
    if is_scenic:
        return settings.weather_default_city, settings.weather_default_scope, True
    return query, (str(scope).strip() if scope and str(scope).strip() else None), False


async def _resolve_adcode(
    city: str,
    scope: Optional[str] = None,
    *,
    timeout: float | None = None,
) -> tuple[Optional[str], Optional[str]]:
    """城市/景点名 → (adcode, 完整地名)，本景区直接锁定无锡滨湖区。"""
    query, query_scope, is_scenic = _normalize_location(city, scope)
    if is_scenic:
        return settings.weather_default_adcode, f"{settings.weather_default_scope}{settings.weather_default_city}"
    params = {"key": settings.amap_web_key, "address": query}
    if query_scope:
        params["city"] = query_scope
    geo = await _amap_get(
        f"{AMAP_REST}/geocode/geo",
        params,
        timeout=timeout if timeout is not None else settings.weather_geocode_timeout_seconds,
        stage="geocode",
    )
    geocodes = (geo or {}).get("geocodes") or []
    candidates = []
    for gc in geocodes:
        full = str(gc.get("formatted_address") or "")
        province = str(gc.get("province") or "")
        city_name = str(gc.get("city") or "")
        district = str(gc.get("district") or "")
        if is_scenic and not ("江苏" in province and "无锡" in city_name + full):
            continue
        score = 0
        if is_scenic and "滨湖" in district + full:
            score += 4
        if is_scenic and "灵山" in full:
            score += 3
        if query_scope and query_scope in city_name + full:
            score += 2
        candidates.append((score, gc, full))
    if not candidates:
        return None, None
    _, gc, full = max(candidates, key=lambda item: item[0])
    return gc.get("adcode"), full or gc.get("district") or gc.get("city") or query


# ---------------------------------------------------------------------------
# 工具执行分发
# ---------------------------------------------------------------------------
def _weather_key(city: str, scope: Optional[str], extensions: str) -> tuple[str, str, str]:
    query, query_scope, _ = _normalize_location(city, scope)
    return query, query_scope or "", extensions or "all"


def _copy_weather(value: dict[str, Any]) -> dict[str, Any]:
    """复制缓存结果，避免调用方修改缓存中的列表和元数据。"""
    return {
        **value,
        "live": dict(value.get("live") or {}) if value.get("live") else None,
        "casts": [dict(item) for item in value.get("casts") or []],
    }


def _cache_weather(key: tuple[str, str, str], value: dict[str, Any]) -> None:
    _weather_cache[key] = {**value, "cached_at": time.monotonic()}
    _weather_cache.move_to_end(key)
    while len(_weather_cache) > max(1, settings.weather_cache_max_entries):
        _weather_cache.popitem(last=False)


async def _fetch_weather(city: str, scope: Optional[str], extensions: str) -> dict[str, Any]:
    """在单一总 deadline 内完成地点、预报和实况请求。"""
    deadline = time.monotonic() + max(0.01, settings.weather_timeout_seconds)
    query, query_scope, _ = _normalize_location(city, scope)

    def remaining(budget: float) -> float:
        return max(0.01, min(budget, deadline - time.monotonic()))

    adcode, place_name = await _resolve_adcode(query, query_scope, timeout=remaining(settings.weather_geocode_timeout_seconds))
    if not adcode:
        raise AmapRequestError("location_not_found")

    forecasts: list[dict[str, Any]] = []
    if extensions != "base":
        forecast = await _amap_get(
            f"{AMAP_REST}/weather/weatherInfo",
            {"key": settings.amap_web_key, "city": adcode, "extensions": "all", "output": "JSON"},
            timeout=remaining(settings.weather_forecast_timeout_seconds),
            stage="forecast",
        )
        raw_forecasts = (forecast or {}).get("forecasts") or []
        forecasts = ((raw_forecasts[0].get("casts") if raw_forecasts else None) or [])

    live_weather = await _amap_get(
        f"{AMAP_REST}/weather/weatherInfo",
        {"key": settings.amap_web_key, "city": adcode, "extensions": "base", "output": "JSON"},
        timeout=remaining(settings.weather_live_timeout_seconds),
        stage="live",
    )
    live = None
    lives = (live_weather or {}).get("lives") or []
    if lives:
        item = lives[0]
        live = {
            "weather": item.get("weather", ""),
            "temperature": item.get("temperature", ""),
            "humidity": item.get("humidity", ""),
            "winddirection": item.get("winddirection", ""),
            "windpower": item.get("windpower", ""),
            "reporttime": item.get("reporttime", ""),
        }
    if not live and not forecasts:
        raise AmapRequestError("no_data")
    return {"place": place_name or query, "live": live, "casts": forecasts}


async def amap_weather(city: str, extensions: str = "all", scope: Optional[str] = None) -> str:
    """查询天气，和 REST/evidence 路径共用缓存及失败语义。"""
    result = await amap_weather_raw(city, scope, extensions=extensions)
    if result.get("status") != "ready":
        return f"{result.get('message', '天气查询暂不可用')}（不会使用过期或错误天气回答）"
    place_name = result.get("place", city)
    live = result.get("live") or {}
    casts = result.get("casts") or []
    lines = [f"【{place_name}天气】"]
    if live:
        lines.append(
            f"实况({live.get('reporttime','')})：{live.get('weather','')}，气温{live.get('temperature','')}°C，"
            f"湿度{live.get('humidity','')}%，{live.get('winddirection','')}风{live.get('windpower','')}级。"
        )
    for item in casts[:4]:
        lines.append(
            f"{item.get('date','')} 周{item.get('week','')}：白天{item.get('dayweather','')}"
            f"{item.get('daytemp','')}°C / 夜间{item.get('nightweather','')}{item.get('nighttemp','')}°C。"
        )
    return "\n".join(lines) if len(lines) > 1 else "暂无天气数据。"


async def amap_weather_evidence(city: str, scope: Optional[str] = None) -> dict:
    """返回统一 weather evidence，供 QueryCoordinator 和管理诊断使用。"""
    tool_call_id = f"tool_{uuid.uuid4().hex}"
    result = await amap_weather_raw(city, scope)
    status = result.get("status") or ("ready" if result.get("ok") else "error")
    as_of = result.get("as_of") or datetime.now(timezone.utc).isoformat()
    place = result.get("place", city)
    if status != "ready":
        return {
            "id": tool_call_id,
            "kind": "weather",
            "content": result.get("message", "天气查询失败"),
            "source": {"title": place, "type": "weather"},
            "confidence": 0.0,
            "quality_reason": f"weather_{status}",
            "provider": "amap",
            "tool_call_id": tool_call_id,
            "as_of": as_of,
            "expires_at": result.get("expires_at"),
            "status": status,
            "fallback_reason": result.get("reason", f"weather_{status}"),
            "metadata": result,
        }
    live = result.get("live") or {}
    content = f"{place}当前天气：{live.get('weather', '暂无')}，气温 {live.get('temperature', '暂无')}°C。"
    return {
        "id": tool_call_id,
        "kind": "weather",
        "content": content,
        "source": {"title": place, "type": "weather"},
        "confidence": 0.95,
        "quality_reason": "fresh_amap_weather",
        "provider": "amap",
        "tool_call_id": tool_call_id,
        "as_of": as_of,
        "expires_at": result.get("expires_at"),
        "status": "ready",
        "metadata": result,
    }


async def amap_weather_raw(
    city: str,
    scope: Optional[str] = None,
    *,
    extensions: str = "all",
) -> dict:
    """结构化天气查询（供 REST、前端卡片和 LLM 工具共用）。

    只缓存成功结果；stale 仅用于诊断/REST 展示，调用方不得将其作为回答证据。
    """
    started_at = started()
    query, query_scope, _ = _normalize_location(city, scope)
    key = _weather_key(query, query_scope, extensions)
    now = time.monotonic()
    cached = _weather_cache.get(key)
    if cached:
        age = now - float(cached.get("cached_at", now))
        if age <= settings.weather_cache_ttl_seconds:
            value = _copy_weather(cached)
            value.update({
                "ok": True,
                "status": "ready",
                "message": "",
                "reason": "fresh_cache",
                "cache_hit": True,
                "latency_ms": elapsed_ms(started_at),
            })
            return value

    if not settings.amap_web_key:
        return {
            "place": query,
            "ok": False,
            "status": "error",
            "live": None,
            "casts": [],
            "message": "天气服务未配置",
            "reason": "missing_api_key",
            "cache_hit": False,
            "latency_ms": elapsed_ms(started_at),
        }

    provider_code = None
    failed_stage = None
    try:
        value = await asyncio.wait_for(
            _fetch_weather(query, query_scope, extensions),
            timeout=max(0.01, settings.weather_timeout_seconds),
        )
        as_of = datetime.now(timezone.utc).isoformat()
        value.update({
            "ok": True,
            "status": "ready",
            "message": "",
            "reason": "fresh_provider",
            "as_of": as_of,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=settings.weather_cache_ttl_seconds)).isoformat(),
            "cache_hit": False,
            "latency_ms": elapsed_ms(started_at),
        })
        _cache_weather(key, value)
        return _copy_weather(value)
    except AmapRequestError as exc:
        reason = exc.reason
        provider_code = exc.provider_code
        failed_stage = exc.stage
        logger.warning(
            f"天气查询失败 reason={reason} stage={failed_stage or 'unknown'} "
            f"provider_code={provider_code or 'none'}"
        )
    except (asyncio.TimeoutError, httpx.TimeoutException):
        reason = "timeout"
    except Exception as exc:
        logger.warning(f"天气查询异常 reason=unexpected_error type={type(exc).__name__}")
        reason = "unexpected_error"

    if cached:
        age = now - float(cached.get("cached_at", now))
        if age <= settings.weather_cache_ttl_seconds + settings.weather_stale_window_seconds:
            stale = _copy_weather(cached)
            stale.update({
                "ok": False,
                "status": "stale",
                "message": "天气服务暂不可用，已有天气数据可能已过期",
                "reason": reason,
                "provider_code": provider_code,
                "stage": failed_stage,
            })
            return stale
    return {
        "place": (cached or {}).get("place", query),
        "ok": False,
        "status": "error",
        "live": None,
        "casts": [],
        "message": "天气暂无可用数据，请稍后重试" if reason == "no_data" else "天气服务暂不可用，请稍后重试",
        "reason": reason,
        "provider_code": provider_code,
        "stage": failed_stage,
    }


# 工具名 → 执行函数 的路由表
TOOL_HANDLERS = {
    "amap_weather": amap_weather,
}


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """执行 LLM 决定调用的工具，返回字符串结果。未知工具返回错误提示。"""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"未知工具：{name}"
    try:
        return await handler(**(arguments or {}))
    except TypeError as e:
        logger.warning(f"工具 {name} 参数错误：{e}")
        return f"工具 {name} 参数错误：{e}"
    except Exception as e:
        logger.warning(f"工具 {name} 执行异常：{e}")
        return f"工具 {name} 执行异常：{e}"