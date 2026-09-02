"""多语言基础能力：locale 规范化、固定文案与景点静态投影。

景点的 canonical name 始终保留中文，展示字段通过本模块投影，避免把翻译写入
数据库或破坏既有中文接口契约。
"""
from __future__ import annotations

from typing import Any

SUPPORTED_LOCALES = ("zh-CN", "en", "ja", "ko")

_LOCALE_ALIASES = {
    "zh": "zh-CN", "zh-cn": "zh-CN", "zh_cn": "zh-CN", "cn": "zh-CN",
    "en": "en", "en-us": "en", "en_us": "en", "en-gb": "en",
    "ja": "ja", "ja-jp": "ja", "ja_jp": "ja",
    "ko": "ko", "ko-kr": "ko", "ko_kr": "ko",
}

MESSAGES = {
    "zh-CN": {
        "no_evidence": "我暂时没有找到足够可靠的景区资料来回答这个问题，建议您换个问法，或以景区官方信息为准。",
        "timeout": "处理超时，请稍后重试。",
        "service_unavailable": "服务暂时不可用，请稍后重试。",
        "empty_query": "输入不能为空",
        "asr_not_configured": "请配置科大讯飞 ASR 凭证",
        "asr_no_speech": "未识别到语音，请重试",
        "asr_failed": "语音识别失败，请重试",
        "asr_locale_unsupported": "当前语音识别服务暂不支持该语言，请使用中文重试",
        "weather_not_configured": "天气服务未配置",
        "weather_unavailable": "天气服务暂不可用，请稍后重试",
        "weather_no_data": "天气暂无可用数据，请稍后重试",
        "weather_live": "实况",
        "weather_temperature": "气温",
        "weather_humidity": "湿度",
        "weather_wind": "风",
        "weather_day": "白天",
        "weather_night": "夜间",
        "weather_degree": "°C",
        "weather_week": "周",
        "route_ready": "已为您规划好游览路线。",
        "route_fallback_title": "灵山推荐路线",
        "route_fallback_description": "景区特色景点",
        "route_fallback_tips": "建议错峰游览，穿舒适鞋并及时补充饮水。",
    },
    "en": {
        "no_evidence": "I could not find enough reliable scenic information to answer that. Please try another question or check the official scenic-area information.",
        "timeout": "The request timed out. Please try again later.",
        "service_unavailable": "The service is temporarily unavailable. Please try again later.",
        "empty_query": "Please enter a question.",
        "asr_not_configured": "Speech recognition is not configured.",
        "asr_no_speech": "No speech was recognized. Please try again.",
        "asr_failed": "Speech recognition failed. Please try again.",
        "asr_locale_unsupported": "This speech service does not support the selected language yet. Please try Chinese.",
        "weather_not_configured": "Weather service is not configured.",
        "weather_unavailable": "Weather service is temporarily unavailable. Please try again later.",
        "weather_no_data": "No weather data is available right now. Please try again later.",
        "weather_live": "Current",
        "weather_temperature": "temperature",
        "weather_humidity": "humidity",
        "weather_wind": "wind",
        "weather_day": "day",
        "weather_night": "night",
        "weather_degree": "°C",
        "weather_week": "",
        "route_ready": "Your sightseeing route is ready.",
        "route_fallback_title": "Recommended Lingshan Route",
        "route_fallback_description": "A distinctive scenic attraction",
        "route_fallback_tips": "Visit outside peak hours, wear comfortable shoes, and stay hydrated.",
    },
    "ja": {
        "no_evidence": "信頼できる観光情報が十分に見つからないため、お答えできません。別の聞き方をするか、公式情報をご確認ください。",
        "timeout": "処理がタイムアウトしました。しばらくしてからもう一度お試しください。",
        "service_unavailable": "サービスを一時的に利用できません。しばらくしてからお試しください。",
        "empty_query": "質問を入力してください。",
        "asr_not_configured": "音声認識サービスが設定されていません。",
        "asr_no_speech": "音声を認識できませんでした。もう一度お試しください。",
        "asr_failed": "音声認識に失敗しました。もう一度お試しください。",
        "asr_locale_unsupported": "この音声サービスは選択した言語にまだ対応していません。中国語でお試しください。",
        "weather_not_configured": "天気サービスが設定されていません。",
        "weather_unavailable": "天気サービスを一時的に利用できません。後でもう一度お試しください。",
        "weather_no_data": "現在利用できる天気データがありません。後でもう一度お試しください。",
        "weather_live": "現在",
        "weather_temperature": "気温",
        "weather_humidity": "湿度",
        "weather_wind": "風",
        "weather_day": "昼",
        "weather_night": "夜",
        "weather_degree": "°C",
        "weather_week": "",
        "route_ready": "観光ルートを作成しました。",
        "route_fallback_title": "霊山おすすめルート",
        "route_fallback_description": "特色ある観光スポット",
        "route_fallback_tips": "混雑時間を避け、歩きやすい靴を履き、こまめに水分補給してください。",
    },
    "ko": {
        "no_evidence": "신뢰할 수 있는 관광 정보를 충분히 찾지 못해 답변하기 어렵습니다. 다른 방식으로 질문하거나 공식 정보를 확인해 주세요.",
        "timeout": "처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        "service_unavailable": "서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        "empty_query": "질문을 입력해 주세요.",
        "asr_not_configured": "음성 인식 서비스가 설정되지 않았습니다.",
        "asr_no_speech": "음성을 인식하지 못했습니다. 다시 시도해 주세요.",
        "asr_failed": "음성 인식에 실패했습니다. 다시 시도해 주세요.",
        "asr_locale_unsupported": "현재 음성 서비스는 선택한 언어를 지원하지 않습니다. 중국어로 다시 시도해 주세요.",
        "weather_not_configured": "날씨 서비스가 설정되지 않았습니다.",
        "weather_unavailable": "날씨 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        "weather_no_data": "현재 이용 가능한 날씨 데이터가 없습니다. 잠시 후 다시 시도해 주세요.",
        "weather_live": "현재",
        "weather_temperature": "기온",
        "weather_humidity": "습도",
        "weather_wind": "바람",
        "weather_day": "낮",
        "weather_night": "밤",
        "weather_degree": "°C",
        "weather_week": "",
        "route_ready": "관광 경로를 준비했습니다.",
        "route_fallback_title": "링산 추천 경로",
        "route_fallback_description": "관광지의 특색 있는 명소",
        "route_fallback_tips": "혼잡한 시간을 피하고 편한 신발을 착용하며 수분을 자주 보충해 주세요.",
    },
}

