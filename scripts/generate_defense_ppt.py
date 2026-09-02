"""生成灵境导游答辩 PPT。

不依赖第三方 PPT 库，直接写入 Office Open XML，便于在当前环境稳定生成 .pptx。
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

EMU = 914400
SLIDE_W = 13.333333
SLIDE_H = 7.5
OUT = Path("灵境导游_答辩PPT_创新点.pptx")

THEME = {
    "bg": "F8F5EF",
    "bg2": "FBFAF7",
    "ink": "1E2A24",
    "muted": "647067",
    "primary": "2D6A4F",
    "primary2": "40916C",
    "accent": "B07D4F",
    "lake": "2B6F8A",
    "sage": "7C9A74",
    "line": "E5DED2",
    "white": "FFFFFF",
    "soft": "EFE7DA",
    "danger": "B94747",
}


@dataclass
class Shape:
    xml: str


@dataclass
class Slide:
    title: str
    shapes: list[Shape] = field(default_factory=list)


def emu(value: float) -> int:
    return int(value * EMU)


def xml_text(text: str) -> str:
    return escape(text).replace("\n", "<a:br/>")


def tx_body(text: str, size: int, color: str, bold: bool = False, align: str = "l") -> str:
    bold_xml = "<a:b/>" if bold else ""
    return (
        "<p:txBody><a:bodyPr wrap=\"square\" rtlCol=\"0\"/><a:lstStyle/>"
        f"<a:p><a:pPr algn=\"{align}\"><a:lnSpc><a:spcPct val=\"112000\"/></a:lnSpc></a:pPr>"
        f"<a:r><a:rPr lang=\"zh-CN\" sz=\"{size * 100}\" dirty=\"0\">{bold_xml}"
        f"<a:solidFill><a:srgbClr val=\"{color}\"/></a:solidFill>"
        "<a:latin typeface=\"Microsoft YaHei\"/><a:ea typeface=\"Microsoft YaHei\"/>"
        f"</a:rPr><a:t>{xml_text(text)}</a:t></a:r></a:p></p:txBody>"
    )


def sp_id(value: int) -> str:
    return str(1000 + value)


class Builder:
    def __init__(self) -> None:
        self.slides: list[Slide] = []
        self.counter = 1

    def slide(self, title: str) -> Slide:
        slide = Slide(title)
        self.slides.append(slide)
        self.counter = 1
        self.bg(slide)
        return slide

    def add(self, slide: Slide, xml: str) -> None:
        slide.shapes.append(Shape(xml))
        self.counter += 1

    def rect(
        self,
        slide: Slide,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        line: str | None = None,
        radius: bool = True,
        alpha: int | None = None,
    ) -> None:
        geom = "roundRect" if radius else "rect"
        fill_alpha = f"<a:alpha val=\"{alpha}\"/>" if alpha is not None else ""
        line_xml = "<a:ln><a:noFill/></a:ln>" if line is None else f"<a:ln w=\"9525\"><a:solidFill><a:srgbClr val=\"{line}\"/></a:solidFill></a:ln>"
        self.add(
            slide,
            f"""
            <p:sp><p:nvSpPr><p:cNvPr id=\"{sp_id(self.counter)}\" name=\"rect\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
            <p:spPr><a:xfrm><a:off x=\"{emu(x)}\" y=\"{emu(y)}\"/><a:ext cx=\"{emu(w)}\" cy=\"{emu(h)}\"/></a:xfrm>
            <a:prstGeom prst=\"{geom}\"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val=\"{fill}\">{fill_alpha}</a:srgbClr></a:solidFill>{line_xml}</p:spPr>
            </p:sp>""",
        )

    def text(
        self,
        slide: Slide,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        size: int = 18,
        color: str = THEME["ink"],
        bold: bool = False,
        align: str = "l",
        fill: str | None = None,
        line: str | None = None,
    ) -> None:
        fill_xml = "<a:noFill/>" if fill is None else f"<a:solidFill><a:srgbClr val=\"{fill}\"/></a:solidFill>"
        line_xml = "<a:ln><a:noFill/></a:ln>" if line is None else f"<a:ln w=\"9525\"><a:solidFill><a:srgbClr val=\"{line}\"/></a:solidFill></a:ln>"
        self.add(
            slide,
            f"""
            <p:sp><p:nvSpPr><p:cNvPr id=\"{sp_id(self.counter)}\" name=\"text\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
            <p:spPr><a:xfrm><a:off x=\"{emu(x)}\" y=\"{emu(y)}\"/><a:ext cx=\"{emu(w)}\" cy=\"{emu(h)}\"/></a:xfrm>
            <a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>
            {tx_body(text, size, color, bold, align)}</p:sp>""",
        )

    def line(self, slide: Slide, x1: float, y1: float, x2: float, y2: float, color: str = THEME["line"], width: int = 2) -> None:
        self.add(
            slide,
            f"""
            <p:cxnSp><p:nvCxnSpPr><p:cNvPr id=\"{sp_id(self.counter)}\" name=\"line\"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
            <p:spPr><a:xfrm><a:off x=\"{emu(x1)}\" y=\"{emu(y1)}\"/><a:ext cx=\"{emu(x2 - x1)}\" cy=\"{emu(y2 - y1)}\"/></a:xfrm>
            <a:prstGeom prst=\"line\"><a:avLst/></a:prstGeom><a:ln w=\"{width * 12700}\"><a:solidFill><a:srgbClr val=\"{color}\"/></a:solidFill></a:ln></p:spPr></p:cxnSp>""",
        )

    def bg(self, slide: Slide) -> None:
        self.rect(slide, 0, 0, SLIDE_W, SLIDE_H, THEME["bg"], None, False)
        self.rect(slide, 9.85, -0.4, 3.9, 8.4, "EFE2D1", None, True, 55000)

    def title(self, slide: Slide, title: str, subtitle: str = "") -> None:
        self.text(slide, title, 0.55, 0.35, 8.7, 0.45, 22, THEME["primary"], True)
        if subtitle:
            self.text(slide, subtitle, 0.58, 0.82, 9.2, 0.28, 8, THEME["muted"])
        self.line(slide, 0.55, 1.16, 12.25, 1.16, THEME["line"], 1)


