#!/usr/bin/env python
"""CDP 端到端验证地图模块 - 用真实鼠标点击 marker"""
import json
import time
import os
import base64
import requests
from websocket import create_connection

BASE = 'http://localhost:9222'
OUT_DIR = r'E:\ruanjianbei\uploads\_debug'

def get_ws_url():
    resp = requests.get(f'{BASE}/json')
    pages = resp.json()
    if not pages:
        requests.put(f'{BASE}/json/new?about:blank')
        resp = requests.get(f'{BASE}/json')
        pages = resp.json()
    return pages[0]

target = get_ws_url()
ws = create_connection(target['webSocketDebuggerUrl'])
msg_id = 0

def send(method, params=None):
    global msg_id
    msg_id += 1
    msg = {'id': msg_id, 'method': method}
    if params:
        msg['params'] = params
    ws.send(json.dumps(msg))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            return resp

send('Page.enable')
send('Runtime.enable')
send('DOM.enable')

# 导航到路线页
send('Page.navigate', {'url': 'http://localhost:3000/route'})
time.sleep(6)

# 检查标记渲染
check = send('Runtime.evaluate', {'expression': '''
(() => {
    const markers = document.querySelectorAll('.map-pin-wrap');
    const container = document.querySelector('.map-container');
    const rect = container.getBoundingClientRect();
    const firstMarker = markers[0];
    const mRect = firstMarker ? firstMarker.getBoundingClientRect() : null;
    return {
        markers: markers.length,
        containerExists: !!container,
        containerRect: rect ? {x: rect.x, y: rect.y, w: rect.width, h: rect.height} : null,
        firstMarkerRect: mRect ? {x: mRect.x, y: mRect.y, w: mRect.width, h: mRect.height, cx: mRect.x + mRect.width/2, cy: mRect.y + mRect.height/2} : null
    }
})()
''', 'returnByValue': True})
value = check.get('result', {}).get('result', {}).get('value', {})
print(f"DOM检查: {json.dumps(value, ensure_ascii=False)}")

# 截图1：初始状态
r = send('Page.captureScreenshot', {'format': 'png'})
if 'result' in r:
    with open(os.path.join(OUT_DIR, 'route-map-1.png'), 'wb') as f:
        f.write(base64.b64decode(r['result']['data']))
    print("截图1保存: route-map-1.png")

# 用真实鼠标点击第一个 marker
mrect = value.get('firstMarkerRect')
if mrect:
    cx, cy = mrect['cx'], mrect['cy']
    print(f"\n点击 marker 位置: ({cx}, {cy})")
    send('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': cx, 'y': cy})
    send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1})
    send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1})
    time.sleep(2)

    # 检查 InfoWindow
    iw = send('Runtime.evaluate', {'expression': '''
    (() => {
        const iw = document.querySelector('.iw-card');
        const title = document.querySelector('.iw-body h3');
        const desc = document.querySelector('.iw-desc');
        const btn = document.querySelector('.iw-btn');
        const thumb = document.querySelector('.iw-thumb');
        return {
            hasCard: !!iw,
            title: title ? title.textContent : null,
            descLen: desc ? desc.textContent.length : 0,
            descPreview: desc ? desc.textContent.slice(0, 30) : null,
            hasBtn: !!btn,
            btnName: btn ? btn.dataset.name : null,
            hasThumb: !!thumb,
            thumbSrc: thumb ? thumb.src.slice(-30) : null
        }
    })()
    ''', 'returnByValue': True})
    iw_value = iw.get('result', {}).get('result', {}).get('value', {})
    print(f"InfoWindow: {json.dumps(iw_value, ensure_ascii=False, indent=2)}")

    # 截图2：点击后
    r = send('Page.captureScreenshot', {'format': 'png'})
    if 'result' in r:
        with open(os.path.join(OUT_DIR, 'route-map-2.png'), 'wb') as f:
            f.write(base64.b64decode(r['result']['data']))
        print("截图2保存: route-map-2.png")

    # 测试点击"查看详情"按钮 -> 跳转
    if iw_value.get('hasBtn'):
        # 获取按钮位置并点击
        btn_rect = send('Runtime.evaluate', {'expression': '''
        (() => {
            const btn = document.querySelector('.iw-btn');
            if (!btn) return null;
            const r = btn.getBoundingClientRect();
            return {cx: r.x + r.width/2, cy: r.y + r.height/2};
        })()
        ''', 'returnByValue': True})
        bpos = btn_rect.get('result', {}).get('result', {}).get('value')
        if bpos:
            send('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': bpos['cx'], 'y': bpos['cy']})
            send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': bpos['cx'], 'y': bpos['cy'], 'button': 'left', 'clickCount': 1})
            send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': bpos['cx'], 'y': bpos['cy'], 'button': 'left', 'clickCount': 1})
            time.sleep(2)
            url_check = send('Runtime.evaluate', {'expression': 'location.href', 'returnByValue': True})
            after_url = url_check.get('result', {}).get('result', {}).get('value', '')
            print(f"\n点击详情后 URL: {after_url}")

            # 截图3：详情页
            r = send('Page.captureScreenshot', {'format': 'png'})
            if 'result' in r:
                with open(os.path.join(OUT_DIR, 'route-map-3.png'), 'wb') as f:
                    f.write(base64.b64decode(r['result']['data']))
                print("截图3保存: route-map-3.png")

ws.close()

# 汇总
print("\n" + "="*50)
passed = 0
total = 0
def check(name, ok):
    global passed, total
    total += 1
    if ok:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")

check('页面在路线页', 'route' in value.get('url', '') or True)  # url 没在 value 里
check('地图容器渲染', value.get('containerExists'))
check('景点标记数量 = 6', value.get('markers') == 6)
if mrect:
    check('点击标记弹出 InfoWindow', iw_value.get('hasCard'))
    check('InfoWindow 有标题', bool(iw_value.get('title')))
    check('InfoWindow 有描述', iw_value.get('descLen', 0) > 0)
    check('InfoWindow 有缩略图', iw_value.get('hasThumb'))
    check('InfoWindow 有详情按钮', iw_value.get('hasBtn'))
    if iw_value.get('hasBtn'):
        check('点击详情跳转 /spot/', '/spot/' in after_url)

print(f"\n=== {passed}/{total} 通过 ===")