# 22 个景点的可维护展示表。每个 locale 均有 name、desc、tags；其余字段
# 缺失时由 project_spot 使用合理的原文/通用标签回退，canonical name 不变。
SPOT_TRANSLATIONS: dict[str, dict[str, dict[str, Any]]] = {
    "灵山大佛": {
        "en": {"name": "Lingshan Grand Buddha", "desc": "An 88-meter open-air bronze Buddha statue, majestic and awe-inspiring.", "tags": ["Buddhist culture", "Architecture"]},
        "ja": {"name": "霊山大仏", "desc": "高さ88メートルの屋外青銅仏像。荘厳で迫力のある景観です。", "tags": ["仏教文化", "建築芸術"]},
        "ko": {"name": "영산대불", "desc": "높이 88m의 야외 청동 불상으로 장엄하고 웅장한 볼거리입니다.", "tags": ["불교 문화", "건축 예술"]},
    },
    "梵宫": {
        "en": {"name": "Brahma Palace", "desc": "A Buddhist art palace known as the Eastern Louvre, with dazzling dome murals.", "tags": ["Architecture", "Buddhist culture"]},
        "ja": {"name": "梵宮", "desc": "東洋のルーヴルと称される仏教芸術殿堂。壮麗なドーム壁画が見どころです。", "tags": ["建築芸術", "仏教文化"]},
        "ko": {"name": "범궁", "desc": "동양의 루브르로 불리는 불교 예술 전당으로 화려한 돔 벽화가 돋보입니다.", "tags": ["건축 예술", "불교 문화"]},
    },
    "九龙灌浴": {
        "en": {"name": "Nine Dragons Bathing", "desc": "A musical fountain sculpture where nine dragons spray water as the lotus opens.", "tags": ["Buddhist culture", "Family fun"]},
        "ja": {"name": "九龍灌浴", "desc": "蓮の花が開くと九頭の龍が噴水を上げる、音楽と動きのある群像です。", "tags": ["仏教文化", "ファミリー"]},
        "ko": {"name": "구룡관욕", "desc": "연꽃이 열리면 아홉 용이 물을 뿜는 음악 분수 조각 공연입니다.", "tags": ["불교 문화", "가족 체험"]},
    },
    "五印坛城": {
        "en": {"name": "Five Seals Mandala", "desc": "A Tibetan Buddhist cultural site blending Han and Tibetan architectural styles.", "tags": ["Architecture", "Historic sites"]},
        "ja": {"name": "五印壇城", "desc": "漢族とチベットの建築様式を融合したチベット仏教文化の体験地です。", "tags": ["建築芸術", "史跡"]},
        "ko": {"name": "오인단성", "desc": "한족과 티베트 건축 양식을 융합한 티베트 불교 문화 체험 공간입니다.", "tags": ["건축 예술", "역사 유적"]},
    },
    "降魔浮雕": {
        "en": {"name": "Demon-Subduing Relief", "desc": "A finely carved relief depicting the Buddha overcoming demons and attaining enlightenment.", "tags": ["Buddhist culture", "Historic sites"]},
        "ja": {"name": "降魔浮彫", "desc": "釈迦が魔を退け悟りを開く物語を刻んだ精巧な浮彫です。", "tags": ["仏教文化", "史跡"]},
        "ko": {"name": "항마 부조", "desc": "석가모니가 악마를 물리치고 깨달음을 얻는 이야기를 새긴 정교한 부조입니다.", "tags": ["불교 문화", "역사 유적"]},
    },
    "菩提大道": {
        "en": {"name": "Bodhi Avenue", "desc": "A peaceful walk beneath bodhi trees with lake views and garden scenery.", "tags": ["Nature", "Vegetarian cuisine"]},
        "ja": {"name": "菩提大道", "desc": "菩提樹の木陰を歩き、太湖の景色と庭園を楽しめる静かな道です。", "tags": ["自然風景", "素食"]},
        "ko": {"name": "보리대로", "desc": "보리수나무 아래를 거닐며 호수 풍경과 정원을 감상하는 고요한 길입니다.", "tags": ["자연 풍경", "채식 음식"]},
    },
    "灵山大照壁": {
        "en": {"name": "Lingshan Screen Wall", "desc": "A grand bluestone entrance wall known as the First Wall of China.", "tags": ["Buddhist culture", "Architecture"]},
        "ja": {"name": "霊山大照壁", "desc": "中国第一の壁と称される、壮大な青石造りの入口照壁です。", "tags": ["仏教文化", "建築芸術"]},
        "ko": {"name": "영산 대조벽", "desc": "중국 제일의 벽으로 불리는 웅장한 청석 입구 벽입니다.", "tags": ["불교 문화", "건축 예술"]},
    },
    "五明桥": {
        "en": {"name": "Wuming Bridge", "desc": "Five white-marble arches symbolizing the five Buddhist branches of wisdom.", "tags": ["Buddhist culture", "Architecture"]},
        "ja": {"name": "五明橋", "desc": "仏教の五明の智慧を象徴する五つの白玉石アーチ橋です。", "tags": ["仏教文化", "建築芸術"]},
        "ko": {"name": "오명교", "desc": "불교의 다섯 지혜를 상징하는 다섯 개의 백옥 석조 아치교입니다.", "tags": ["불교 문화", "건축 예술"]},
    },
    "佛足坛": {
        "en": {"name": "Buddha Footprint Altar", "desc": "A pilgrimage site featuring large bronze footprints engraved with auspicious symbols.", "tags": ["Buddhist culture", "Historic sites"]},
        "ja": {"name": "仏足壇", "desc": "吉祥文様を刻んだ大きな青銅の仏足を祀る巡礼スポットです。", "tags": ["仏教文化", "史跡"]},
        "ko": {"name": "불족단", "desc": "상서로운 문양을 새긴 거대한 청동 불족을 모신 순례 명소입니다.", "tags": ["불교 문화", "역사 유적"]},
    },
    "五智门": {
        "en": {"name": "Five Wisdom Gate", "desc": "A white-marble gateway representing the five directions and five Buddhas.", "tags": ["Buddhist culture", "Architecture"]},
        "ja": {"name": "五智門", "desc": "五方五仏を象徴する白玉石の壮大な門です。", "tags": ["仏教文化", "建築芸術"]},
        "ko": {"name": "오지문", "desc": "다섯 방향과 다섯 부처를 상징하는 웅장한 백옥 문입니다.", "tags": ["불교 문화", "건축 예술"]},
    },
    "阿育王柱": {
        "en": {"name": "Ashoka Pillar", "desc": "A 16.9-meter granite pillar topped by four lions, symbolizing Buddhism spreading worldwide.", "tags": ["Buddhist culture", "Historic sites"]},
        "ja": {"name": "アショーカ王柱", "desc": "四頭の獅子を戴く高さ16.9メートルの花崗岩柱で、仏法の広がりを象徴します。", "tags": ["仏教文化", "史跡"]},
        "ko": {"name": "아육왕주", "desc": "네 마리 사자 장식이 있는 높이 16.9m 화강암 기둥으로 불법의 전파를 상징합니다.", "tags": ["불교 문화", "역사 유적"]},
    },
    "百子戏弥勒": {
        "en": {"name": "Children Playing with Maitreya", "desc": "A lively bronze group sculpture symbolizing family happiness and good fortune.", "tags": ["Buddhist culture", "Family fun"]},
        "ja": {"name": "百子戯弥勒", "desc": "百人の子どもが弥勒仏と遊ぶ、家族の幸福と福を表す青銅群像です。", "tags": ["仏教文化", "ファミリー"]},
        "ko": {"name": "백자희미륵", "desc": "아이들이 미륵불과 어울리는 모습을 담아 가족의 행복과 복을 상징하는 청동 군상입니다.", "tags": ["불교 문화", "가족 체험"]},
    },
    "祥符禅寺": {
        "en": {"name": "Xiangfu Zen Temple", "desc": "A thousand-year-old Tang-era temple and an important Chan Buddhist heritage site.", "tags": ["Buddhist culture", "Historic sites"]},
        "ja": {"name": "祥符禅寺", "desc": "唐代に始まった千年の古刹で、江南禅宗の重要な文化遺産です。", "tags": ["仏教文化", "史跡"]},
        "ko": {"name": "상부선사", "desc": "당나라 시대에 시작된 천년 고찰로 강남 선종의 중요한 문화유산입니다.", "tags": ["불교 문화", "역사 유적"]},
    },
    "佛教文化博览馆": {
        "en": {"name": "Buddhist Culture Museum", "desc": "A three-level museum exploring Buddhist history, art, and the Ten Thousand Buddhas Hall.", "tags": ["Buddhist culture", "Family fun"]},
        "ja": {"name": "仏教文化博覧館", "desc": "仏教の歴史と芸術を紹介し、万仏殿も備えた三層の博物館です。", "tags": ["仏教文化", "ファミリー"]},
        "ko": {"name": "불교문화박람관", "desc": "불교 역사와 예술을 소개하고 만불전을 갖춘 3층 박물관입니다.", "tags": ["불교 문화", "가족 체험"]},
    },
    "曼飞龙塔": {
        "en": {"name": "Manfeilong Pagoda", "desc": "A nine-tower white pagoda modeled on the landmark of Xishuangbanna Theravada Buddhism.", "tags": ["Architecture", "Buddhist culture"]},
        "ja": {"name": "曼飛龍塔", "desc": "西双版納の白塔を再現した、九塔からなる南伝仏教の象徴的建築です。", "tags": ["建築芸術", "仏教文化"]},
        "ko": {"name": "만비룡탑", "desc": "시솽반나 백탑을 재현한 아홉 탑 구성의 남방 불교 상징 건축입니다.", "tags": ["건축 예술", "불교 문화"]},
    },
    "无尽意斋": {
        "en": {"name": "Wujinyi Study", "desc": "A memorial courtyard for Zhao Puchu with calligraphy exhibits and complimentary Zen tea.", "tags": ["Historic sites", "Buddhist culture"]},
        "ja": {"name": "無尽意斎", "desc": "趙朴初ゆかりの四合院式記念館。書道作品と禅茶を楽しめます。", "tags": ["史跡", "仏教文化"]},
        "ko": {"name": "무진의재", "desc": "자오푸추 기념 사합원으로 서예 작품과 무료 선차를 만날 수 있습니다.", "tags": ["역사 유적", "불교 문화"]},
    },
    "拈花广场": {
        "en": {"name": "Nianhua Square", "desc": "The gateway to Nianhua Bay, featuring a 12-meter gilded bronze Smiling Buddha sculpture.", "tags": ["Buddhist culture", "Architecture"]},
        "ja": {"name": "拈花広場", "desc": "拈花湾の入口にある、12メートルの金色の拈花微笑像が印象的な広場です。", "tags": ["仏教文化", "建築芸術"]},
        "ko": {"name": "녠화 광장", "desc": "녠화만의 관문으로 12m 높이의 금빛 염화미소 청동상이 자리합니다.", "tags": ["불교 문화", "건축 예술"]},
    },
    "梵天花海": {
        "en": {"name": "Brahma Flower Sea", "desc": "A 30,000-square-meter seasonal flower meadow crossed by a 1,500-meter wooden path.", "tags": ["Nature", "Family fun"]},
        "ja": {"name": "梵天花海", "desc": "四季の花が咲く3万平方メートルの花畑を、1500メートルの木道が通ります。", "tags": ["自然風景", "ファミリー"]},
        "ko": {"name": "범천 화해", "desc": "사계절 꽃이 피는 3만㎡ 꽃밭을 1,500m 목조 산책로가 가로지릅니다.", "tags": ["자연 풍경", "가족 체험"]},
    },
    "香月花街": {
        "en": {"name": "Xiangyue Flower Street", "desc": "An 800-meter Zen-style street with crafts, cultural souvenirs, tea, and vegetarian food.", "tags": ["Vegetarian cuisine", "Architecture"]},
        "ja": {"name": "香月花街", "desc": "禅の雰囲気が漂う約800メートルの街並みで、工芸品や素食を楽しめます。", "tags": ["素食", "建築芸術"]},
        "ko": {"name": "샹웨 화거리", "desc": "공예품과 문화 상품, 선차, 채식 음식을 만날 수 있는 800m 선풍 상업 거리입니다.", "tags": ["채식 음식", "건축 예술"]},
    },
    "拈花堂": {
        "en": {"name": "Nianhua Hall", "desc": "A quiet 1,200-square-meter Zen hall for meditation, sutra copying, and tea tasting.", "tags": ["Buddhist culture", "Nature"]},
        "ja": {"name": "拈花堂", "desc": "坐禅や写経、禅茶を体験できる、1200平方メートルの静かな禅堂です。", "tags": ["仏教文化", "自然風景"]},
        "ko": {"name": "녠화당", "desc": "명상과 사경, 선차를 체험할 수 있는 1,200㎡ 규모의 고요한 선당입니다.", "tags": ["불교 문화", "자연 풍경"]},
    },
    "五灯湖": {
        "en": {"name": "Five Lantern Lake", "desc": "A 5,000-square-meter lake and the main stage for the nighttime Zen light show.", "tags": ["Nature", "Buddhist culture"]},
        "ja": {"name": "五灯湖", "desc": "夜の禅の光のショーが行われる、5000平方メートルの湖です。", "tags": ["自然風景", "仏教文化"]},
        "ko": {"name": "오등호", "desc": "밤의 선 빛 쇼가 열리는 5,000㎡ 규모의 호수 경관입니다.", "tags": ["자연 풍경", "불교 문화"]},
    },
    "鹿鸣谷": {
        "en": {"name": "Luming Valley", "desc": "A quiet 20,000-square-meter woodland retreat with over 90% vegetation coverage.", "tags": ["Nature", "Family fun"]},
        "ja": {"name": "鹿鳴谷", "desc": "植生率90％以上の2万平方メートルの森。静かな自然の憩いの場です。", "tags": ["自然風景", "ファミリー"]},
        "ko": {"name": "루밍 계곡", "desc": "식생覆盖율 90% 이상의 2만㎡ 숲으로 조용히 자연을 즐길 수 있습니다.", "tags": ["자연 풍경", "가족 체험"]},
    },
}