def slide_xml(slide: Slide) -> str:
    body = "\n".join(shape.xml for shape in slide.shapes)
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>{body}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def content_types(n: int) -> str:
    slides = "\n".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1))
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
<Default Extension=\"xml\" ContentType=\"application/xml\"/>
<Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>
<Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>
<Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>
<Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>
<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>
<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>
{slides}
</Types>"""


def presentation_xml(n: int) -> str:
    ids = "\n".join(f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, n + 1))
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">
<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId{n + 1}\"/></p:sldMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst><p:sldSz cx=\"{emu(SLIDE_W)}\" cy=\"{emu(SLIDE_H)}\" type=\"wide\"/><p:notesSz cx=\"6858000\" cy=\"9144000\"/><p:defaultTextStyle/></p:presentation>"""


def presentation_rels(n: int) -> str:
    rels = [f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, n + 1)]
    rels.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>')
    rels.append(f'<Relationship Id="rId{n + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>')
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">{''.join(rels)}</Relationships>"


ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""
THEME_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="LingGuide"><a:themeElements><a:clrScheme name="LingGuide"><a:dk1><a:srgbClr val="1E2A24"/></a:dk1><a:lt1><a:srgbClr val="F8F5EF"/></a:lt1><a:dk2><a:srgbClr val="2D6A4F"/></a:dk2><a:lt2><a:srgbClr val="FBFAF7"/></a:lt2><a:accent1><a:srgbClr val="2D6A4F"/></a:accent1><a:accent2><a:srgbClr val="B07D4F"/></a:accent2><a:accent3><a:srgbClr val="2B6F8A"/></a:accent3><a:accent4><a:srgbClr val="7C9A74"/></a:accent4><a:accent5><a:srgbClr val="40916C"/></a:accent5><a:accent6><a:srgbClr val="B94747"/></a:accent6><a:hlink><a:srgbClr val="2B6F8A"/></a:hlink><a:folHlink><a:srgbClr val="7C9A74"/></a:folHlink></a:clrScheme><a:fontScheme name="LingGuide"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme><a:fmtScheme name="LingGuide"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>"""
SLIDE_LAYOUT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"""
SLIDE_MASTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"""


def build_deck() -> Builder:
    b = Builder()

    s = b.slide("cover")
    b.rect(s, 0.65, 0.75, 2.0, 0.24, THEME["primary"], None, True)
    b.text(s, "软件杯项目答辩", 0.78, 0.79, 1.7, 0.1, 7, THEME["white"], True, "ctr")
    b.text(s, "灵境导游", 0.72, 1.55, 5.6, 0.72, 30, THEME["primary"], True)
    b.text(s, "AI 数字人智慧导览系统", 0.76, 2.3, 5.2, 0.38, 18, THEME["ink"], True)
    b.text(s, "重点：多模态交互、可信知识问答、实时工具调用、景区内容运营闭环", 0.78, 2.88, 6.8, 0.42, 12, THEME["muted"])
    for i, (num, label, color) in enumerate([("22", "景点内容", THEME["primary"]), ("36", "向量分块", THEME["lake"]), ("15", "FAQ", THEME["accent"]), ("5", "预设路线", THEME["sage"])]):
        x = 0.78 + i * 1.62
        b.rect(s, x, 4.55, 1.36, 0.9, THEME["white"], THEME["line"], True)
        b.text(s, num, x + 0.12, 4.72, 0.55, 0.22, 20, color, True)
        b.text(s, label, x + 0.13, 5.08, 0.9, 0.16, 8, THEME["muted"])
    b.rect(s, 7.8, 1.05, 4.55, 5.25, THEME["white"], THEME["line"], True)
    b.text(s, "一句话定位", 8.18, 1.42, 1.6, 0.25, 10, THEME["accent"], True)
    b.text(s, "把静态景区资料升级为会听、会答、会讲、会推荐、会反馈的数字人导游。", 8.18, 1.9, 3.52, 1.0, 19, THEME["ink"], True)
    b.text(s, "示范景区：无锡灵山胜境\n当前状态：后端 8000、游客端 3000、管理端 3001 已联通", 8.2, 4.28, 3.6, 0.5, 10, THEME["muted"])

    s = b.slide("problem")
    b.title(s, "01 选题背景：景区导览从展示走向陪伴", "面向游客体验和景区运营的双侧问题")
    items = [
        ("游客侧", "讲解依赖人工或静态牌示，问题碎片化，老人、亲子、文化深度需求差异大。", THEME["primary"]),
        ("知识侧", "景区资料分散在文档、FAQ、页面中，模型直接回答容易幻觉，事实可信度难保证。", THEME["lake"]),
        ("运营侧", "游客问了什么、哪里不满意、哪些知识缺口需要补充，传统系统很难形成闭环。", THEME["accent"]),
    ]
    for i, (head, text, color) in enumerate(items):
        x = 0.72 + i * 4.05
        b.rect(s, x, 1.75, 3.55, 3.25, THEME["white"], THEME["line"], True)
        b.rect(s, x, 1.75, 0.12, 3.25, color, None, False)
        b.text(s, head, x + 0.35, 2.05, 1.2, 0.28, 16, color, True)
        b.text(s, text, x + 0.35, 2.65, 2.7, 1.15, 15, THEME["ink"], True)
        b.text(s, "对应创新：" + ["多模态数字人", "RAG+FAQ可信问答", "管理后台+感受度报告"][i], x + 0.35, 4.25, 2.6, 0.3, 9, THEME["muted"])
    b.text(s, "答辩主线：不是做一个聊天窗口，而是做景区导览业务闭环。", 0.85, 5.85, 10.8, 0.34, 18, THEME["primary"], True)

    s = b.slide("architecture")
    b.title(s, "02 系统架构：游客端、AI 后端、管理端三层闭环", "Vue3 + FastAPI + RAG + DeepSeek/本地模型 + 高德工具 + 3D 数字人")
    cols = [("游客交互端", "语音输入\n文本对话\n3D数字人播报\n路线地图", THEME["primary"]), ("FastAPI 智能中枢", "FAQ优先\nRAG检索\nLLM生成\n情感分析\n日志沉淀", THEME["lake"]), ("外部能力", "讯飞ASR\nEdge-TTS\n高德天气/地理编码\n魔珐星云3D", THEME["accent"]), ("管理后台", "知识库管理\n景点/路线CRUD\n数据大屏\n感受度报告", THEME["sage"])]
    for i, (head, text, color) in enumerate(cols):
        x = 0.7 + i * 3.05
        b.rect(s, x, 1.72, 2.55, 3.35, THEME["white"], THEME["line"], True)
        b.rect(s, x + 0.22, 1.98, 0.36, 0.36, color, None, True)
        b.text(s, head, x + 0.7, 1.98, 1.55, 0.25, 12, color, True)
        b.text(s, text, x + 0.34, 2.68, 1.9, 1.5, 13, THEME["ink"], True)
        if i < 3:
            b.line(s, x + 2.55, 3.38, x + 3.03, 3.38, THEME["muted"], 2)
    b.rect(s, 1.05, 5.7, 10.9, 0.62, "EAF3EE", None, True)
    b.text(s, "核心闭环：游客问题 → 知识检索/工具调用 → 数字人讲解 → 交互日志 → 运营分析 → 内容更新", 1.25, 5.9, 10.2, 0.2, 13, THEME["primary"], True, "ctr")

    s = b.slide("progress")
    b.title(s, "03 当前进度：核心演示链路已打通", "后端、游客端、管理端已启动并通过 HTTP 校验")
    progress = [("基础环境", 1.0), ("AI问答链路", 1.0), ("前后端联调", 1.0), ("地图与路线", 1.0), ("内容运营", 0.92), ("文档与演示", 0.65)]
    for i, (name, pct) in enumerate(progress):
        y = 1.6 + i * 0.68
        b.text(s, name, 0.9, y, 1.6, 0.18, 11, THEME["ink"], True)
        b.rect(s, 2.45, y + 0.03, 6.4, 0.16, THEME["soft"], None, True)
        b.rect(s, 2.45, y + 0.03, 6.4 * pct, 0.16, THEME["primary"] if pct == 1 else THEME["accent"], None, True)
        b.text(s, f"{round(pct * 100)}%", 9.05, y, 0.5, 0.16, 9, THEME["muted"])
    stats = [("22", "景点可编辑"), ("5", "路线可管理"), ("36", "知识分块"), ("15", "FAQ问答"), ("3", "运行端口")]
    for i, (num, label) in enumerate(stats):
        x = 0.9 + i * 2.32
        b.rect(s, x, 6.0, 1.78, 0.62, THEME["white"], THEME["line"], True)
        b.text(s, num, x + 0.18, 6.12, 0.45, 0.18, 18, THEME["primary"], True)
        b.text(s, label, x + 0.72, 6.18, 0.82, 0.12, 8, THEME["muted"])

    s = b.slide("innovation-matrix")
    b.title(s, "04 创新点总览：五个可答辩的差异化能力", "从技术拼装升级为景区业务系统")
    matrix = [
        ("多模态交互", "文本/语音/数字人播报", "游客体验"),
        ("可信问答", "FAQ优先 + bge向量RAG + 防幻觉prompt", "内容可信"),
        ("实时工具", "DeepSeek function calling 调高德天气", "时效信息"),
        ("内容运营", "景点/路线/知识库后台可编辑", "景区管理"),
        ("反馈闭环", "情感分析 + 热点问题 + 知识缺口", "持续优化"),
    ]
    for i, (a, btxt, c) in enumerate(matrix):
        y = 1.55 + i * 0.86
        color = [THEME["primary"], THEME["lake"], THEME["accent"], THEME["sage"], THEME["primary2"]][i]
        b.rect(s, 0.78, y, 11.65, 0.58, THEME["white"], THEME["line"], True)
        b.rect(s, 0.78, y, 0.13, 0.58, color, None, False)
        b.text(s, f"创新 {i + 1}", 1.02, y + 0.18, 0.72, 0.1, 7, color, True)
        b.text(s, a, 1.9, y + 0.14, 1.55, 0.16, 13, THEME["ink"], True)
        b.text(s, btxt, 4.1, y + 0.14, 4.35, 0.16, 12, THEME["muted"])
        b.text(s, c, 9.7, y + 0.14, 1.35, 0.16, 12, color, True, "ctr")

    s = b.slide("innovation-1")
    b.title(s, "05 创新点一：多模态数字人导游闭环", "从问答机器人变成会讲解的导游角色")
    flow = [("游客输入", "语音 / 文本"), ("智能理解", "ASR + 会话上下文"), ("知识回答", "FAQ / RAG / LLM"), ("情感驱动", "表情标签"), ("数字人讲解", "3D播报 / TTS")]
    for i, (head, text) in enumerate(flow):
        x = 0.65 + i * 2.45
        b.rect(s, x, 2.05, 1.85, 1.0, THEME["white"], THEME["line"], True)
        b.text(s, head, x + 0.18, 2.27, 1.05, 0.16, 12, THEME["primary"], True)
        b.text(s, text, x + 0.18, 2.64, 1.22, 0.14, 9, THEME["muted"])
        if i < 4:
            b.line(s, x + 1.86, 2.55, x + 2.36, 2.55, THEME["accent"], 2)
    b.rect(s, 0.8, 4.22, 5.6, 1.0, "EAF3EE", None, True)
    b.text(s, "已实现证据", 1.08, 4.45, 1.0, 0.16, 12, THEME["primary"], True)
    b.text(s, "ChatView 自动挂载 XingyunStage；WS 收到 llm_done 后可驱动数字人 speak；保留独立 TTS 播放。", 2.05, 4.38, 3.9, 0.28, 10, THEME["ink"])
    b.rect(s, 6.85, 4.22, 4.9, 1.0, "F4EDE3", None, True)
    b.text(s, "答辩话术", 7.13, 4.45, 1.0, 0.16, 12, THEME["accent"], True)
    b.text(s, "交互不是停留在文本框，而是把回答转成可听、可看的导游讲解。", 8.05, 4.38, 3.1, 0.28, 10, THEME["ink"])

    s = b.slide("innovation-2")
    b.title(s, "06 创新点二：可信知识问答，不让模型自由发挥", "FAQ 快答 + 语义检索 + 来源约束 + 降级兜底")
    layers = [("FAQ 精确匹配", "门票、开放时间、高频问题秒回"), ("bge-large-zh 向量检索", "36 个景区知识分块，top_k=5"), ("Prompt 防幻觉", "片段外不编造，片段不足就诚实说明"), ("离线降级", "模型/向量依赖不可用时仍可关键词应答")]
    for i, (head, text) in enumerate(layers):
        y = 1.65 + i * 0.86
        b.rect(s, 1.0 + i * 0.35, y, 8.3 - i * 0.7, 0.58, ["F4EDE3", "EAF3EE", "E8F1F5", "F5F1EB"][i], THEME["line"], True)
        b.text(s, head, 1.35 + i * 0.35, y + 0.16, 1.8, 0.16, 12, THEME["ink"], True)
        b.text(s, text, 3.45 + i * 0.35, y + 0.16, 4.6, 0.16, 10, THEME["muted"])
    b.rect(s, 9.55, 1.75, 2.35, 2.6, THEME["white"], THEME["line"], True)
    b.text(s, "量化状态", 9.9, 2.05, 0.9, 0.18, 12, THEME["primary"], True)
    b.text(s, "36", 10.0, 2.62, 0.78, 0.3, 28, THEME["primary"], True)
    b.text(s, "知识分块", 10.85, 2.79, 0.8, 0.12, 8, THEME["muted"])
    b.text(s, "15", 10.0, 3.35, 0.78, 0.3, 28, THEME["accent"], True)
    b.text(s, "FAQ", 10.85, 3.52, 0.8, 0.12, 8, THEME["muted"])
    b.text(s, "核心价值：把景区官方资料变成模型回答边界。", 1.0, 5.72, 8.7, 0.25, 17, THEME["primary"], True)

    s = b.slide("innovation-3")
    b.title(s, "07 创新点三：实时工具调用，让导游能回答今天", "DeepSeek function calling + 高德天气工具")
    b.rect(s, 0.9, 1.65, 11.25, 2.0, THEME["white"], THEME["line"], True)
    steps = ["游客问：要带伞吗？", "模型判断需实时信息", "调用 amap_weather", "高德返回实况/预报", "生成出行建议"]
    for i, st in enumerate(steps):
        x = 1.1 + i * 2.12
        b.rect(s, x, 2.25, 1.6, 0.46, [THEME["primary"], THEME["lake"], THEME["accent"], THEME["sage"], THEME["primary2"]][i], None, True)
        b.text(s, st, x + 0.08, 2.41, 1.42, 0.08, 7, THEME["white"], True, "ctr")
        if i < 4:
            b.line(s, x + 1.61, 2.48, x + 2.03, 2.48, THEME["muted"], 2)
    b.rect(s, 1.05, 4.35, 4.45, 1.05, "E8F1F5", None, True)
    b.text(s, "当前实时接口", 1.35, 4.62, 1.2, 0.15, 11, THEME["lake"], True)
    b.text(s, "无锡滨湖区灵山胜境：多云，34℃，湿度52%，未来4天预报可展示。", 2.55, 4.55, 2.4, 0.25, 10, THEME["ink"])
    b.rect(s, 6.05, 4.35, 4.95, 1.05, "F4EDE3", None, True)
    b.text(s, "关键细节", 6.35, 4.62, 0.9, 0.15, 11, THEME["accent"], True)
    b.text(s, "scope 默认无锡，避免灵山胜境同名地理编码误匹配。", 7.18, 4.55, 2.95, 0.25, 10, THEME["ink"])

    s = b.slide("innovation-4")
    b.title(s, "08 创新点四：景区内容可运营，而不是写死在页面里", "管理端编辑后，游客端实时读取后端数据")
    blocks = [("景点管理", "22个景点\n详情/亮点/贴士/坐标/周边"), ("路线管理", "5条路线\n时长/距离/难度/景点顺序"), ("知识库管理", "文档上传\nFAQ CRUD\n统计状态"), ("双端共享", "图片由后端统一服务\n游客端/管理端复用")]
    for i, (head, text) in enumerate(blocks):
        x = 0.75 + (i % 2) * 5.95
        y = 1.65 + (i // 2) * 1.85
        b.rect(s, x, y, 5.2, 1.28, THEME["white"], THEME["line"], True)
        b.text(s, head, x + 0.3, y + 0.25, 1.4, 0.18, 14, [THEME["primary"], THEME["lake"], THEME["accent"], THEME["sage"]][i], True)
        b.text(s, text, x + 2.0, y + 0.24, 2.6, 0.38, 12, THEME["ink"], True)
    b.rect(s, 1.0, 5.65, 10.65, 0.58, "EAF3EE", None, True)
    b.text(s, "创新价值：景区运营人员可持续维护内容，AI 导游随业务更新同步进化。", 1.28, 5.84, 9.6, 0.14, 13, THEME["primary"], True, "ctr")

    s = b.slide("innovation-5")
    b.title(s, "09 创新点五：游客反馈分析反哺知识库", "交互日志 → 情感趋势 → 热点问题 → 知识缺口")
    b.rect(s, 0.9, 1.62, 11.25, 3.25, THEME["white"], THEME["line"], True)
    labels = [("问答日志", "query/response\n耗时/来源"), ("情感分析", "positive/neutral/negative\n情绪分数"), ("运营洞察", "热点问题\n峰值时段"), ("知识补全", "未覆盖问题\nFAQ/文档更新")]
    for i, (head, text) in enumerate(labels):
        x = 1.25 + i * 2.65
        b.rect(s, x, 2.25, 1.88, 1.05, ["EAF3EE", "E8F1F5", "F4EDE3", "EEF3EA"][i], None, True)
        b.text(s, head, x + 0.2, 2.47, 1.1, 0.16, 12, THEME["ink"], True)
        b.text(s, text, x + 0.2, 2.82, 1.35, 0.24, 8, THEME["muted"])
        if i < 3:
            b.line(s, x + 1.88, 2.78, x + 2.42, 2.78, THEME["accent"], 2)
    b.text(s, "当前大屏已能从真实交互表计算满意度、热门问题、近7天趋势；没有数据时有演示默认值兜底。", 1.05, 5.65, 10.4, 0.26, 13, THEME["primary"], True)

    s = b.slide("demo")
    b.title(s, "10 现场演示路径：按创新点组织，不按页面罗列", "建议控制在 4-5 分钟")
    demo = [
        ("游客端首页", "展示景点卡片来自后端 22 条数据"),
        ("对话页", "问灵山大佛有多高/推荐路线，看流式回答与数字人播报"),
        ("路线页", "按兴趣生成路线并在高德地图上绘制"),
        ("天气卡片", "问今天要带伞吗，展示实时工具调用价值"),
        ("管理端", "编辑景点/路线/FAQ，说明内容运营闭环"),
        ("数据大屏", "展示热点问题和感受度报告"),
    ]
    for i, (head, text) in enumerate(demo):
        y = 1.45 + i * 0.72
        b.rect(s, 1.0, y, 0.42, 0.42, THEME["primary"] if i < 3 else THEME["accent"], None, True)
        b.text(s, str(i + 1), 1.12, y + 0.14, 0.12, 0.08, 9, THEME["white"], True, "ctr")
        b.text(s, head, 1.72, y + 0.1, 1.55, 0.16, 12, THEME["ink"], True)
        b.text(s, text, 3.6, y + 0.1, 6.4, 0.16, 11, THEME["muted"])
    b.rect(s, 1.0, 6.08, 10.8, 0.42, "F4EDE3", None, True)
    b.text(s, "演示口径：每一步都对应一个创新点，避免只展示页面效果。", 1.28, 6.22, 10.0, 0.1, 11, THEME["accent"], True, "ctr")

    s = b.slide("technical")
    b.title(s, "11 技术亮点：工程上可落地、可降级、可运营", "答辩时可用于回应实现细节问题")
    tech = [
        ("WebSocket 流式交互", "llm_stream / llm_done 分阶段推送，前端可边生成边展示。"),
        ("模型防编造", "路线推荐只允许从真实景点候选中选择，输出后再校验匹配。"),
        ("工具调用上限", "function calling 最多 3 轮，避免模型反复调工具导致超时。"),
        ("依赖降级", "向量库/LLM不可用时降级关键词或内置应答，保证演示稳定。"),
        ("数据闭环", "交互记录持久化，管理端从真实数据计算运营指标。"),
    ]
    for i, (head, text) in enumerate(tech):
        x = 0.86 + (i % 2) * 5.7
        y = 1.55 + (i // 2) * 1.35
        w = 5.05 if i < 4 else 10.75
        left = x if i < 4 else 0.86
        b.rect(s, left, y, w, 0.92, THEME["white"], THEME["line"], True)
        b.text(s, head, left + 0.28, y + 0.2, 1.8, 0.15, 12, THEME["primary"], True)
        b.text(s, text, left + 2.15, y + 0.17, w - 2.55, 0.22, 9, THEME["muted"])

    s = b.slide("value")
    b.title(s, "12 应用价值：游客体验提升，景区运营降本增效", "面向景区数字化转型的可复制方案")
    values = [("游客", "随时问、听得懂、讲得清\n老人/亲子/文化深度需求可被个性化响应"), ("景区", "减少重复咨询压力\n把热点问题转化为运营决策"), ("平台", "一个景区跑通后可复制到多景区\n更换知识库和景点数据即可迁移")]
    for i, (head, text) in enumerate(values):
        x = 0.82 + i * 4.0
        b.rect(s, x, 1.82, 3.36, 3.05, THEME["white"], THEME["line"], True)
        b.text(s, head, x + 0.35, 2.18, 0.9, 0.23, 18, [THEME["primary"], THEME["accent"], THEME["lake"]][i], True)
        b.text(s, text, x + 0.35, 2.85, 2.42, 0.78, 14, THEME["ink"], True)
    b.text(s, "可复制路径：景区资料导入 → 景点/路线配置 → 工具 key 配置 → 数字人形象接入 → 运营看板上线", 1.0, 5.86, 10.7, 0.22, 13, THEME["primary"], True, "ctr")

    s = b.slide("ending")
    b.rect(s, 0, 0, SLIDE_W, SLIDE_H, THEME["primary"], None, False)
    b.rect(s, 8.4, -0.2, 4.6, 8.0, "40916C", None, True, 60000)
    b.text(s, "结论", 0.92, 1.05, 1.2, 0.32, 18, THEME["white"], True)
    b.text(s, "灵境导游的创新，不是单点 AI 能力，而是把多模态交互、可信知识、实时工具和运营反馈连成景区导览闭环。", 0.92, 1.78, 7.0, 1.28, 28, THEME["white"], True)
    b.text(s, "已具备现场演示条件：后端 8000、游客端 3000、管理端 3001。", 0.98, 4.78, 5.9, 0.25, 13, "DDEBE4", True)
    b.text(s, "谢谢各位老师", 0.98, 5.78, 2.2, 0.28, 18, "F4EDE3", True)

    return b


def write_pptx(builder: Builder, out: Path) -> None:
    n = len(builder.slides)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types(n))
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("ppt/presentation.xml", presentation_xml(n))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(n))
        z.writestr("ppt/theme/theme1.xml", THEME_XML)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>")
        z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/><Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"../theme/theme1.xml\"/></Relationships>")
        for i, slide in enumerate(builder.slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(slide))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/></Relationships>")
        z.writestr("docProps/core.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"><dc:title>灵境导游答辩PPT</dc:title><dc:subject>创新点答辩</dc:subject><dc:creator>Claude Code</dc:creator><cp:keywords>AI数字人;智慧导览;RAG;多模态;景区运营</cp:keywords><dc:description>以创新点为重点的项目答辩PPT</dc:description></cp:coreProperties>")
        z.writestr("docProps/app.xml", f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\"><Application>Claude Code</Application><PresentationFormat>宽屏</PresentationFormat><Slides>{n}</Slides><ScaleCrop>false</ScaleCrop><Company>LingGuide</Company></Properties>")


def main() -> None:
    os.chdir(Path(__file__).resolve().parents[1])
    builder = build_deck()
    write_pptx(builder, OUT)
    print(f"generated={OUT.resolve()}")
    print(f"slides={len(builder.slides)} size={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
