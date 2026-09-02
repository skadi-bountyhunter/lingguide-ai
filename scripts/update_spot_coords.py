"""用高德实核坐标更新数据库 spots 表（不存在独立POI的景点用相邻地标坐标）"""
import asyncio
from app.core.database import async_session
from sqlalchemy import select
from app.models.spot import Spot

# 名称 → (lng, lat)
COORDS = {
    "灵山大佛": (120.096477, 31.430194),
    "梵宫": (120.102420, 31.428218),
    "九龙灌浴": (120.099984, 31.424601),
    "五印坛城": (120.103054, 31.424676),
    "降魔浮雕": (120.099569, 31.425559),
    "菩提大道": (120.101143, 31.423182),
    "灵山大照壁": (120.102499, 31.421388),
    "五明桥": (120.102248, 31.421749),
    "佛足坛": (120.101497, 31.422725),
    "五智门": (120.101292, 31.423055),
    "阿育王柱": (120.099261, 31.426188),
    "百子戏弥勒": (120.098844, 31.427190),
    "祥符禅寺": (120.098012, 31.427949),
    "佛教文化博览馆": (120.096477, 31.430194),  # 无独立POI，位于大佛座基内
    "曼飞龙塔": (120.104609, 31.426070),
    "无尽意斋": (120.096987, 31.428768),
    "拈花广场": (120.077149, 31.421850),  # 微笑广场=拈花微笑雕塑
    "梵天花海": (120.075421, 31.415904),
    "香月花街": (120.073636, 31.416822),
    "拈花堂": (120.073636, 31.416822),  # 无独立POI，香月花街中段
    "五灯湖": (120.075312, 31.418665),
    "鹿鸣谷": (120.079449, 31.424319),
}

async def main():
    async with async_session() as s:
        r = await s.execute(select(Spot))
        spots = r.scalars().all()
        updated = 0
        for sp in spots:
            if sp.name in COORDS:
                lng, lat = COORDS[sp.name]
                changed = sp.lng != lng or sp.lat != lat
                sp.lng = lng
                sp.lat = lat
                if changed:
                    updated += 1
                    print(f"  更新 {sp.name}: -> {lng}, {lat}")
        await s.commit()
        print(f"\n共更新 {updated} 个景点坐标")
asyncio.run(main())