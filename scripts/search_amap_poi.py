"""通过 CDP + 高德 PlaceSearch 查询各景点真实坐标（JS API 环境，规避 REST key 类型不符）"""
import json
import time
import websocket
import requests

CDP = "http://localhost:9222"
AMAP_KEY = "7e482d00f4ea9eb68b5c4b666ad9cdcf"
SECURITY = "76fb12864890353caef1eaeddcaad565"

SPOTS = [
    ("灵山大佛", "灵山大佛"),
    ("梵宫", "灵山梵宫"),
    ("九龙灌浴", "九龙灌浴"),
    ("五印坛城", "五印坛城"),
    ("降魔浮雕", "降魔浮雕"),
    ("菩提大道", "灵山菩提大道"),
    ("灵山大照壁", "灵山大照壁"),
    ("五明桥", "灵山五明桥"),
    ("佛足坛", "灵山佛足坛"),
    ("五智门", "灵山五智门"),
    ("阿育王柱", "灵山阿育王柱"),
    ("百子戏弥勒", "百子戏弥勒"),
    ("祥符禅寺", "祥符禅寺"),
    ("佛教文化博览馆", "灵山佛教文化博览馆"),
    ("曼飞龙塔", "灵山曼飞龙塔"),
    ("无尽意斋", "无尽意斋"),
    ("拈花广场", "拈花湾拈花广场"),
    ("梵天花海", "拈花湾梵天花海"),
    ("香月花街", "拈花湾香月花街"),
    ("拈花堂", "拈花湾拈花堂"),
    ("五灯湖", "拈花湾五灯湖"),
    ("鹿鸣谷", "拈花湾鹿鸣谷"),
]


class CdpClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url)
        self.mid = 0

    def call(self, method, params=None):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params or {}}))
        while True:
            raw = self.ws.recv()
            obj = json.loads(raw)
            if obj.get("id") == self.mid:
                return obj.get("result", {})


def get_page_ws():
    tabs = requests.get(f"{CDP}/json/list").json()
    page = next((t for t in tabs if t["type"] == "page"), None)
    if not page:
        requests.get(f"{CDP}/json/new?about:blank")
        tabs = requests.get(f"{CDP}/json/list").json()
        page = next(t for t in tabs if t["type"] == "page")
    return page["webSocketDebuggerUrl"]


def main():
    cdp = CdpClient(get_page_ws())
    cdp.call("Runtime.enable")
    cdp.call("Page.enable")
    cdp.call("Page.navigate", {"url": "about:blank"})
    time.sleep(0.5)

    inject = f"""
    (async () => {{
      window._AMapSecurityConfig = {{ securityJsCode: '{SECURITY}' }};
      await new Promise((res, rej) => {{
        const s = document.createElement('script');
        s.src = 'https://webapi.amap.com/maps?v=2.0&key={AMAP_KEY}&plugin=AMap.PlaceSearch,AMap.AutoComplete';
        s.onload = res; s.onerror = rej;
        document.head.appendChild(s);
      }});
      window.__done = false;
      window.__results = [];
      const spots = {json.dumps(SPOTS, ensure_ascii=False)};
      (async () => {{
        for (const [name, kw] of spots) {{
          try {{
            const ps = new AMap.PlaceSearch({{ city:'无锡', citylimit:true, pageSize:5 }});
            const pois = await new Promise((res) => ps.search(kw, (status, result) => {{
              if (status === 'complete' && result.poiList && result.poiList.pois) res(result.poiList.pois);
              else res([]);
            }}));
            if (pois.length) {{
              const top = pois.map(p => ({{ name:p.name, loc:p.location.toString(), address:p.address||'', type:p.type||'' }}));
              window.__results.push({{ name, kw, found: top }});
            }} else {{
              window.__results.push({{ name, kw, found: [] }});
            }}
          }} catch(e) {{
            window.__results.push({{ name, kw, error: String(e) }});
          }}
        }}
        window.__done = true;
      }})();
      return 'started';
    }})()
    """
    r = cdp.call("Runtime.evaluate", {"expression": inject, "awaitPromise": True, "returnByValue": True})
    print("inject:", r.get("result", {}).get("value"))

    for _ in range(90):
        time.sleep(1)
        v = cdp.call("Runtime.evaluate", {"expression": "({done:window.__done, n:(window.__results||[]).length})", "returnByValue": True})
        val = v.get("result", {}).get("value", {})
        print("  poll:", val)
        if val.get("done"):
            break

    r = cdp.call("Runtime.evaluate", {"expression": "JSON.stringify(window.__results)", "returnByValue": True})
    out = open("../uploads/amap_poi_results.json" if False else "E:/ruanjianbei/uploads/amap_poi_results.json", "w", encoding="utf-8")
    out.write(r["result"]["value"])
    out.close()
    print("\n=== 已写入 uploads/amap_poi_results.json ===")


if __name__ == "__main__":
    main()