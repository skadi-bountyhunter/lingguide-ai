"""情感分析模块单元测试"""
import pytest
from app.core.emotion import analyze_emotion


@pytest.mark.parametrize("text,expected_label", [
    # 否定词处理
    ("这个讲解一点都不好", "negative"),
    ("服务态度不是很满意", "negative"),
    ("态度很不好", "negative"),
    ("不满意", "negative"),
    ("不好看", "negative"),
    ("不算很好，一般吧", "negative"),
    # 纯信息查询句 → 强制中性
    ("灵山大佛怎么走", "neutral"),
    ("去梵宫的路线是什么", "neutral"),
    ("门票多少钱", "neutral"),
    ("几点开门", "neutral"),
    ("还要等多久才能进去", "neutral"),
    # 疑问句削弱置信度 → 中性
    ("这里好玩吗", "neutral"),
    # 正向情绪
    ("太棒了这个表演", "positive"),
    ("谢谢讲解，很清楚", "positive"),
    ("哇这个也太震撼了吧", "positive"),
    ("挺好的", "positive"),
    ("好玩", "positive"),
    ("好开心", "positive"),
    # 负向情绪
    ("垃圾景区，投诉！", "negative"),
    ("好无聊啊，什么时候结束", "negative"),
    ("这个地方一点都不好玩，很无聊", "negative"),
    ("好累啊", "negative"),
    # 边界输入
    ("", "neutral"),
    ("   ", "neutral"),
    ("123", "neutral"),
])
def test_analyze_emotion_label(text, expected_label):
    label, score = analyze_emotion(text)
    assert label == expected_label, f"输入={repr(text)!r}, 期望={expected_label}, 实际={label}(score={score:.3f})"


@pytest.mark.parametrize("text,lo,hi", [
    ("垃圾景区，投诉！", 0.0, 0.20),
    ("太棒了这个表演", 0.75, 1.0),
    ("灵山大佛怎么走", 0.499, 0.501),
    ("", 0.499, 0.501),
])
def test_analyze_emotion_score_range(text, lo, hi):
    _, score = analyze_emotion(text)
    assert lo <= score <= hi, f"输入={repr(text)!r}, score={score:.3f} 不在 [{lo}, {hi}]"


def test_analyze_emotion_returns_tuple():
    result = analyze_emotion("测试")
    assert isinstance(result, tuple) and len(result) == 2
    label, score = result
    assert label in {"positive", "neutral", "negative"}
    assert 0.0 <= score <= 1.0
