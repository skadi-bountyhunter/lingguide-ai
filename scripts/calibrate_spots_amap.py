"""高德 POI 搜索校准景点坐标

用高德 Web 服务 POI 搜索，按景点名在无锡市范围内取首个 POI 的真实坐标，
替换手填的经纬度，消除地图标注偏移。

用法：
  python scripts/calibrate_spots_amap.py            # dry-run，仅打印对比
  python scripts/calibrate_spots_amap.py --apply    # 写回后端数据库
"""
import os
import sys
import json
import argparse
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

BACKEND = 'http://localhost:8000'


def load_amap_key() -> str:
    """从前端 .env 读取 VITE_AMAP_KEY（JS API key 与 Web 服务 key 通常一致）"""
    root = os.path.dirname(__file__) + '/..'
    for env_path in (root + '/frontend-visitor/.env', root + '/.env'):
        if not os.path.exists(env_path):
            continue
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('VITE_AMAP_KEY='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


AMAP_KEY = load_amap_key()


def poi_search(keywords: str, city: str = '无锡') -> dict:
    """高德 POI 关键字搜索（Web 服务 REST API）"""
    url = 'https://restapi.amap.com/v3/place/text'
    params = {
        'keywords': keywords,
        'city': city,
        'citylimit': 'true',
        'output': 'json',
        'offset': '5',
        'key': AMAP_KEY,
    }
    full = url + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def get_spots() -> list:
    with urllib.request.urlopen(f'{BACKEND}/api/spots', timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def update_spot(spot_id: int, lng: float, lat: float) -> bool:
    body = json.dumps({'lng': lng, 'lat': lat}).encode('utf-8')
    req = urllib.request.Request(
        f'{BACKEND}/api/spots/{spot_id}',
        data=body,
        method='PUT',
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return 200 <= resp.status < 300


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='写回后端数据库')
    args = ap.parse_args()

    if not AMAP_KEY:
        print('❌ 未在 .env 找到 VITE_AMAP_KEY')
        sys.exit(1)

    spots = get_spots()
    print(f'共 {len(spots)} 个景点 | 高德 Key: {AMAP_KEY[:8]}... | 模式: {"写回" if args.apply else "dry-run"}\n')
    print(f'{"景点":<8} | {"旧坐标":<20} | {"新坐标(POI)":<20} | {"POI名":<18} | 状态')
    print('-' * 95)

    for s in spots:
        name = s['name']
        old = f"{s.get('lng')},{s.get('lat')}" if s.get('lng') else '无'
        try:
            res = poi_search(name)
            if res.get('status') != '1':
                print(f'{name:<8} | {old:<20} | {"":<20} | {"":<18} | ❌ {res.get("info")}')
                continue
            pois = res.get('pois') or []
            if not pois:
                print(f'{name:<8} | {old:<20} | {"":<20} | {"":<18} | ❌ 无POI结果')
                continue
            poi = pois[0]
            loc = poi.get('location', '')
            if not loc:
                print(f'{name:<8} | {old:<20} | {"":<20} | {poi.get("name",""):<18} | ❌ POI无坐标')
                continue
            lng, lat = loc.split(',')
            lng, lat = float(lng), float(lat)
            new = f'{lng},{lat}'
            poi_name = poi.get('name', '')[:16]
            status = ''
            if args.apply:
                status = '✅ 已更新' if update_spot(s['id'], lng, lat) else '❌ 更新失败'
            print(f'{name:<8} | {old:<20} | {new:<20} | {poi_name:<18} | {status}')
        except Exception as e:
            print(f'{name:<8} | {old:<20} | {"":<20} | {"":<18} | ❌ {e}')


if __name__ == '__main__':
    main()
