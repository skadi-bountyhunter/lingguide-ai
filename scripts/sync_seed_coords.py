"""同步更新 SEED_SPOTS 种子文件里新增16个景点的坐标"""
import re

COORDS = {
    "灵山大照壁": (120.102499, 31.421388),
    "五明桥": (120.102248, 31.421749),
    "佛足坛": (120.101497, 31.422725),
    "五智门": (120.101292, 31.423055),
    "阿育王柱": (120.099261, 31.426188),
    "百子戏弥勒": (120.098844, 31.427190),
    "祥符禅寺": (120.098012, 31.427949),
    "佛教文化博览馆": (120.096477, 31.430194),
    "曼飞龙塔": (120.104609, 31.426070),
    "无尽意斋": (120.096987, 31.428768),
    "拈花广场": (120.077149, 31.421850),
    "梵天花海": (120.075421, 31.415904),
    "香月花街": (120.073636, 31.416822),
    "拈花堂": (120.073636, 31.416822),
    "五灯湖": (120.075312, 31.418665),
    "鹿鸣谷": (120.079449, 31.424319),
    "梵宫": (120.102420, 31.428218),
}

p = "app/api/spots.py"
src = open(p, encoding="utf-8").read()
updated = 0
for name, (lng, lat) in COORDS.items():
    # 找到 name 对应块，替换其后的 lng/lat 行
    # 模式: "name": "XXX", ... 后面首个 "lng": ..., "lat": ...
    pat = re.compile(
        r'("name":\s*"' + re.escape(name) + r'".*?"lng":\s*)[0-9.]+,\s*"lat":\s*([0-9.]+)',
        re.DOTALL,
    )
    # 更安全：分两步，匹配 name 后到 lng 之间的首个 lng/lat
    idx = src.find(f'"name": "{name}"')
    if idx == -1:
        print(f"  [skip] {name} not found")
        continue
    lng_idx = src.find('"lng":', idx)
    lat_idx = src.find('"lat":', lng_idx)
    # 替换 lng 值
    m_lng = re.match(r'"lng":\s*([0-9.]+)', src[lng_idx:lng_idx+40])
    m_lat = re.match(r'"lat":\s*([0-9.]+)', src[lat_idx:lat_idx+40])
    if not m_lng or not m_lat:
        print(f"  [fail] {name}")
        continue
    src = src[:lng_idx] + f'"lng": {lng}, ' + src[lng_idx+m_lng.end():]
    # lat 位置保持不变（lat 在 lng 之后单独）
    # 重新定位 lat
    lat_idx = src.find('"lat":', lng_idx)
    m_lat2 = re.match(r'"lat":\s*([0-9.]+)', src[lat_idx:lat_idx+40])
    src = src[:lat_idx] + f'"lat": {lat},' + src[lat_idx+m_lat2.end():]
    updated += 1
    print(f"  [ok] {name} -> {lng}, {lat}")

open(p, "w", encoding="utf-8").write(src)
print(f"\n共更新种子文件 {updated} 个景点坐标")