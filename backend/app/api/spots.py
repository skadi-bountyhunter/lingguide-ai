"""景点管理 API — 景点详情卡片内容（后台可编辑，游客端只读）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import json

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models.spot import Spot
from app.core.locales import normalize_locale, project_spot

router = APIRouter(prefix="/api/spots", tags=["景点"])


# ===== Pydantic 模型 =====

class SpotCreate(BaseModel):
    name: str
    icon: str = ""
    image: str = ""
    desc: str = ""
    full_desc: str = ""
    tags: List[str] = []
    duration: str = ""
    distance: str = ""
    highlights: List[str] = []
    hours: str = ""
    ticket: str = ""
    tips: List[str] = []
    best_season: str = ""
    nearby: List[str] = []
    lng: Optional[float] = None
    lat: Optional[float] = None
    sort_order: int = 0


class SpotUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    image: str | None = None
    desc: str | None = None
    full_desc: str | None = None
    tags: List[str] | None = None
    duration: str | None = None
    distance: str | None = None
    highlights: List[str] | None = None
    hours: str | None = None
    ticket: str | None = None
    tips: List[str] | None = None
    best_season: str | None = None
    nearby: List[str] | None = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    sort_order: int | None = None


class SpotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    # 旧字段 name/desc/tags 保留；locale 下它们直接映射到展示值。
    name: str
    icon: str
    image: str
    desc: str
    full_desc: str
    tags: List[str] = []
    duration: str
    distance: str
    highlights: List[str] = []
    hours: str
    ticket: str
    tips: List[str] = []
    best_season: str
    nearby: List[str] = []
    lng: Optional[float] = None
    lat: Optional[float] = None
    sort_order: int
    canonical_name: str = ""
    display_name: str = ""
    display_desc: str = ""
    display_full_desc: str = ""
    display_tags: List[str] = []
    canonical_tags: List[str] = []
    display_highlights: List[str] = []
    display_tips: List[str] = []
    display_best_season: str = ""
    display_nearby: List[str] = []
    canonical_nearby: List[str] = []
    translation_status: str = "source"


def _to_out(s: Spot, locale: str | None = None) -> SpotOut:
    """ORM → 输出；未传 locale 时保持中文旧契约。"""
    projection = project_spot(s, locale)
    return SpotOut(
        id=s.id, name=projection["display_name"], icon=s.icon or "", image=s.image or "",
        desc=projection["display_desc"], full_desc=projection["display_full_desc"],
        tags=projection["display_tags"], duration=s.duration or "", distance=s.distance or "",
        highlights=projection["display_highlights"], hours=s.hours or "", ticket=s.ticket or "",
        tips=projection["display_tips"], best_season=projection["display_best_season"],
        nearby=projection["display_nearby"], lng=s.lng, lat=s.lat, sort_order=s.sort_order or 0,
        canonical_name=projection["canonical_name"], display_name=projection["display_name"],
        display_desc=projection["display_desc"], display_full_desc=projection["display_full_desc"],
        display_tags=projection["display_tags"], canonical_tags=s.tags_list,
        display_highlights=projection["display_highlights"],
        display_tips=projection["display_tips"], display_best_season=projection["display_best_season"],
        display_nearby=projection["display_nearby"], canonical_nearby=s.nearby_list,
        translation_status=projection["translation_status"],
    )


def _apply(data: SpotCreate | SpotUpdate, spot: Spot):
    """把请求体写入 ORM 对象（仅更新非 None 字段）"""
    for field in ("name", "icon", "image", "desc", "full_desc", "duration",
                  "distance", "hours", "ticket", "best_season", "sort_order"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(spot, field, val)
    # 坐标可为 None（表示清除定位），独立处理
    if data.lng is not None:
        spot.lng = data.lng
    if data.lat is not None:
        spot.lat = data.lat
    for field in ("tags", "highlights", "tips", "nearby"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(spot, f"{field}_list", val)


# ===== 公开接口（游客端） =====

@router.get("", response_model=List[SpotOut])
async def list_spots(db: AsyncSession = Depends(get_db), locale: str = "zh-CN"):
    """景点列表（按 sort_order 升序）；locale 下展示字段本地化。"""
    normalized = normalize_locale(locale)
    result = await db.execute(select(Spot).order_by(Spot.sort_order.asc(), Spot.id.asc()))
    return [_to_out(s, normalized) for s in result.scalars().all()]


@router.get("/carousel")
async def carousel(db: AsyncSession = Depends(get_db), locale: str = "zh-CN"):
    """首页轮播（取前 4 个景点），保留 title/subtitle 点击字段兼容。"""
    normalized = normalize_locale(locale)
    result = await db.execute(select(Spot).order_by(Spot.sort_order.asc(), Spot.id.asc()).limit(4))
    cards = []
    for spot in result.scalars().all():
        projection = project_spot(spot, normalized)
        cards.append({
            "image": spot.image, "title": projection["display_name"],
            "subtitle": projection["display_desc"],
            "name": projection["display_name"], "canonical_name": projection["canonical_name"],
            "display_name": projection["display_name"], "display_desc": projection["display_desc"],
            "display_tags": projection["display_tags"], "translation_status": projection["translation_status"],
        })
    return cards


@router.get("/{name}", response_model=SpotOut)
async def get_spot(name: str, db: AsyncSession = Depends(get_db), locale: str = "zh-CN"):
    """按 canonical 中文名称获取景点详情。"""
    result = await db.execute(select(Spot).where(Spot.name == name))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(404, "景点不存在")
    return _to_out(spot, normalize_locale(locale))


# ===== 管理接口（后台 CRUD） =====

@router.post("", response_model=SpotOut, status_code=201)
async def create_spot(
    data: SpotCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """新增景点"""
    # 名称唯一性校验
    existing = await db.execute(select(Spot).where(Spot.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "景点名已存在")
    spot = Spot()
    _apply(data, spot)
    db.add(spot)
    await db.commit()
    await db.refresh(spot)
    return _to_out(spot)


@router.put("/{spot_id}", response_model=SpotOut)
async def update_spot(
    spot_id: int,
    data: SpotUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """更新景点"""
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(404, "景点不存在")
    # 改名时校验唯一性
    if data.name and data.name != spot.name:
        dup = await db.execute(select(Spot).where(Spot.name == data.name))
        if dup.scalar_one_or_none():
            raise HTTPException(400, "景点名已存在")
    _apply(data, spot)
    await db.commit()
    await db.refresh(spot)
    return _to_out(spot)


@router.delete("/{spot_id}")
async def delete_spot(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """删除景点"""
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(404, "景点不存在")
    await db.delete(spot)
    await db.commit()
    return {"deleted": spot_id}


# ===== 种子数据（首次启动表空时写入） =====

SEED_SPOTS = [
    {
        "name": "灵山大佛", "icon": "", "image": "/images/spots/spot_01.jpg",
        "desc": "通高88米的世界最高露天青铜释迦牟尼立像，右手施无畏印，左手施与愿印，庄严震撼",
        "tags": ["佛教文化", "建筑艺术"], "duration": "1.5h", "distance": "0.8km",
        "full_desc": "灵山大佛坐落于无锡马山秦履峰南侧，通高88米，其中佛体79米，莲花瓣9米，是迄今为止世界上最高的露天青铜释迦牟尼立像。大佛右手指天施「无畏印」，寓意众生无所畏惧；左手指地施「与愿印」，寓意心想事成。整座大佛采用锡青铜材料铸造，总用铜量达700吨，由1560块铜壁板拼接而成，每块铜壁板均经精密计算与打磨，确保大佛表面光滑如镜。\n\n大佛所在的小灵山，因唐玄西天取经归来见此山形酷似印度灵鹫山而得名。站在大佛脚下仰望，那份庄严与震撼令人肃然起敬；登临大佛基座远眺，太湖烟波浩渺，尽收眼底。",
        "highlights": ["88米世界最高青铜立像", "700吨锡青铜铸造", "无畏印与与愿印", "登基座远眺太湖"],
        "hours": "7:30 - 17:30（夏季）/ 7:30 - 17:00（冬季）",
        "ticket": "含在灵山胜境门票内（210元/人）",
        "tips": ["建议顺时针绕佛三圈祈福", "登基座需另购抱佛脚票（30元）", "大佛脚下可免费领取平安符", "日落时分光影效果最佳"],
        "best_season": "四季皆宜，秋季天高气爽最佳",
        "nearby": ["梵宫", "九龙灌浴", "降魔浮雕"], "sort_order": 1,
        "lng": 120.1032, "lat": 31.4247,
    },
    {
        "name": "梵宫", "icon": "✨", "image": "/images/spots/spot_02.jpg",
        "desc": "被誉为「东方卢浮宫」的佛教艺术殿堂，穹顶壁画超千平方米，琉璃墙面光彩夺目",
        "tags": ["建筑艺术", "佛教文化"], "duration": "1h", "distance": "0.5km",
        "full_desc": "灵山梵宫是一座集佛教文化、建筑艺术于一体的大型佛教艺术殿堂，总建筑面积达7万平方米，被誉为「东方卢浮宫」。梵宫整体建筑采用唐代风格，融合了中国传统木构建筑与佛教石窟艺术精髓，气势恢宏而不失典雅。\n\n步入梵宫，首先映入眼帘的是高达30余米的穹顶壁画，面积超过千平方米，描绘佛教经典故事，色彩斑斓、气势磅礴。琉璃墙面是世界最大的琉璃作品，超过2000平方米，光彩夺目。大型油画融合东西方艺术精髓，宝相阁珍藏各类佛教艺术珍品，每一处细节都令人叹为观止。",
        "highlights": ["千平方米穹顶壁画", "世界最大琉璃墙面", "大型东西方融合油画", "宝相阁佛教珍品"],
        "hours": "7:30 - 17:00（梵宫圣境演出：10:00 / 14:00）",
        "ticket": "含在灵山胜境门票内",
        "tips": ["梵宫内部禁止拍照摄像", "建议跟随免费讲解员参观", "圣境演出需提前30分钟入场", "穿鞋套入内（现场提供）"],
        "best_season": "室内景点，四季皆宜",
        "nearby": ["灵山大佛", "五印坛城", "菩提大道"], "sort_order": 2,
        "lng": 120.102420, "lat": 31.428218,
    },
    {
        "name": "九龙灌浴", "icon": "🐉", "image": "/images/spots/spot_03.jpg",
        "desc": "大型音乐动态群雕表演，莲花开启时九龙喷水，伴随悠扬佛乐，场面蔚为壮观",
        "tags": ["佛教文化", "亲子游乐"], "duration": "0.5h", "distance": "0.3km",
        "full_desc": "九龙灌浴是灵山胜境最具代表性的动态景观，根据佛教典籍中释迦牟尼诞生时九龙喷水沐浴的传说而建。大型音乐动态群雕由莲花、九龙和太子佛像组成，莲花直径达9米，六瓣莲花在音乐声中缓缓开启，金身太子佛像从中升起，九龙同时喷出高达数米的水柱，伴随悠扬佛乐，场面蔚为壮观。\n\n表演全程约6分钟，莲花开启前有佛经诵读，开启瞬间九龙齐喷水，水雾弥漫如临仙境。莲花闭合后，周围水池中的水被视为圣水，游客可用手触摸祈福。",
        "highlights": ["9米直径巨型莲花", "九龙齐喷水柱", "金身太子佛像", "圣水祈福体验"],
        "hours": "每日四场：10:00 / 11:30 / 14:00 / 16:00",
        "ticket": "含在灵山胜境门票内",
        "tips": ["提前10分钟到达正面观赏位", "表演约6分钟，请耐心等待", "可接圣水祈福（自备容器）", "带小朋友建议站前排"],
        "best_season": "春夏季节水景最美",
        "nearby": ["灵山大佛", "降魔浮雕", "菩提大道"], "sort_order": 3,
        "lng": 120.1003, "lat": 31.4235,
    },
    {
        "name": "五印坛城", "icon": "️", "image": "/images/spots/spot_04.jpg",
        "desc": "藏传佛教文化体验圣地，融合汉藏建筑风格，内部供奉各类佛教艺术珍品",
        "tags": ["建筑艺术", "历史古迹"], "duration": "0.5h", "distance": "0.4km",
        "full_desc": "五印坛城是灵山胜境中独具特色的藏传佛教文化体验圣地，整座建筑仿照藏族传统坛城形制建造，融合汉藏建筑风格，外观金碧辉煌、庄严华美。坛城共六层，总高度达31.8米，建筑面积约5000平方米。\n\n内部供奉各类藏传佛教艺术珍品，包括精美的唐卡、酥油花、坛城沙画等。每层设有不同的主题展示区，从藏传佛教的历史渊源到艺术传承，层层递进。顶层可俯瞰灵山胜境全景，远眺太湖风光。五印坛城不仅是宗教圣地，更是汉藏文化交融的生动见证。",
        "highlights": ["31.8米藏式坛城建筑", "唐卡与酥油花艺术", "坛城沙画展示", "顶层俯瞰灵山全景"],
        "hours": "7:30 - 17:00",
        "ticket": "含在灵山胜境门票内",
        "tips": ["可体验转经筒祈福", "内部有藏文化互动体验", "顶层观景台视野极佳", "尊重藏传佛教礼仪"],
        "best_season": "四季皆宜，冬季雪景别有韵味",
        "nearby": ["梵宫", "灵山大佛", "菩提大道"], "sort_order": 4,
        "lng": 120.0972, "lat": 31.4215,
    },
    {
        "name": "降魔浮雕", "icon": "🛕", "image": "/images/spots/spot_05.png",
        "desc": "大型浮雕群讲述释迦牟尼降魔成道故事，雕刻精美，感悟佛法智慧",
        "tags": ["佛教文化", "历史古迹"], "duration": "0.3h", "distance": "0.2km",
        "full_desc": "降魔浮雕位于灵山大佛基座北侧，是一组大型浮雕群，生动讲述了释迦牟尼在菩提树下降魔成道的佛教故事。浮雕全长约30米，高约8米，采用传统石雕工艺，人物造型生动传神，场景气势恢宏。\n\n浮雕以释迦牟尼端坐菩提树下禅定为画面中心，周围环绕着魔王波旬率领的魔军，或怒目圆睁、或张牙舞爪，与佛祖的安详从容形成鲜明对比。最终魔军溃散，佛祖悟道成佛。整组浮雕不仅是一件精美的艺术品，更蕴含着「以静制动、以善克恶」的深刻佛理。",
        "highlights": ["30米大型石雕群", "降魔成道故事", "传统石雕工艺", "佛理感悟"],
        "hours": "7:30 - 17:30（户外，全天可观赏）",
        "ticket": "含在灵山胜境门票内",
        "tips": ["建议结合大佛参观一并游览", "浮雕旁有解说牌可自助阅读", "清晨光线适合拍照", "可静坐感悟禅意"],
        "best_season": "四季皆宜，清晨光影最佳",
        "nearby": ["灵山大佛", "九龙灌浴", "菩提大道"], "sort_order": 5,
        "lng": 120.1038, "lat": 31.4252,
    },
    {
        "name": "菩提大道", "icon": "🌿", "image": "/images/spots/spot_06.jpg",
        "desc": "漫步菩提树下，感受禅意与宁静，沿途可欣赏太湖风光与园林景观",
        "tags": ["自然风光", "美食素斋"], "duration": "0.5h", "distance": "0.6km",
        "full_desc": "菩提大道是灵山胜境中最具禅意的漫步步道，全长约800米，两侧菩提树成荫，四季景色各异。大道以释迦牟尼在菩提树下悟道为文化主题，沿途设有禅意小品、石刻经文和休憩亭台，一步一景，处处体现东方禅学美学。\n\n漫步其间，可远眺太湖烟波，近赏园林景观。春日菩提新绿，夏日浓荫蔽日，秋日金叶满地，冬日枝影婆娑。大道中段设有素食体验区，可品尝灵山特色素斋，在禅意中感受味蕾的清净。大道尽头连接杏坛广场，是休憩与感悟的绝佳场所。",
        "highlights": ["800米菩提树荫步道", "禅意小品与石刻经文", "太湖远眺观景", "灵山特色素斋体验"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["素斋需提前预约（11:30前到达）", "建议穿舒适步行鞋", "沿途有休憩亭台可小坐", "秋末金叶铺地最为浪漫"],
        "best_season": "秋季（10-11月）金叶最美",
        "nearby": ["梵宫", "五印坛城", "九龙灌浴"], "sort_order": 6,
        "lng": 120.0985, "lat": 31.4220,
    },
    # ===== 灵山胜境其余 10 个景点（补充，源自示范景区结构化数据集） =====
    {
        "name": "灵山大照壁", "icon": "🏛️", "image": "/images/spots/spot_07.jpg",
        "desc": "「华夏第一壁」，长39.8米、高7米青石照壁，赵朴初题写鎏金「灵山胜境」四字",
        "tags": ["佛教文化", "建筑艺术"], "duration": "0.2h", "distance": "0km",
        "full_desc": "灵山大照壁是进入灵山胜境的第一道视觉屏障与景观节点，全长39.8米，最高处7米，最厚处1.9米，采用优质青石精心雕刻而成，整体造型恢弘大气，被誉为「华夏第一壁」。\n\n照壁正面鎏金大字「灵山胜境」由赵朴初先生亲笔题写，笔力遒劲，鎏金工艺让字体在阳光下熠熠生辉。北立面刻有赵朴初诗作《小灵山》，诗中将无锡小灵山与印度灵鹫山相媲美，彰显中华佛教文化的自信与底蕴。照壁两侧与碧波荡漾的太湖交相辉映，构成「湖光山色共一楼」的壮美景观，是景区入口处最具代表性的打卡景观。",
        "highlights": ["39.8米华夏第一壁", "赵朴初鎏金题字", "《小灵山》诗刻", "湖光壁影同框"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["入园首处打卡点，适合定格第一帧画面", "细读背面《小灵山》诗刻感受文化底蕴", "搭配太湖背景合影效果最佳", "如愿火车站装置是小众取景框"],
        "best_season": "四季皆宜，晴日鎏金最耀眼",
        "nearby": ["五明桥", "佛足坛", "菩提大道"], "sort_order": 7,
        "lng": 120.102499, "lat": 31.421388,
    },
    {
        "name": "五明桥", "icon": "🌉", "image": "/images/spots/spot_08.jpg",
        "desc": "五座汉白玉石拱桥横跨香水海，象征佛教五明智慧，是进入核心景区的必经之路",
        "tags": ["佛教文化", "建筑艺术"], "duration": "0.2h", "distance": "0.1km",
        "full_desc": "五明桥位于大照壁北侧，横跨香水海，由5座石拱桥并列排布而成，桥身采用汉白玉雕刻，桥面与桥栏均刻有精美佛教图案，造型规整大气，是进入核心景区的必经之路。\n\n五座石桥代表佛教中的五种核心智慧——声明（语言学）、因明（逻辑学）、内明（哲学）、医方明（医学）、工巧明（工艺学），寓意过桥即能开启智慧、走向觉悟。桥栏由优质汉白玉打造，雕刻着莲花、飞天、神兽等精美图案，线条流畅、栩栩如生。石桥倒映在香水海的碧波之中，如五条洁白玉带横卧水面，意境悠远。",
        "highlights": ["五座汉白玉石拱桥", "象征五明智慧", "莲花飞天雕刻", "香水海倒影"],
        "hours": "全天开放",
        "ticket": "无门票，免费通行",
        "tips": ["漫步过桥体悟五明智慧内涵", "拍摄石桥与香水海倒影同框", "桥面宽阔平坦适合驻足观赏", "感受水与建筑的禅意融合"],
        "best_season": "四季皆宜",
        "nearby": ["灵山大照壁", "佛足坛", "五智门"], "sort_order": 8,
        "lng": 120.102248, "lat": 31.421749,
    },
    {
        "name": "佛足坛", "icon": "👣", "image": "/images/spots/spot_09.jpg",
        "desc": "青铜铸造的巨型佛足印，复刻佛祖真身脚印，足心刻32种吉祥图案，朝圣核心节点",
        "tags": ["佛教文化", "历史古迹"], "duration": "0.2h", "distance": "0.2km",
        "full_desc": "佛足坛位于五明桥北侧、菩提大道起点，处于景区中轴线之上，与后方的五智门、灵山大佛遥相呼应，是核心朝圣节点。坛中巨型佛足印一对，左右对称摆放，每只足印长1.2米、宽0.6米，采用整块青铜铸造而成，表面经过特殊防腐处理，色泽温润。\n\n佛足坛复刻佛祖释迦牟尼真身脚印，足心刻有千辐轮相、宝瓶鱼纹等32种吉祥图案，每种图案都蕴含独特的佛教寓意，象征「佛足所至，佛光普照」。相传佛祖涅槃前特意留下双足印并嘱托弟子「佛足所至，即为佛地」，这对佛足也因此被称为「两足尊」，是佛教文化中「福德圆满、智慧无量」的象征。",
        "highlights": ["青铜铸造巨型佛足", "32种吉祥图案", "「两足尊」朝圣节点", "中轴线核心位置"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["瞻仰佛足寄托祈福心愿", "可亲手触摸足心吉祥图案", "细读32种吉祥瑞相寓意", "与后方五智门、大佛形成庄严格局"],
        "best_season": "四季皆宜",
        "nearby": ["五明桥", "五智门", "菩提大道"], "sort_order": 9,
        "lng": 120.101497, "lat": 31.422725,
    },
    {
        "name": "五智门", "icon": "⛩️", "image": "/images/spots/spot_10.jpg",
        "desc": "高16.8米、宽35米的汉白玉五门六柱石牌坊，象征五方五佛与六度波罗蜜，核心景区门户",
        "tags": ["佛教文化", "建筑艺术"], "duration": "0.2h", "distance": "0.3km",
        "full_desc": "五智门矗立在佛足坛北侧的景区中轴线上，高16.8米、宽35米，为五门六柱石牌坊造型，整体采用优质汉白玉雕刻而成，是区分景区外围区域与核心朝圣区域的重要标志。\n\n五门分别象征五方五佛，代表佛教的全域覆盖与普度众生；六柱代表佛教「六度波罗蜜」——布施、持戒、忍辱、精进、禅定、般若，门柱上刻有对应的佛教经文。门楣处饰有飞天、神兽、莲花等吉祥图案，造型栩栩如生。整座牌坊与后方的灵山大佛在同一直线上，穿过这道门，便正式从「凡俗之境」踏入「禅意圣地」，开启核心朝圣之旅。",
        "highlights": ["16.8米汉白玉牌坊", "五门象征五方五佛", "六柱六度波罗蜜", "夜间灯光氛围感"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["穿门祈福感受恢弘气势", "拍摄牌坊全景搭配蓝天绿树", "解读门柱经文与门楣图案", "夜间灯光点缀更具氛围感"],
        "best_season": "四季皆宜，夜间灯光别有韵味",
        "nearby": ["佛足坛", "菩提大道", "灵山大佛"], "sort_order": 10,
        "lng": 120.101292, "lat": 31.423055,
    },
    {
        "name": "阿育王柱", "icon": "🏺", "image": "/images/spots/spot_11.jpg",
        "desc": "通高16.9米、重180吨的花岗岩石柱，柱头四头狮子象征佛法四方传播，佛教东传地标",
        "tags": ["佛教文化", "历史古迹"], "duration": "0.2h", "distance": "0.4km",
        "full_desc": "阿育王柱位于降魔浮雕北侧、祥符禅寺正前方，矗立在景区中轴线之上，与灵山大佛、五智门形成一条直线，庄严肃穆。石柱通高16.9米，直径1.8米，总重量达180吨，采用整块优质花岗岩一次性雕刻而成。\n\n柱头雕刻四头朝向不同方向的狮子，分别朝向东南西北四方，象征佛法向世界各地传播，彰显佛教「和平、包容、普度」的核心精神。柱身表面打磨光滑，刻有「阿育王柱」四个大字及相关梵文经文。阿育王是古印度历史上最著名的弘扬佛法的国王，他统一印度后放下屠刀、笃信佛教，将佛法传播至世界各地，这根石柱也成为佛教从印度传入中国的重要历史象征。",
        "highlights": ["16.9米花岗岩石柱", "四狮柱头象征四方", "180吨整石雕刻", "佛教东传历史象征"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["瞻仰巨型石柱感受威严气势", "拍摄四狮柱头精美细节", "聆听阿育王弘扬佛法的故事", "与五智门、大佛形成中轴线呼应"],
        "best_season": "四季皆宜",
        "nearby": ["降魔浮雕", "祥符禅寺", "百子戏弥勒"], "sort_order": 11,
        "lng": 120.099261, "lat": 31.426188,
    },
    {
        "name": "百子戏弥勒", "icon": "😄", "image": "/images/spots/spot_12.jpg",
        "desc": "9吨青铜群雕，弥勒佛卧姿笑容可掬，身上百名孩童嬉戏，寓意多子多福、皆大欢喜",
        "tags": ["佛教文化", "亲子游乐"], "duration": "0.2h", "distance": "0.4km",
        "full_desc": "百子戏弥勒位于阿育王柱与祥符禅寺之间，是一组高3米、宽7.8米、总重达9吨的青铜群雕。弥勒佛呈卧姿，袒胸露腹、笑容满面，身上塑有百名嬉戏的孩童，形态各异、生动活泼。\n\n弥勒佛是佛教中的未来佛，象征着「欢喜、包容、慈悲」，百子环绕在弥勒佛身边，寓意「多子多福、家庭和睦、子孙满堂」，完美融合了佛教的「慈悲喜舍」与民间的祈福愿望。群雕中弥勒佛嘴角上扬，笑容憨厚可掬，尽显「大肚能容天下难容之事」的包容气度；百名孩童有的攀爬、有的嬉戏、有的挠弥勒佛肚皮，每个表情动作都独具特色，充满童趣，深受游客尤其是亲子家庭的喜爱。",
        "highlights": ["9吨青铜群雕", "百名孩童形态各异", "摸弥勒肚皮享福气", "亲子互动热门点位"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["触摸弥勒佛肚皮寓意享一生福气", "寻找百名孩童的不同姿态", "亲子互动拍照定格温馨瞬间", "感受民间艺术灵动之美"],
        "best_season": "四季皆宜",
        "nearby": ["阿育王柱", "祥符禅寺", "灵山大佛"], "sort_order": 12,
        "lng": 120.098844, "lat": 31.42719,
    },
    {
        "name": "祥符禅寺", "icon": "🛕", "image": "/images/spots/spot_13.png",
        "desc": "始建于唐贞观年间的千年古刹，玄奘弟子窥基开坛讲经，江南禅宗祖庭，12.8吨祥符禅钟",
        "tags": ["佛教文化", "历史古迹"], "duration": "0.5h", "distance": "0.5km",
        "full_desc": "祥符禅寺位于灵山胜境中轴核心、灵山大佛基座之下，四周绿树环绕，环境清幽，是景区内历史最悠久的人文景观。寺院占地约30亩，整体采用仿唐重檐歇山式建筑风格，布局完整，包含弥勒殿、大雄宝殿、钟楼、鼓楼。\n\n寺院始建于唐贞观年间，由玄奘法师的弟子窥基大师开坛讲经，北宋大中祥符年间正式更名为「祥符禅寺」，历经千年风雨洗礼，香火绵延不绝，是江南地区重要的千年禅宗祖庭。钟楼内悬挂着重12.8吨的「祥符禅钟」，钟声浑厚洪亮，响彻整个灵山山谷；寺内的六角井是唐代名泉，曾被茶圣陆羽品鉴，列为江南名泉之一；千年古银杏树龄超过千年，秋季金黄的树叶铺满寺院，意境绝美。",
        "highlights": ["唐贞观年间千年古刹", "玄奘弟子窥基开坛", "12.8吨祥符禅钟", "千年银杏与六角古井"],
        "hours": "全天开放，钟楼定时有钟声表演",
        "ticket": "含在灵山胜境门票内",
        "tips": ["礼佛祈福虔诚朝拜寄托心愿", "聆听祥符禅钟浑厚钟声", "秋季赏千年银杏金黄景致", "寺内需保持庄严肃穆禁止喧哗"],
        "best_season": "秋季（10-11月）银杏金黄最美",
        "nearby": ["阿育王柱", "百子戏弥勒", "灵山大佛"], "sort_order": 13,
        "lng": 120.098012, "lat": 31.427949,
    },
    {
        "name": "佛教文化博览馆", "icon": "🏛️", "image": "/images/spots/spot_14.jpg",
        "desc": "大佛座基内三层展馆，1万㎡展区，万佛殿9999尊小佛像与大佛「万佛朝宗」，免费讲解",
        "tags": ["佛教文化", "亲子游乐"], "duration": "0.5h", "distance": "0.6km",
        "full_desc": "佛教文化博览馆设于灵山大佛三层座基内，总建筑面积达10000㎡，是灵山博物馆的核心展区。馆内为三层框架结构，层高均超4米，空间开阔通透，配备智能导览屏、沉浸式投影、文物复刻展柜等现代化展陈设施，免费向游客开放。\n\n一层展厅以「五方五佛」与中国佛教四大名山为核心，陈列佛像复刻品、历代法器、名山文化卷轴，搭配实景沙盘；二层以时间为轴线，通过图文展板、沉浸式投影详细介绍世界佛教发展历程，其中「佛法东传」互动区可让游客通过触屏了解关键历史节点；三层为万佛殿，殿内采用鎏金装饰与暖光照明，9999尊灵山大佛真身小佛像整齐排布于殿内四周与穹顶，每尊按1:100比例复刻大佛造型，与室外的灵山大佛形成「上下呼应、万佛朝宗」的震撼格局。",
        "highlights": ["1万㎡三层展馆", "9999尊小佛万佛朝宗", "沉浸式投影体验", "免费讲解服务"],
        "hours": "8:00-17:00（冬季16:30闭馆）",
        "ticket": "免费参观（含在门票内）",
        "tips": ["免费讲解时段：9:30/11:00/14:30/16:00", "沉浸式投影每30分钟一场循环播放", "万佛殿可免费领取祈福卡写心愿", "禁止触摸文物与使用闪光灯"],
        "best_season": "室内景点，四季皆宜",
        "nearby": ["灵山大佛", "降魔浮雕", "祥符禅寺"], "sort_order": 14,
        "lng": 120.096394, "lat": 31.430364,
    },
    {
        "name": "曼飞龙塔", "icon": "🗼", "image": "/images/spots/spot_15.jpg",
        "desc": "复刻西双版纳曼飞龙白塔，主塔高16.9米九塔组合，南传佛教标志性建筑，异域风情地标",
        "tags": ["建筑艺术", "佛教文化"], "duration": "0.3h", "distance": "0.5km",
        "full_desc": "曼飞龙塔位于五印坛城北侧、香水海北岸的景观绿地上，与五印坛城隔岸相望，处于佛教三大语系建筑群落的核心位置。主塔高16.9米，底部为直径10米的圆形须弥座，由一座主塔和八座高约8米的小塔组成九塔组合，整体为南传佛教干栏式建筑风格。\n\n曼飞龙塔又称「白塔」，完全复刻了云南西双版纳曼飞龙白塔的形制与工艺，是南传佛教的标志性建筑之一。九塔组合象征着南传佛教的九种智慧，也代表着佛陀的九种功德。塔身以白色花岗岩为主要材质，表面雕刻着释迦牟尼佛成道图、阿罗汉像、莲花纹等南传佛教特色图案；塔刹采用鎏金铜质，呈锥形。这座佛塔的建造，让汉传、藏传、南传三大语系佛教建筑齐聚灵山，彰显了佛教文化的多元性与包容性。",
        "highlights": ["16.9米九塔组合", "复刻西双版纳白塔", "南传佛教标志性建筑", "三大语系建筑齐聚"],
        "hours": "全天开放",
        "ticket": "含在灵山胜境门票内",
        "tips": ["拍摄九塔组合搭配香水海背景", "对比汉传藏传南传三大语系建筑", "解读塔身雕刻图案与经文", "夜间灯光亮化夜景绝美"],
        "best_season": "四季皆宜，夜间灯光别有韵味",
        "nearby": ["五印坛城", "灵山梵宫", "菩提大道"], "sort_order": 15,
        "lng": 120.104609, "lat": 31.42607,
    },
    {
        "name": "无尽意斋", "icon": "🏡", "image": "/images/spots/spot_16.jpg",
        "desc": "赵朴初先生纪念馆，复刻其北京故居的四合院格局，陈列书法真迹，禅茶免费品鉴",
        "tags": ["历史古迹", "佛教文化"], "duration": "0.3h", "distance": "0.6km",
        "full_desc": "无尽意斋位于祥符禅寺西北侧、灵山大佛左下方的山林间，毗邻景区禅意休息区，环境清幽，远离景区主客流，是一处闹中取静的人文景观。占地600㎡，为典型的北京四合院风格建筑，坐北朝南，由正房、东西厢房、倒座房组成，复刻赵朴初先生北京故居的建筑格局与内饰风格。\n\n「无尽意」取自佛教经典《无尽意菩萨经》，象征着赵朴初先生对佛教文化传承、慈善事业发展的无尽初心与执着追求。正房为纪念馆核心展区，分为「生平事迹厅」「灵山渊源厅」「书法作品厅」三个部分，陈列着赵朴初先生与灵山胜境的往来书信、题字手稿、合影照片，以及数十幅书法真迹与复刻品，其书法兼具颜体的浑厚与柳体的挺拔。东西厢房设有临时展厅与禅意茶室，禅意茶室提供免费的禅茶品鉴，游客可在此静坐品茗，感受宁静。",
        "highlights": ["赵朴初先生纪念馆", "复刻北京故居四合院", "书法真迹与手稿陈列", "免费禅茶品鉴"],
        "hours": "9:00-17:00（冬季16:30闭馆）",
        "ticket": "免费参观",
        "tips": ["了解赵朴初与灵山的深厚渊源", "欣赏书法真迹感受艺术魅力", "禅意茶室免费品鉴灵山禅茶", "书法真迹禁止使用闪光灯拍照"],
        "best_season": "四季皆宜，山林清幽",
        "nearby": ["祥符禅寺", "灵山大佛", "降魔浮雕"], "sort_order": 16,
        "lng": 120.096987, "lat": 31.428768,
    },
    # ===== 拈花湾禅意小镇 6 个景点（补充，源自示范景区结构化数据集） =====
    {
        "name": "拈花广场", "icon": "🌸", "image": "/images/spots/spot_17.jpg",
        "desc": "拈花湾小镇门户，12米高「拈花微笑」鎏金青铜雕塑，源自迦叶拈花佛陀微笑典故",
        "tags": ["佛教文化", "建筑艺术"], "duration": "0.3h", "distance": "拈花湾入口",
        "full_desc": "拈花广场是进入拈花湾禅意小镇的第一站，也是小镇的灵魂节点，占地约8000㎡，整体设计融合中式禅意与日式简约风格，低调而不失雅致。广场中央矗立着高12米的「拈花微笑」主题雕塑，采用青铜铸造，表面鎏金处理，展现佛陀手持莲花、面带温和微笑的模样。\n\n「拈花微笑」源自佛教「迦叶拈花、佛陀微笑」的典故，象征「顿悟成佛」的禅理，传递「宁静、平和、向善」的生活理念，是拈花湾禅意文化的开篇与浓缩。广场地面采用青石板铺设，上面雕刻着简洁的莲花纹与禅意诗句，四周环绕景观绿植与中式景观灯，搭配小型水景喷泉。作为小镇的集散中心，广场周边设有游客服务中心、卫生间、便利店等配套设施，同时也是小镇大型开园仪式、禅意表演的举办场地。",
        "highlights": ["12米拈花微笑鎏金雕塑", "迦叶拈花典故", "中式禅意开园仪式", "小镇门户集散中心"],
        "hours": "9:00-21:30（冬季20:30闭园）",
        "ticket": "含在拈花湾门票内",
        "tips": ["与拈花微笑雕塑打卡合影", "9:30观看开园仪式（节假日14:30加演）", "夜间18:00景观灯点亮氛围感足", "节假日客流大建议错峰打卡"],
        "best_season": "四季皆宜，夜间灯光最美",
        "nearby": ["梵天花海", "香月花街", "拈花塔"], "sort_order": 17,
        "lng": 120.077149, "lat": 31.42185,
    },
    {
        "name": "梵天花海", "icon": "🌺", "image": "/images/spots/spot_18.png",
        "desc": "3万㎡自然花海，四季有花，格桑花波斯菊硫华菊轮替，1500米木质步道贯穿其中",
        "tags": ["自然风光", "亲子游乐"], "duration": "0.5h", "distance": "拈花湾西侧",
        "full_desc": "梵天花海是拈花湾禅意小镇的「自然名片」，位于小镇西侧，总占地约30000㎡，是小镇内规模最大的自然景观区。花海根据季节变化种植不同花卉，实现「四季有花、四季有景」。\n\n春季格桑花、波斯菊竞相绽放，粉色、白色、紫色的花朵铺满大地，宛如童话世界；夏季硫华菊、百日草盛开，色彩艳丽、生机盎然；秋季波斯菊再次绽放，搭配金黄的芦苇，尽显秋日诗意；冬季步道两侧绿植依旧翠绿。花海内的木质步道蜿蜒曲折，总长约1500米，贯穿整个花海，步道两侧设有休息长椅。花海中央设有一座木质景观凉亭，采用中式歇山顶设计，游客可在此静坐休憩，俯瞰整片花海，感受自然与禅意的完美融合。以「花伴禅心」为核心内涵，寓意「一花一世界，一叶一菩提」。",
        "highlights": ["3万㎡四季花海", "1500米木质步道", "中式歇山顶景观凉亭", "花伴禅心一花一世界"],
        "hours": "随小镇开放（9:00-21:30）",
        "ticket": "免费开放",
        "tips": ["四季拍不同花卉春季格桑最美", "漫步木质步道感受清新气息", "凉亭静坐俯瞰花海全景", "夏季蚊虫多建议做好防蚊"],
        "best_season": "春季（3-5月）格桑花海最美",
        "nearby": ["拈花广场", "香月花街", "鹿鸣谷"], "sort_order": 18,
        "lng": 120.075421, "lat": 31.415904,
    },
    {
        "name": "香月花街", "icon": "🏮", "image": "/images/spots/spot_19.png",
        "desc": "800米禅意商业街，白墙黛瓦飞檐翘角，禅意文创非遗手作特色餐饮，夜间灯笼氛围感足",
        "tags": ["美食素斋", "建筑艺术"], "duration": "1h", "distance": "拈花湾核心",
        "full_desc": "香月花街是拈花湾禅意小镇的「灵魂街巷」，北接拈花广场、南连五灯湖，贯穿小镇南北中轴线，街道总长约800米，宽8米，是小镇内最繁华的禅意商业街。两侧建筑为中式禅意风格，多为两层砖木结构，白墙黛瓦、飞檐翘角，门窗为雕花样式。\n\n街道以「禅意生活、慢享时光」为核心内涵，将商业与禅意文化深度融合，拒绝过度商业化。街道两侧的商铺各具特色，涵盖禅意文创、非遗手作、特色餐饮、禅茶品鉴等品类，没有喧嚣的叫卖声，只有静谧的氛围。非遗手作铺可体验剪纸、陶艺、木刻等传统技艺，禅意文创铺售卖佛珠、书签、香薰等特色产品，特色餐饮铺提供素面、禅茶、江南小吃等美食。飞檐翘角上悬挂的中式灯笼，夜间点亮后氛围感十足。",
        "highlights": ["800米禅意商业街", "非遗手作体验", "禅意文创与素斋", "夜间灯笼氛围感"],
        "hours": "9:30-21:00（部分餐饮至21:30）",
        "ticket": "免费开放，商铺消费自愿",
        "tips": ["体验剪纸陶艺木刻非遗手作", "品尝素面禅茶江南小吃", "夜间18:00灯笼点亮氛围感拉满", "不定时禅意巡游表演"],
        "best_season": "四季皆宜，夜间灯笼最美",
        "nearby": ["拈花广场", "拈花堂", "五灯湖"], "sort_order": 19,
        "lng": 120.073636, "lat": 31.416822,
    },
    {
        "name": "拈花堂", "icon": "🍵", "image": "/images/spots/spot_20.jpg",
        "desc": "1200㎡中式禅堂，提供禅坐抄经禅茶品鉴，源自拈花悟禅典故，小镇静心之地",
        "tags": ["佛教文化", "自然风光"], "duration": "0.5h", "distance": "香月花街中段",
        "full_desc": "拈花堂位于香月花街中段东侧，隐藏在绿植之中，环境清幽，远离街道喧嚣，是小镇内最具禅意的静心场所之一。占地约1200㎡，为中式禅堂建筑，单层砖木结构，白墙黛瓦、朱红门窗，屋顶为歇山顶设计，屋檐下悬挂着刻有「拈花堂」三字的木质匾额。\n\n拈花堂源自佛教「拈花悟禅」的典故，以「静心、修身、悟道」为核心内涵，传递「心无杂念、回归本真」的禅理。堂内设有禅坐区、抄经区、禅茶区：禅坐区摆放着数十把木质禅椅，游客可在此静坐冥想、聆听禅乐；抄经区提供经文手稿、毛笔、墨汁，游客可亲手抄写经文感悟禅理；禅茶区设有木质茶桌茶椅，提供免费禅茶品鉴，有专业人员讲解禅茶礼仪，体验「禅茶一味」的意境。每日还会举办小型禅意讲座，讲解禅意文化与生活哲学。",
        "highlights": ["1200㎡中式禅堂", "禅坐冥想聆听禅乐", "亲手抄经感悟禅理", "免费禅茶品鉴"],
        "hours": "9:30-19:00（冬季18:00闭馆）",
        "ticket": "免费开放",
        "tips": ["禅坐抄经禅茶均免费", "禅意讲座10:30/15:30各一场", "堂内需保持绝对安静手机静音", "建议穿着舒适素雅衣物"],
        "best_season": "室内景点，四季皆宜",
        "nearby": ["香月花街", "拈花广场", "五灯湖"], "sort_order": 20,
        "lng": 120.073435, "lat": 31.417260,
    },
    {
        "name": "五灯湖", "icon": "💡", "image": "/images/spots/spot_21.jpg",
        "desc": "5000㎡湖面，夜间《禅行》灯光秀核心场地，五灯象征五智，灯光倒映湖面如梦如幻",
        "tags": ["自然风光", "佛教文化"], "duration": "0.5h", "distance": "小镇南侧",
        "full_desc": "五灯湖是拈花湾禅意小镇的「水景核心」，位于小镇南侧、香月花街南端，湖面面积约5000㎡，是小镇内最大的水景景观区，也是小镇夜间灯光秀的核心举办场地。湖水清澈见底，湖底铺设鹅卵石，湖面设有木质栈道、景观桥、湖心亭等设施。\n\n五灯湖以「灯映禅心、湖光禅意」为核心内涵，五灯象征「五智」，呼应灵山胜境的五智文化，湖水象征「清净本心」，传递「心似湖水，澄澈无染」的禅理。湖中央设有大型灯光投影装置，四周安装有景观灯与水雾装置。最具特色的是夜间灯光秀，每日夜间灯光投影装置会投射出禅意图案、佛教经文，搭配水雾装置营造出如梦如幻的氛围；岸边景观灯点亮后，灯光倒映在湖水中，波光粼粼，美不胜收。夏季荷花盛开时，尽显江南水乡的柔美与禅意。",
        "highlights": ["5000㎡湖面水景", "夜间《禅行》灯光秀", "五灯象征五智", "灯光倒映如梦如幻"],
        "hours": "随小镇开放，灯光秀19:00/20:00各一场",
        "ticket": "免费开放",
        "tips": ["夜间观看《禅行》灯光秀提前30分钟占位", "白天漫步栈道赏荷花（夏季）", "湖心亭静坐感受湖光禅意", "禁止使用闪光灯拍摄灯光秀"],
        "best_season": "夏季（6-8月）荷花盛开最美",
        "nearby": ["香月花街", "拈花堂", "拈花广场"], "sort_order": 21,
        "lng": 120.075312, "lat": 31.418665,
    },
    {
        "name": "鹿鸣谷", "icon": "🌲", "image": "/images/spots/spot_22.jpg",
        "desc": "2万㎡山林景观区，植被覆盖率90%以上，香樟松柏翠竹茂密，小镇最静谧的自然氧吧",
        "tags": ["自然风光", "亲子游乐"], "duration": "0.5h", "distance": "小镇西侧",
        "full_desc": "鹿鸣谷位于拈花湾小镇西侧、梵天花海北侧，地处山林之间，是小镇内最静谧的自然景观区，远离主客流，山林植被茂密，空气清新。占地约20000㎡，核心为山林景观，种植着香樟、松柏、翠竹等多种绿植，植被覆盖率达90%以上。\n\n谷内设有木质步道，蜿蜒穿梭于山林之间，漫步其间，可聆听鸟鸣虫语、感受山风拂面，仿佛置身于天然氧吧。鹿鸣谷远离小镇的喧嚣商业区，是一处闹中取静的世外桃源，适合游客静心漫步、亲近自然、放松身心。谷内还点缀着禅意小品与休憩亭台，处处体现东方禅学美学，是深度感受「天人合一」自然意境的绝佳场所。",
        "highlights": ["2万㎡山林景观", "90%植被覆盖率", "天然氧吧静谧漫步", "禅意小品休憩亭台"],
        "hours": "随小镇开放（9:00-21:30）",
        "ticket": "免费开放",
        "tips": ["漫步山林步道呼吸清新空气", "远离喧嚣静心放松身心", "聆听鸟鸣虫语感受自然", "穿舒适步行鞋"],
        "best_season": "春夏季节绿意最浓",
        "nearby": ["梵天花海", "拈花广场", "香月花街"], "sort_order": 22,
        "lng": 120.079449, "lat": 31.424319,
    },
]


async def seed_spots(db: AsyncSession):
    """初始化或补充种子数据（在应用启动时调用）"""
    # 检查已有景点
    result = await db.execute(select(Spot))
    existing_spots = result.scalars().all()
    existing_names = {s.name for s in existing_spots}

    # 追加缺失的景点
    for item in SEED_SPOTS:
        if item["name"] not in existing_names:
            spot = Spot()
            for k, v in item.items():
                if k in ("tags", "highlights", "tips", "nearby"):
                    setattr(spot, f"{k}_list", v)
                else:
                    setattr(spot, k, v)
            db.add(spot)

    # 如果是空表，写入所有种子数据
    if not existing_names:
        await db.commit()
        return

    # 补充已存在但数据不完整的景点（字段为空时更新）
    for existing in existing_spots:
        for item in SEED_SPOTS:
            if item["name"] == existing.name:
                # 更新缺失的字段
                updates = {
                    k: v for k, v in item.items()
                    if k not in ("tags", "highlights", "tips", "nearby")
                    and getattr(existing, k, None) in (None, "")
                }
                for k, v in updates.items():
                    setattr(existing, k, v)

                # 更新缺失的列表字段
                for list_field in ("tags", "highlights", "tips", "nearby"):
                    existing_list = getattr(existing, f"{list_field}_list")
                    item_list = item.get(list_field, [])
                    if not existing_list and item_list:
                        setattr(existing, f"{list_field}_list", item_list)

    await db.commit()