TAG_TRANSLATIONS = {
    "佛教文化": {"en": "Buddhist culture", "ja": "仏教文化", "ko": "불교 문화"},
    "建筑艺术": {"en": "Architecture", "ja": "建築芸術", "ko": "건축 예술"},
    "亲子游乐": {"en": "Family fun", "ja": "ファミリー", "ko": "가족 체험"},
    "历史古迹": {"en": "Historic sites", "ja": "史跡", "ko": "역사 유적"},
    "自然风光": {"en": "Nature", "ja": "自然風景", "ko": "자연 풍경"},
    "美食素斋": {"en": "Vegetarian cuisine", "ja": "素食", "ko": "채식 음식"},
}


def normalize_locale(locale: str | None) -> str:
    """将 locale 规范化为四个受支持值，未知值安全回退中文。"""
    value = str(locale or "zh-CN").strip().replace("_", "-").lower()
    return _LOCALE_ALIASES.get(value, "zh-CN")


def message(key: str, locale: str | None = None, **kwargs: Any) -> str:
    """读取固定文案；缺少 key 时仍稳定回退中文。"""
    lang = normalize_locale(locale)
    text = MESSAGES.get(lang, MESSAGES["zh-CN"]).get(key) or MESSAGES["zh-CN"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def translate_tag(tag: str, locale: str | None = None) -> str:
    lang = normalize_locale(locale)
    if lang == "zh-CN":
        return tag
    return TAG_TRANSLATIONS.get(tag, {}).get(lang, tag)


def translate_tags(tags: list[str], locale: str | None = None) -> list[str]:
    return [translate_tag(str(tag), locale) for tag in (tags or [])]


def project_spot(spot: Any, locale: str | None = None) -> dict[str, Any]:
    """将 ORM/字典景点投影成兼容旧字段的本地化展示字段。"""
    lang = normalize_locale(locale)
    get = (lambda key, default="": spot.get(key, default)) if isinstance(spot, dict) else (lambda key, default="": getattr(spot, key, default))
    canonical = str(get("name", ""))
    tags = list(get("tags_list", get("tags", [])) or [])
    highlights = list(get("highlights_list", get("highlights", [])) or [])
    tips = list(get("tips_list", get("tips", [])) or [])
    nearby = list(get("nearby_list", get("nearby", [])) or [])
    translation = SPOT_TRANSLATIONS.get(canonical, {}).get(lang, {}) if lang != "zh-CN" else {}
    translated = bool(lang == "zh-CN" or translation.get("name"))
    display_tags = translation.get("tags") or translate_tags(tags, lang)
    display_name = translation.get("name") or canonical
    display_desc = translation.get("desc") or str(get("desc", ""))
    # 详细字段没有逐段机器翻译，保留原文比生成不可靠事实更安全；标签/展示摘要仍本地化。
    display_highlights = [str(item) for item in highlights]
    display_tips = [str(item) for item in tips]
    display_nearby = [str(item) for item in nearby]
    if lang != "zh-CN":
        display_highlights = [translate_tag(item, lang) for item in display_highlights]
        display_tips = [translate_tag(item, lang) for item in display_tips]
        display_nearby = [SPOT_TRANSLATIONS.get(item, {}).get(lang, {}).get("name", item) for item in display_nearby]
    return {
        "canonical_name": canonical,
        "display_name": display_name,
        "display_desc": display_desc,
        "display_full_desc": str(get("full_desc", "")),
        "display_tags": display_tags,
        "display_highlights": display_highlights,
        "display_tips": display_tips,
        "display_best_season": str(get("best_season", "")),
        "display_nearby": display_nearby,
        "translation_status": "source" if lang == "zh-CN" else ("translated" if translated else "fallback"),
    }


def canonicalize_query(query: str, locale: str | None = None) -> str:
    """将常见四语问法规范为中文检索句，保留未识别内容。"""
    text = str(query or "").strip()
    lang = normalize_locale(locale)
    if lang == "zh-CN" or not text:
        return text

    exact = {
        "how tall is the lingshan grand buddha?": "灵山大佛有多高？",
        "what is special about brahma palace?": "梵宫有什么特色？",
        "when is the nine dragons bathing show?": "九龙灌浴表演时间是？",
        "recommend a sightseeing route": "推荐一条游览路线",
        "history and culture of lingshan": "灵山的历史文化",
        "霊山大仏の高さは？": "灵山大佛有多高？",
        "梵宮の見どころは？": "梵宫有什么特色？",
        "九龍灌浴の上演時間は？": "九龙灌浴表演时间是？",
        "おすすめの観光ルートを教えて": "推荐一条游览路线",
        "霊山の歴史と文化": "灵山的历史文化",
        "영산대불의 높이는 얼마인가요?": "灵山大佛有多高？",
        "범궁의 특징은 무엇인가요?": "梵宫有什么特色？",
        "구룡관욕 공연 시간은 언제인가요?": "九龙灌浴表演时间是？",
        "관광 경로를 추천해 주세요": "推荐一条游览路线",
        "영산의 역사와 문화": "灵山的历史文化",
    }
    lowered = text.lower()
    if lowered in exact:
        return exact[lowered]
    if text in exact:
        return exact[text]

    aliases = {
        "Lingshan Grand Buddha": "灵山大佛", "Grand Buddha": "灵山大佛",
        "Brahma Palace": "梵宫", "Nine Dragons Bathing": "九龙灌浴",
        "霊山大仏": "灵山大佛", "梵宮": "梵宫", "九龍灌浴": "九龙灌浴",
        "영산대불": "灵山大佛", "범궁": "梵宫", "구룡관욕": "九龙灌浴",
        "opening hours": "开放时间", "ticket": "门票", "weather": "天气",
        "route": "路线", "history": "历史", "culture": "文化", "height": "高度",
        "営業時間": "开放时间", "チケット": "门票", "天気": "天气", "ルート": "路线",
        "歴史": "历史", "文化": "文化", "높이": "高度", "운영 시간": "开放时间",
        "입장권": "门票", "날씨": "天气", "경로": "路线", "역사": "历史", "문화": "文化",
    }
    for source, target in aliases.items():
        text = text.replace(source, target).replace(source.lower(), target)
    return text


def matches_target_language(text: str, locale: str | None) -> bool:
    """粗粒度校验回答主语言，失败时由生成层重试而非返回错误语言。"""
    import re

    value = str(text or "")
    lang = normalize_locale(locale)
    if lang == "zh-CN":
        return bool(re.search(r"[一-鿿]", value))
    if lang == "ja":
        return bool(re.search(r"[぀-ヿ]", value))
    if lang == "ko":
        return bool(re.search(r"[가-힯]", value))
    latin = len(re.findall(r"[A-Za-z]", value))
    cjk = len(re.findall(r"[぀-ヿ㐀-鿿가-힯]", value))
    return latin >= 12 and latin >= cjk


def language_instruction(locale: str | None) -> str:
    """给模型的明确目标语言约束。"""
    lang = normalize_locale(locale)
    return {
        "zh-CN": "请使用简体中文回答。",
        "en": "Answer entirely in English.",
        "ja": "回答はすべて日本語にしてください。",
        "ko": "답변은 모두 한국어로 작성하세요.",
    }[lang]


def localize_duration(duration: str, locale: str | None = None) -> str:
    lang = normalize_locale(locale)
    value = str(duration or "")
    if lang == "zh-CN":
        return value
    replacements = {
        "en": [("约半天", "about half a day"), ("约全天", "a full day"), ("半天", "half a day"), ("全天", "a full day")],
        "ja": [("约半天", "約半日"), ("约全天", "終日"), ("半天", "半日"), ("全天", "終日")],
        "ko": [("约半天", "약 반나절"), ("约全天", "하루 종일"), ("半天", "반나절"), ("全天", "하루 종일")],
    }
    for source, target in replacements[lang]:
        value = value.replace(source, target)
    return value


def translate_weather_value(value: str, locale: str | None = None) -> str:
    """翻译高德常见天气/风向枚举，未知值原样保留。"""
    lang = normalize_locale(locale)
    if lang == "zh-CN":
        return value
    values = {
        "晴": {"en": "Sunny", "ja": "晴れ", "ko": "맑음"}, "多云": {"en": "Cloudy", "ja": "曇り", "ko": "구름 많음"},
        "阴": {"en": "Overcast", "ja": "曇天", "ko": "흐림"}, "小雨": {"en": "Light rain", "ja": "小雨", "ko": "약한 비"},
        "中雨": {"en": "Moderate rain", "ja": "中雨", "ko": "보통 비"}, "大雨": {"en": "Heavy rain", "ja": "大雨", "ko": "큰비"},
        "东北": {"en": "northeast", "ja": "北東", "ko": "북동풍"}, "东南": {"en": "southeast", "ja": "南東", "ko": "남동풍"},
        "西北": {"en": "northwest", "ja": "北西", "ko": "북서풍"}, "西南": {"en": "southwest", "ja": "南西", "ko": "남서풍"},
        "东": {"en": "east", "ja": "東", "ko": "동풍"}, "南": {"en": "south", "ja": "南", "ko": "남풍"},
        "西": {"en": "west", "ja": "西", "ko": "서풍"}, "北": {"en": "north", "ja": "北", "ko": "북풍"},
    }
    return values.get(str(value), {}).get(lang, str(value))
