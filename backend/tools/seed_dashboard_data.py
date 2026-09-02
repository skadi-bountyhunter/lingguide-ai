"""生成30天模拟运营数据（截止2026-07-31）"""
import asyncio
import random
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "app" / "data" / "lingguide.db"

# 景点 ID（从现有数据结构推测）
SPOT_IDS = [
    "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11", "12", "13", "14", "15", "16", "17", "18",
    "19", "20", "21", "22", "23",
]

# 模拟问题模板（符合景区特征）
QUESTIONS = [
    "灵山大佛有多高？",
    "梵宫里面可以参观吗？",
    "九龙灌浴表演时间是几点？",
    "景区开放时间是几点到几点？",
    "门票多少钱？",
    "有素斋餐厅吗？",
    "五印坛城怎么去？",
    "灵山大佛是什么时候建的？",
    "景区有讲解服务吗？",
    "从大佛到梵宫要走多久？",
    "九龙灌浴在哪里？",
    "景区里有休息的地方吗？",
    "梵宫建筑风格是什么？",
    "五印坛城的意义是什么？",
    "灵山圣境有哪些必看景点？",
    "景区推荐游览路线？",
    "停车场在哪里？",
    "景区内可以拍照吗？",
    "有轮椅租赁服务吗？",
    "雨天景区开放吗？",
    "灵山大佛的佛像材质是什么？",
    "梵宫内部装饰有什么特色？",
    "九龙灌浴表演讲的是什么故事？",
    "曼飞龙塔的历史？",
    "降魔浮雕在哪里？",
    "吉祥颂演出时间？",
    "灵山胜境的历史背景？",
    "阿育王柱的含义？",
    "百子戏弥勒在哪？",
    "五智门是什么意思？",
]

# 回答模板（简短示例）
ANSWERS = [
    "灵山大佛高88米，是世界著名的露天青铜释迦牟尼立像。",
    "梵宫内部富丽堂皇，结合了中国传统与西方建筑风格，需单独购票参观。",
    "九龙灌浴表演时间为每天上午10:00和下午14:00，表演约15分钟。",
    "景区开放时间为7:00-17:30，建议您提前规划行程。",
    "成人门票210元，学生票半价，可在线预订享优惠。",
    "有灵山素斋馆，提供各种精致素食，营业时间11:00-14:00。",
    "五印坛城位于景区东侧，从大佛广场步行约8分钟可到达。",
    "大佛于1997年落成开光，历时5年建造，共使用750吨铜材。",
    "景区内设有官方讲解员，可在服务中心预约，也可使用语音导览设备。",
    "从大佛广场到梵宫步行约10分钟，也可乘坐景区观光车。",
    "九龙灌浴广场在进入景区后沿主路直行约500米即可到达。",
    "景区内设有多处休息亭和座椅，在主要景点附近均有遮荫休息区。",
    "梵宫融合了佛教建筑风格与现代工艺，被誉为'世界佛教艺术的殿堂'。",
    "五印坛城象征佛教宇宙观，供奉着大日如来佛像。",
    "推荐路线：大门→阿育王柱→九龙灌浴→大佛广场→梵宫→五印坛城，全程约4小时。",
]

# 景区景点坐标（用于热力图，无锡灵山胜境附近）
SPOT_COORDS = [
    (120.3518, 31.5632),  # 灵山大佛广场
    (120.3495, 31.5618),  # 梵宫
    (120.3528, 31.5645),  # 九龙灌浴
    (120.3505, 31.5598),  # 五印坛城
    (120.3488, 31.5655),  # 阿育王柱
    (120.3542, 31.5612),  # 小灵山
    (120.3475, 31.5640),  # 香月花街
    (120.3558, 31.5628),  # 灵山梵宫广场
    (120.3512, 31.5670),  # 降魔浮雕
    (120.3468, 31.5605),  # 五智门
]


def _new_id() -> str:
    return uuid.uuid4().hex


def _new_session() -> str:
    return "sim_" + uuid.uuid4().hex[:16]


def _weighted_hour() -> int:
    """模拟景区高峰时段分布"""
    weights = [
        0, 0, 0, 0, 0, 0, 0,   # 0-6  关闭（7个）
        3, 8, 15, 20, 18,       # 7-11 上午高峰（5个）
        10, 8, 16, 18, 12,      # 12-16 午后高峰（5个）
        8, 5, 2, 1, 0, 0,       # 17-22（6个），合计23个……
        0,                      # 23（1个）
    ]
    return random.choices(range(24), weights=weights)[0]


def _emotion() -> tuple[str, float]:
    """70% 正面，20% 中性，10% 负面"""
    r = random.random()
    if r < 0.70:
        return "positive", round(random.uniform(0.70, 0.98), 3)
    elif r < 0.90:
        return "neutral", round(random.uniform(0.40, 0.65), 3)
    else:
        return "negative", round(random.uniform(0.05, 0.35), 3)


