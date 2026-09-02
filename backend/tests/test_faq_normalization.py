"""FAQ 规范化回归测试。"""
from app.api.knowledge import _normalize_faq_term
from app.api.chat import match_faq


def test_normalize_faq_term_removes_whitespace_punctuation_without_losing_letters():
    assert _normalize_faq_term("  灵山大佛？\n") == "灵山大佛"
    assert _normalize_faq_term("FAQ_s W") == "faqsw"


def test_faq_matching_accepts_full_width_punctuation_and_whitespace():
    faq = match_faq("  灵山大佛  有多高？ ")
    assert faq is not None
    assert faq["intent"] == "height"
