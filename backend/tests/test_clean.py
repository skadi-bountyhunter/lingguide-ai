"""回复清理测试 — 验证语气词/markdown/表情描述被正确移除"""
import pytest


class TestCleanResponse:
    """_clean_response 函数单元测试"""

    def test_remove_stage_direction(self, clean_tests):
        """移除中文语气括号"""
        assert "您好" in clean_tests("您好（热情地）！灵山大佛很高。")
        assert "热情地" not in clean_tests("您好（热情地）！灵山大佛很高。")
        assert "（微笑）" not in clean_tests("（微笑）欢迎来到灵山。")
        assert "微微" not in clean_tests("这里很美。（微微一笑）")

    def test_remove_markdown_bold(self, clean_tests):
        """移除 Markdown 加粗符号"""
        result = clean_tests("**灵山大佛**高达88米，非常壮观。")
        assert "**" not in result
        assert "灵山大佛" in result

    def test_remove_markdown_italic(self, clean_tests):
        """移除 Markdown 斜体符号"""
        result = clean_tests("这座大佛*确实*很壮观。")
        assert "*" not in result
        assert "确实" in result

    def test_remove_trailing_expression(self, clean_tests):
        """移除末尾表情描述"""
        result = clean_tests("欢迎来到灵山胜境。（嘴角含笑）")
        assert "嘴角含笑" not in result
        assert "欢迎" in result

    def test_remove_greeting_gesture(self, clean_tests):
        """移除末尾动作描述"""
        result = clean_tests("很高兴为您服务。（双手合十）")
        assert "双手合十" not in result
        assert "服务" in result

    def test_combined_clean(self, clean_tests):
        """组合清理测试"""
        result = clean_tests(
            "（热情地）**灵山大佛**高达88米，*确实*很壮观！"
            "欢迎来灵山游玩。（双手合十）"
        )
        assert "（热情地）" not in result
        assert "**" not in result
        assert "*" not in result
        assert "（双手合十）" not in result
        assert "灵山大佛" in result
        assert "壮观" in result

    def test_normal_text_preserved(self, clean_tests):
        """正常文本不被误删"""
        normal = "灵山大佛高达88米，是世界上最高的青铜立佛像之一。"
        result = clean_tests(normal)
        assert result == normal

    def test_empty_handling(self, clean_tests):
        """空字符串处理"""
        assert clean_tests("") == ""
        assert clean_tests("   ") == ""

    def test_emoji_removed_from_mock(self, clean_tests):
        """mock 回复中的 emoji 被清理"""
        result = clean_tests("非常壮观！😊 您还想了解什么？")
        assert "😊" not in result
        assert "壮观" in result


@pytest.mark.asyncio
async def test_clean_applied_in_chat_api(client):
    """验证聊天 API 返回的回复已经被清理"""
    res = await client.post("/api/chat/text", json={
        "query": "灵山大佛有多高？",
        "interests": [],
    })
    assert res.status_code == 200
    data = res.json()
    reply = data["reply"]
    # 不应包含 markdown
    assert "**" not in reply
    # 不应包含语气括号
    assert "（" not in reply or "）" not in reply
