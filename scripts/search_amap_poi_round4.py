"""第四轮：最后一轮，用 AutoComplete 联想 + 极宽关键词搜剩余4个"""
import json, time, websocket, requests

CDP = "http://localhost:9222"
AMAP_KEY = "7e482d00f4ea9eb68b5c4b666ad9cdcf"
SECURITY = "76fb12864890353caef1eaeddcaad565"

SPOTS = [
    ("阿育王柱", ["阿育王柱", "阿育王柱古石柱 无锡", "阿育王"]),
    ("佛教文化博览馆", ["佛教文化博览馆", "灵山 博览馆", "灵山胜境 博览馆", "无锡佛文化博览 马山", "灵山 佛教文化"]),
    ("拈花堂", ["拈花堂 无锡", "拈花湾 拈花堂 禅", "拈花湾 禅堂"]),
    ("拈花广场", ["拈花广场", "拈花湾 拈花广场", "拈花微笑 雕塑", "拈花湾 广场"]),
]

class CdpClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url); self.mid = 0
    def call(self, method, params=None):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params or {}}))
        while True:
            obj = json.loads(self.ws.recv())
            if obj.get("id") == self.mid:
                return obj.get("result", {})

def get_page_ws():
    tabs = requests.get(f"{CDP}/json/list").json()
    page = next((t for t in tabs if t["type"] == "page"), None)
    return page["webSocketDebuggerUrl"]

def main():
    cdp = CdpClient(get_page_ws())
    cdp.call("Runtime.enable"); cdp.call("Page.enable")
    cdp.call("Page.navigate", {"url": "about:blank"}); time.sleep(0.5)
    inject = f"""
    (async () => {{
      window._AMapSecurityConfig = {{ securityJsCode: '{SECURITY}' }};
      await new Promise((res, rej) => {{
        const s = document.createElement('script');
        s.src = 'https://webapi.amap.com/maps?v=2.0&key={AMAP_KEY}&plugin=AMap.PlaceSearch';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      }});
      window.__done = false; window.__results = [];
      const spots = {json.dumps(SPOTS, ensure_ascii=False)};
      (async () => {{
        for (const [name, kws] of spots) {{
          const all = [];
          for (const kw of kws) {{
            const ps = new AMap.PlaceSearch({{ city:'无锡', citylimit:false, pageSize:5 }});
            const pois = await new Promise(res => ps.search(kw, (status, result) => {{
              if (status === 'complete' && result.poiList && result.poiList.pois) res(result.poiList.pois);
              else res([]);
            }}));
            for (const p of pois) all.push({{ kw, name:p.name, loc:p.location.toString(), address:p.address||'' }});
          }}
          window.__results.push({{ name, candidates: all }});
        }}
        window.__done = true;
      }})();
      return 'started';
    }})()
    """
    cdp.call("Runtime.evaluate", {"expression": inject, "awaitPromise": True, "returnByValue": True})
    for _ in range(120):
        time.sleep(1)
        v = cdp.call("Runtime.evaluate", {"expression": "({done:window.__done,n:(window.__results||[]).length})", "returnByValue": True})
        val = v.get("result", {}).get("value", {})
        print("poll:", val)
        if val.get("done"): break
    r = cdp.call("Runtime.evaluate", {"expression": "JSON.stringify(window.__results)", "returnByValue": True})
    open("E:/ruanjianbei/uploads/amap_poi_round4.json","w",encoding="utf-8").write(r["result"]["value"])
    print("written round4")

if __name__ == "__main__":
    main()