"""虚拟数据种子脚本 — 用于测试管理端热力图和情绪三维图"""
import sqlite3
import uuid
import random
from datetime import datetime, timedelta

DB_PATH = r"E:\ruanjianbei\backend\app\data\lingguide.db"


def seed(n_visits: int = 200, n_interactions: int = 150):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 从数据库读取景点真实 GCJ-02 坐标
    cur.execute("SELECT id, name, lng, lat FROM spots WHERE lng IS NOT NULL AND lat IS NOT NULL")
    spots = cur.fetchall()
    if not spots:
        print("[错误] spots 表无坐标数据，退出")
        conn.close()
        return
    print(f"已找到 {len(spots)} 个有坐标的景点")

    spot_coords = {s[0]: (s[2], s[3]) for s in spots}  # id -> (lng, lat)
    spot_ids = list(spot_coords.keys())

    # 清除上次错误坐标的种子数据（通过来源标记识别，这里用简单范围过滤）
    cur.execute(
        "DELETE FROM user_visits WHERE lng > 120.2 AND lng < 120.4 AND lat > 31.45 AND lat < 31.55"
    )
    deleted = cur.rowcount
    if deleted:
        print(f"已删除偏移坐标旧数据 {deleted} 条")

    now = datetime.utcnow()

    # ── 1. 插入 user_visits（热力图）——坐标以景点为中心小幅随机偏移（约50m内）──
    visits = []
    for _ in range(n_visits):
        sid = random.choice(spot_ids)
        base_lng, base_lat = spot_coords[sid]
        lng = base_lng + random.uniform(-4e-4, 4e-4)   # ≈ 35m 水平范围
        lat = base_lat + random.uniform(-4e-4, 4e-4)
        days_ago = random.randint(0, 29)
        hours_ago = random.randint(0, 23)
        ts = now - timedelta(days=days_ago, hours=hours_ago)
        visits.append((
            uuid.uuid4().hex,
            str(sid),
            round(lng, 6),
            round(lat, 6),
            ts.strftime("%Y-%m-%d %H:%M:%S"),
        ))

    cur.executemany(
        "INSERT INTO user_visits (id, spot_id, lng, lat, created_at) VALUES (?,?,?,?,?)",
        visits,
    )
    print(f"已插入 {len(visits)} 条 user_visits")

    # ── 2. 插入 interactions（情绪三维图）──
    queries = [
        "灵山大佛多高", "梵宫怎么参观", "九龙灌浴几点演出", "门票多少钱",
        "素斋在哪里", "五印坛城怎么走", "停车场在哪", "最佳游览路线",
        "佛顶宫介绍", "灵山历史", "梵天花海花期", "香月花街在哪",
    ]
    interactions = []
    for _ in range(n_interactions):
        spot_id = random.choice(spot_ids)
        score = min(1.0, max(0.0, random.gauss(0.65, 0.2)))
        label = "positive" if score > 0.6 else ("negative" if score < 0.4 else "neutral")
        days_ago = random.randint(0, 6)
        hour = random.choices(
            range(8, 18),
            weights=[1, 3, 5, 8, 10, 10, 8, 5, 3, 1],
            k=1,
        )[0]
        ts = (now - timedelta(days=days_ago)).replace(
            hour=hour, minute=random.randint(0, 59), second=0, microsecond=0
        )
        interactions.append((
            uuid.uuid4().hex,
            uuid.uuid4().hex[:16],
            None,
            random.choice(queries),
            "text",
            "这是测试回复内容。",
            "[]",
            label,
            round(score, 3),
            str(spot_id),
            random.randint(800, 4000),
            ts.strftime("%Y-%m-%d %H:%M:%S"),
        ))

    cur.executemany(
        """INSERT INTO interactions
           (id, session_id, user_id, query_text, query_mode, response_text,
            rag_sources, emotion_label, emotion_score, spot_id, thinking_time_ms, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        interactions,
    )
    print(f"已插入 {len(interactions)} 条 interactions")

    conn.commit()
    conn.close()
    print("完成。")


if __name__ == "__main__":
    seed()
