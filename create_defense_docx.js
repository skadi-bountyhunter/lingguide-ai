const fs = require('fs');
const { AlignmentType, Document, Footer, Header, HeadingLevel, Packer, PageNumber, Paragraph, TextRun } = require('docx');

const body = (text) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 150, line: 360 }, indent: { firstLine: 480 }, children: [new TextRun({ text })] });
const cue = (text) => new Paragraph({ spacing: { before: 60, after: 100 }, children: [new TextRun({ text: `【画面提示】${text}`, color: '6B7B73', italics: true, size: 20 })] });
const heading = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text })] });

const doc = new Document({
  creator: '灵境导游项目组', title: '《灵境导游》项目答辩视频演讲稿', subject: '项目答辩视频演讲稿',
  styles: {
    default: { document: { run: { font: 'Microsoft YaHei', size: 24, color: '24312B' }, paragraph: { spacing: { line: 360 } } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: 'Microsoft YaHei', size: 40, bold: true, color: '174D3B' }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 360, after: 180 } } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: 'Microsoft YaHei', size: 29, bold: true, color: '1F624A' }, paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 0, keepNext: true } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1276, right: 1440, bottom: 1276, left: 1440 }, pageNumbers: { start: 1, formatType: 'decimal' } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: '灵境导游 · 项目答辩', color: '7A8981', size: 18 })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '—  ', color: '87958E', size: 18 }), new TextRun({ children: [PageNumber.CURRENT], color: '87958E', size: 18 }), new TextRun({ text: '  —', color: '87958E', size: 18 })] })] }) },
    children: [
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: '《灵境导游》项目答辩视频演讲稿' })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 180 }, children: [new TextRun({ text: '预计朗读时长：约 6 分钟', color: '718078', size: 21 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 280 }, children: [new TextRun({ text: '说明：画面提示不需要朗读', color: '8A9790', italics: true, size: 19 })] }),

      heading('一、开场与项目概述'),
      cue('展示项目名称、游客端首页及整体功能架构。'),
      body('各位老师好，我们的项目是《灵境导游》。这是一款面向景区游客与管理人员的智能导游软件。游客端以人工智能数字人为核心，融合文字问答、语音交互、表情反馈和个性化路线规划；管理端则对真实落库的游客交互数据进行统计分析，并支持景点、路线、知识库和数字人角色等内容管理。下面我将重点介绍数字人交互、路线规划，以及后台数据管理大屏。'),

      heading('二、数字人交互页面'),
      cue('进入智能对话页，展示左侧三维数字人和右侧对话区。'),
      body('首先是本项目最具特色的数字人交互页面。页面采用双栏布局：左侧是三维数字人舞台，右侧是智能对话区域。数字人接入魔珐星云能力，页面会直观显示角色名称、连接状态、资源加载进度、当前表情以及播报状态。进入页面后，系统可自动唤醒数字人；游客也可以手动开启或关闭数字人，在沉浸式体验和设备性能之间灵活选择。'),
      cue('依次演示文字提问、语音提问、自动播报和停止播报。'),
      body('在交互方式上，游客既可以输入文字，也可以点击麦克风直接提问。语音会被转换为文本并交给后端处理；系统结合景区知识库生成回答后，除了显示文字内容，还会自动驱动数字人进行语音播报。数字人能够根据回答携带的表达状态呈现相应表情，使讲解不再是机械的文字输出，而更接近真实导游的交流过程。游客还可以对任意回答进行重新播报，或者随时停止当前讲解。'),
      body('在可信度方面，回答支持展示知识来源与引用片段。当检索证据不足或服务降级时，页面也会给出明确提示，避免把不确定内容包装成确定答案。对于路线类问题，回答中会出现“路线推荐”入口，将本轮生成的结构化方案直接带入路线页面。由此，数字人不仅负责“讲”，还承担了从需求理解到后续服务跳转的交互入口。'),

      heading('三、AI 路线规划页面'),
      cue('切换到路线规划页，展示地图、兴趣标签和游览时长。'),
      body('路线规划页面主要由地图、AI规划、已保存路线和预设路线四个版块组成。游客首先可以选择佛教文化、自然风光、历史古迹、亲子游乐、建筑艺术、美食素斋等兴趣标签，并选择半天或全天。点击开始规划后，系统根据兴趣和时间生成结构化路线，其中包含路线名称、预计时长、景点顺序、游览建议和注意事项。'),
      cue('生成一条路线，点击“在地图上显示”，再演示保存路线。'),
      body('生成结果可以一键显示在地图上。地图按照路线中的景点顺序进行呈现，帮助游客快速理解游览位置和行进关系。系统使用同一份结构化数据完成结果展示、地图上图和路线保存，保证三个环节内容一致。生成的路线可以保存到个人账户，之后再次查看或删除。页面还提供后台维护的预设路线，游客可按兴趣筛选，快速查看路线时长、距离、难度、途经景点和游览提示。'),
      body('路线页面还与数字人对话形成联动。如果游客在聊天中提出“帮我规划半日路线”，系统会把本轮已经生成的路线快照直接带到路线页面，而不是重新生成，避免前后景点发生变化。因此，本项目形成了“提出需求、AI理解、数字人讲解、路线落地、地图查看和个人保存”的完整闭环。'),

      heading('四、后台数据管理大屏'),
      cue('进入管理端数据大屏，依次展示顶部筛选、指标卡、图表和明细区域。'),
      body('后台数据大屏用于将游客端产生的交互记录转化为可理解的运营信息。顶部的运营交互总览支持切换今日、近七天和近三十天，并显示数据同步时间、统计范围和刷新状态，方便管理人员明确数据口径。系统还会每分钟自动刷新，也支持手动刷新；如果刷新失败，会保留上一次成功数据并给出提示。'),
      body('第一组是四张核心指标卡。交互次数表示所选范围内成功落库的交互记录；服务会话按照会话编号去重，反映独立服务过程，但不等同于实名游客人数；平均处理耗时用于评估系统端到端响应效率；平均输入情绪得分用于观察游客提问中呈现的情绪信号，需要强调，它不是满意度评分。'),
      body('第二组是趋势图表。交互趋势按照小时或自然日统计使用量，可帮助景区识别咨询高峰；情绪趋势展示各时间段的平均输入情绪得分和有效样本数，用于发现游客情绪变化。第三组是重复问句前八名，管理人员可以据此识别游客最关心的问题，并反向补充知识库、优化页面提示或调整服务内容。'),
      body('下方的最近活动版块，统计最近一段时间的活跃会话和交互次数，用于快速判断系统当前活跃程度；交互方式构成版块，则展示文本、语音和其他方式的数量及占比，为后续优化语音识别或文字问答提供依据。最后，图表明细表列出每个时间桶的交互次数、平均情绪得分和样本量，使可视化结果可以进一步核对。'),
      cue('展示管理端左侧导航栏。'),
      body('除数据大屏外，后台还包括知识库管理与RAG诊断，用于维护回答依据和检查检索效果；景点管理与路线管理，用于维护游客端展示内容；星云角色管理，用于切换数字人角色及配置；感受度报告、用户管理、反馈管理和通知管理，则分别承担游客感受分析、账户维护、意见处理和消息发布。管理人员可以先从大屏发现问题，再进入对应模块调整，形成“数据发现、内容管理、服务优化”的运营闭环。'),

      heading('五、总结'),
      cue('回到项目总览，展示“数字人—路线—管理后台”的闭环示意。'),
      body('总体来说，《灵境导游》实现了三个关键融合：一是景区知识与智能问答的融合，让游客能够自然提问；二是数字人、语音和表情的融合，让信息服务更有陪伴感；三是游客服务与后台数据的融合，让每一次真实交互都能够沉淀为运营依据。项目最终实现了从“游客咨询”到“路线执行”，再到“景区管理优化”的完整闭环。我的介绍到这里，谢谢各位老师。'),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync('E:/ruanjianbei/灵境导游项目答辩视频演讲稿.docx', buffer);
  console.log('E:/ruanjianbei/灵境导游项目答辩视频演讲稿.docx');
});
