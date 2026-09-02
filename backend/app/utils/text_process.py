"""文本处理工具"""
import re


def split_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """滑动窗口文本切片"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """简单关键词提取（基于 TF）"""
    # 移除标点
    cleaned = re.sub(r'[，。！？、；：""''（）\s]', ' ', text)
    words = cleaned.split()
    # 过滤短词
    long_words = [w for w in words if len(w) >= 2]
    return long_words[:top_n]


def truncate_text(text: str, max_len: int = 200) -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"
