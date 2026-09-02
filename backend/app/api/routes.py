"""路线管理 API — 游客端预设经典路线（后台可编辑，游客端只读）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict
from typing import List

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models.route import Route
from app.core.locales import SPOT_TRANSLATIONS, normalize_locale, translate_tags

router = APIRouter(prefix="/api/routes", tags=["路线"])


# ===== Pydantic 模型 =====

class RouteCreate(BaseModel):
    title: str
    icon: str = "📍"
    duration: str = ""
    distance: str = ""
    difficulty: str = ""
    desc: str = ""
    spots: List[str] = []
    tags: List[str] = []
    tip: str = ""
    sort_order: int = 0


class RouteUpdate(BaseModel):
    title: str | None = None
    icon: str | None = None
    duration: str | None = None
    distance: str | None = None
    difficulty: str | None = None
    desc: str | None = None
    spots: List[str] | None = None
    tags: List[str] | None = None
    tip: str | None = None
    sort_order: int | None = None


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    icon: str
    duration: str
    distance: str
    difficulty: str
    desc: str
    spots: List[str] = []
    tags: List[str] = []
    tip: str
    sort_order: int
    display_title: str = ""
    display_duration: str = ""
    display_distance: str = ""
    display_difficulty: str = ""
    display_desc: str = ""
    display_spots: List[str] = []
    display_tags: List[str] = []
    display_tip: str = ""


_ROUTE_ONLY_SPOT_TRANSLATIONS = {
    "杏坛广场": {"en": "Xingtan Square", "ja": "杏壇広場", "ko": "행단 광장"},
    "灵山禅意园": {"en": "Lingshan Zen Garden", "ja": "霊山禅庭園", "ko": "링산 선 정원"},
    "太湖观景台": {"en": "Taihu Viewing Platform", "ja": "太湖展望台", "ko": "타이후 전망대"},
    "灵山素食体验": {"en": "Lingshan Vegetarian Experience", "ja": "霊山精進料理体験", "ko": "링산 채식 체험"},
    "素食馆": {"en": "Vegetarian Restaurant", "ja": "精進料理店", "ko": "채식 식당"},
}

_ROUTE_TRANSLATIONS = {
    "佛韵深度游": {
        "en": ("Buddhist Heritage Tour", "Easy", "Explore Lingshan's Buddhist heritage through its landmark statues, palaces, and sacred architecture.", "Morning visits are recommended to avoid peak crowds."),
        "ja": ("仏教文化探訪ルート", "やさしい", "大仏や梵宮、壇城を巡り、霊山の荘厳な仏教文化に触れるルートです。", "混雑を避けるため、午前中の観光がおすすめです。"),
        "ko": ("불교 문화 심층 코스", "쉬움", "대불과 범궁, 단성을 둘러보며 링산의 장엄한 불교 문화를 만나는 경로입니다.", "혼잡을 피하려면 오전 방문을 권장합니다."),
    },
    "山水揽胜游": {
        "en": ("Scenic Nature Tour", "Moderate", "Enjoy waterside scenery, gardens, and relaxed walks through Lingshan's natural landscape.", "Rainy days offer a distinctive misty landscape."),
        "ja": ("山水景観ルート", "普通", "水辺や庭園を歩き、霊山の穏やかな自然景観を楽しむルートです。", "雨の日には趣のある霞んだ景色を楽しめます。"),
        "ko": ("산수 경관 코스", "보통", "물가와 정원을 거닐며 링산의 여유로운 자연 풍경을 즐기는 경로입니다.", "비 오는 날에는 운치 있는 안개 풍경을 볼 수 있습니다."),
    },
    "亲子欢乐游": {
        "en": ("Family Discovery Tour", "Easy", "A relaxed family route combining performances, culture, food, and pleasant walks.", "Check the Nine Dragons Bathing show schedule in advance."),
        "ja": ("家族で楽しむルート", "やさしい", "ショーや文化体験、食事、散策を家族で気軽に楽しめるルートです。", "九龍灌浴の上演時間を事前にご確認ください。"),
        "ko": ("가족 체험 코스", "쉬움", "공연과 문화 체험, 음식, 산책을 가족이 편하게 즐기는 경로입니다.", "구룡관욕 공연 시간을 미리 확인해 주세요."),
    },
    "建筑艺术游": {
        "en": ("Architecture and Art Tour", "Moderate", "Discover architectural highlights ranging from Tang-inspired halls to Tibetan Buddhist design.", "Photography is not allowed inside Brahma Palace."),
        "ja": ("建築芸術ルート", "普通", "唐代風の殿堂からチベット様式まで、霊山の多彩な建築を巡ります。", "梵宮内では撮影できません。"),
        "ko": ("건축 예술 코스", "보통", "당나라풍 전각부터 티베트 양식까지 링산의 다양한 건축을 둘러봅니다.", "범궁 내부에서는 사진 촬영이 금지됩니다."),
    },
    "禅意素心游": {
        "en": ("Zen and Vegetarian Tour", "Easy", "Slow down with quiet gardens, vegetarian cuisine, and peaceful walks.", "Vegetarian meals may require advance booking; arrive before 11:30."),
        "ja": ("禅と精進料理ルート", "やさしい", "静かな庭園と精進料理、穏やかな散策でゆったり過ごすルートです。", "精進料理は予約が必要な場合があります。11時30分前の到着がおすすめです。"),
        "ko": ("선과 채식 코스", "쉬움", "고요한 정원과 채식 요리, 편안한 산책으로 여유를 즐기는 경로입니다.", "채식 식사는 예약이 필요할 수 있으니 11시 30분 전에 도착해 주세요."),
    },
}


def _to_out(r: Route, locale: str | None = None) -> RouteOut:
    """ORM → 输出；canonical 字段不变，display 字段用于本地化展示。"""
    lang = normalize_locale(locale)
    translated = _ROUTE_TRANSLATIONS.get(r.title, {}).get(lang)
    title, difficulty, desc, tip = translated or (
        r.title, r.difficulty or "", r.desc or "", r.tip or "",
    )
    display_spots = [
        SPOT_TRANSLATIONS.get(name, {}).get(lang, {}).get("name")
        or _ROUTE_ONLY_SPOT_TRANSLATIONS.get(name, {}).get(lang, name)
        for name in r.spots_list
    ] if lang != "zh-CN" else r.spots_list
    return RouteOut(
        id=r.id, title=r.title, icon=r.icon or "", duration=r.duration or "",
        distance=r.distance or "", difficulty=r.difficulty or "", desc=r.desc or "",
        spots=r.spots_list, tags=r.tags_list, tip=r.tip or "", sort_order=r.sort_order or 0,
        display_title=title, display_duration=r.duration or "", display_distance=r.distance or "",
        display_difficulty=difficulty, display_desc=desc, display_spots=display_spots,
        display_tags=translate_tags(r.tags_list, lang), display_tip=tip,
    )


def _apply(data: RouteCreate | RouteUpdate, route: Route):
    """把请求体写入 ORM 对象（仅更新非 None 字段）"""
    for field in ("title", "icon", "duration", "distance", "difficulty", "desc",
                  "tip", "sort_order"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(route, field, val)
    for field in ("spots", "tags"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(route, f"{field}_list", val)


# ===== 公开接口（游客端） =====

@router.get("", response_model=List[RouteOut])
async def list_routes(db: AsyncSession = Depends(get_db), locale: str = "zh-CN"):
    """路线列表（按 sort_order 升序），展示字段按 locale 本地化。"""
    result = await db.execute(select(Route).order_by(Route.sort_order.asc(), Route.id.asc()))
    return [_to_out(r, locale) for r in result.scalars().all()]


@router.get("/{route_id}", response_model=RouteOut)
async def get_route(route_id: int, db: AsyncSession = Depends(get_db), locale: str = "zh-CN"):
    """按 ID 获取路线；展示字段按 locale 本地化。"""
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "路线不存在")
    return _to_out(route, locale)


# ===== 管理接口（后台 CRUD） =====

@router.post("", response_model=RouteOut, status_code=201)
async def create_route(
    data: RouteCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """新增路线"""
    existing = await db.execute(select(Route).where(Route.title == data.title))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "路线名已存在")
    route = Route()
    _apply(data, route)
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return _to_out(route)


@router.put("/{route_id}", response_model=RouteOut)
async def update_route(
    route_id: int,
    data: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """更新路线"""
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "路线不存在")
    if data.title and data.title != route.title:
        dup = await db.execute(select(Route).where(Route.title == data.title))
        if dup.scalar_one_or_none():
            raise HTTPException(400, "路线名已存在")
    _apply(data, route)
    await db.commit()
    await db.refresh(route)
    return _to_out(route)


@router.delete("/{route_id}")
async def delete_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """删除路线"""
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "路线不存在")
    await db.delete(route)
    await db.commit()
    return {"deleted": route_id}


# ===== 种子数据（首次启动表空时写入） =====

SEED_ROUTES = [
    {
        "title": "佛韵深度游", "icon": "🛕", "duration": "3.5h", "distance": "4.2km",
        "difficulty": "轻松",
        "desc": "深入感受灵山佛教文化的庄严与宁静，参拜大佛、朝圣梵宫、感悟禅意",
        "spots": ["灵山大佛", "梵宫", "五印坛城", "降魔浮雕"],
        "tags": ["佛教文化", "建筑艺术"],
        "tip": "建议上午前往，避开午后人流高峰", "sort_order": 1,
    },
    {
        "title": "山水揽胜游", "icon": "🌿", "duration": "4h", "distance": "5.8km",
        "difficulty": "适中",
        "desc": "漫步灵山秀水之间，尽享太湖之滨的自然风光与生态之美",
        "spots": ["九龙灌浴", "杏坛广场", "灵山禅意园", "太湖观景台"],
        "tags": ["自然风光", "历史古迹"],
        "tip": "雨天可欣赏烟雨灵山别样意境", "sort_order": 2,
    },
    {
        "title": "亲子欢乐游", "icon": "🎠", "duration": "3h", "distance": "3.1km",
        "difficulty": "轻松",
        "desc": "适合全家出行的轻松路线，寓教于乐，让孩子在游玩中感受传统文化",
        "spots": ["九龙灌浴", "五印坛城", "灵山素食体验", "菩提大道"],
        "tags": ["亲子游乐", "美食素斋"],
        "tip": "九龙灌浴表演每日多场，请提前规划时间", "sort_order": 3,
    },
    {
        "title": "建筑艺术游", "icon": "⛩️", "duration": "3h", "distance": "3.8km",
        "difficulty": "适中",
        "desc": "领略灵山胜境的建筑奇观，从唐代风格到藏式建筑的艺术之旅",
        "spots": ["梵宫", "五印坛城", "灵山大佛", "降魔浮雕"],
        "tags": ["建筑艺术", "佛教文化"],
        "tip": "梵宫内部禁止拍照，请用心感受", "sort_order": 4,
    },
    {
        "title": "禅意素心游", "icon": "🧘", "duration": "2.5h", "distance": "2.5km",
        "difficulty": "轻松",
        "desc": "放慢脚步，品素斋、听梵音、悟禅意，体验灵山的宁静与祥和",
        "spots": ["灵山禅意园", "素食馆", "菩提大道", "杏坛广场"],
        "tags": ["美食素斋", "自然风光"],
        "tip": "素斋需提前预约，建议11:30前到达", "sort_order": 5,
    },
]


async def seed_routes(db: AsyncSession):
    """表空时写入种子数据（在应用启动时调用）"""
    result = await db.execute(select(Route).limit(1))
    if result.scalar_one_or_none():
        return
    for item in SEED_ROUTES:
        route = Route()
        for k, v in item.items():
            if k in ("spots", "tags"):
                setattr(route, f"{k}_list", v)
            else:
                setattr(route, k, v)
        db.add(route)
    await db.commit()
