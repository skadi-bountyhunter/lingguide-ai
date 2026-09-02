"""CDP 打开游客端路线页，截图地图，确认 marker 聚集正确"""
import json, time, websocket, requests

CDP = "http://localhost:9222"

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
    # 移动端尺寸
    cdp.call("Emulation.setDeviceMetricsOverride", {"width": 420, "height": 900, "mobile": True, "deviceScaleFactor": 2})
    cdp.call("Page.navigate", {"url": "http://localhost:3000/route"})
    time.sleep(8)
    # 截图整页
    r = cdp.call("Page.captureScreenshot", {"format": "png"})
    import base64
    open("E:/ruanjianbei/uploads/route_map_check.png", "wb").write(base64.b64decode(r["result"]["data"]))
    # 也收集 marker 的 DOM 信息
    info = cdp.call("Runtime.evaluate", {"expression": """
    (function(){
      const pins = document.querySelectorAll('.map-pin-wrap, .amap-marker');
      const out = [];
      pins.forEach(p => {
        const r = p.getBoundingClientRect();
        out.push({x: r.left.toFixed(0), y: r.top.toFixed(0), w: r.width.toFixed(0)});
      });
      return JSON.stringify({count: pins.length, samples: out.slice(0,25)});
    })()
    """, "returnByValue": True})
    print("markers:", json.dumps(info.get("result",{}).get("value"), ensure_ascii=False))
    print("screenshot saved")

if __name__ == "__main__":
    main()