def _daily_volume(day_offset: int, weekday: int) -> int:
    """模拟日流量：周末多，工作日少，早期偶尔少"""
    base = 40 + day_offset  # 逐渐增长
    if weekday >= 5:         # 周末
        base = int(base * 1.6)
    if day_offset < 5:       # 前几天刚上线
        base = int(base * 0.4)
    return max(10, base + random.randint(-8, 8))


def generate_interactions(end_date: datetime, days: int = 30) -> list[tuple]:
    """生成 interactions 表数据"""
    rows = []
    # end_date 是北京时间7月31日23:59，转为UTC
    end_utc = end_date - timedelta(hours=8)
    start_utc = end_utc - timedelta(days=days)

    for day_offset in range(days):
        day_utc = start_utc + timedelta(days=day_offset)
        weekday = day_utc.weekday()
        volume = _daily_volume(day_offset, weekday)

        # 每天生成若干 session，每 session 1-4 条互动
        sessions_today = max(3, volume // 3)
        for _ in range(sessions_today):
            session_id = _new_session()
            turn_count = random.randint(1, 4)
            for turn in range(turn_count):
                hour = _weighted_hour()
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                created_at = day_utc.replace(hour=hour, minute=minute, second=second)
                if created_at >= end_utc:
                    continue

                label, score = _emotion()
                mode = "voice" if random.random() < 0.20 else "text"
                q = random.choice(QUESTIONS)
                a = random.choice(ANSWERS)
                spot_id = random.choice(SPOT_IDS + [None, None])  # 部分无景点

                rows.append((
                    _new_id(),                          # id
                    session_id,                         # session_id
                    None,                               # user_id
                    q,                                  # query_text
                    mode,                               # query_mode
                    a,                                  # response_text
                    "[]",                               # rag_sources
                    label,                              # emotion_label
                    score,                              # emotion_score
                    spot_id,                            # spot_id
                    random.randint(800, 6500),          # thinking_time_ms
                    "[]",                               # citations_json
                    "{}",                               # retrieval_json
                    "",                                 # trace_id
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),  # created_at
                ))

    return rows


def generate_pins(end_date: datetime, days: int = 30) -> list[tuple]:
    """生成 user_pins 热力图数据"""
    rows = []
    end_utc = end_date - timedelta(hours=8)
    start_utc = end_utc - timedelta(days=days)
    for day_offset in range(days):
        day_utc = start_utc + timedelta(days=day_offset)
        count = random.randint(5, 20)
        for _ in range(count):
            base_lng, base_lat = random.choice(SPOT_COORDS)
            lng = base_lng + random.gauss(0, 0.002)
            lat = base_lat + random.gauss(0, 0.002)
            hour = _weighted_hour()
            created_at = day_utc.replace(
                hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59)
            )
            if created_at >= end_utc:
                continue
            rows.append((
                _new_id(),
                random.choice(["我来过这里", "打卡", "观景台", ""]),
                round(lng, 6),
                round(lat, 6),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ))
    return rows


def generate_visits(end_date: datetime, days: int = 30) -> list[tuple]:
    """生成 user_visits 被动位置数据"""
    rows = []
    end_utc = end_date - timedelta(hours=8)
    start_utc = end_utc - timedelta(days=days)
    for day_offset in range(days):
        day_utc = start_utc + timedelta(days=day_offset)
        count = random.randint(15, 50)
        for _ in range(count):
            base_lng, base_lat = random.choice(SPOT_COORDS)
            lng = base_lng + random.gauss(0, 0.0015)
            lat = base_lat + random.gauss(0, 0.0015)
            hour = _weighted_hour()
            created_at = day_utc.replace(
                hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59)
            )
            if created_at >= end_utc:
                continue
            spot_id = random.choice(SPOT_IDS)
            rows.append((
                _new_id(),
                spot_id,
                round(lng, 6),
                round(lat, 6),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ))
    return rows


def main():
    # 截止时间：北京时间2026-07-31 23:59:59
    end_date = datetime(2026, 7, 31, 23, 59, 59)

    random.seed(42)  # 固定种子，结果可复现

    interactions = generate_interactions(end_date, 30)
    pins = generate_pins(end_date, 30)
    visits = generate_visits(end_date, 30)

    print(f"准备写入：{len(interactions)} 条交互记录，{len(pins)} 条标记，{len(visits)} 条位置记录")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executemany(
        """INSERT OR IGNORE INTO interactions
           (id, session_id, user_id, query_text, query_mode, response_text,
            rag_sources, emotion_label, emotion_score, spot_id, thinking_time_ms,
            citations_json, retrieval_json, trace_id, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        interactions,
    )

    cur.executemany(
        "INSERT OR IGNORE INTO user_pins (id, name, lng, lat, created_at) VALUES (?,?,?,?,?)",
        pins,
    )

    cur.executemany(
        "INSERT OR IGNORE INTO user_visits (id, spot_id, lng, lat, created_at) VALUES (?,?,?,?,?)",
        visits,
    )

    conn.commit()
    conn.close()

    print(f"写入完成：{len(interactions)} 条交互 | {len(pins)} 条 pin | {len(visits)} 条 visit")
    print("数据时间范围：2026-07-02 ~ 2026-07-31（北京时间）")


if __name__ == "__main__":
    main()
