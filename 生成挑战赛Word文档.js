const fs = require('fs');
const path = require('path');
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  Header,
  ImageRun,
  LevelFormat,
  PageBreak,
  PageNumber,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} = require('docx');

const ROOT = 'E:/ruanjianbei';
const OUTPUT = path.join(ROOT, '灵境导游_挑战赛参赛理由及作品亮点.docx');
const HERO = path.join(ROOT, 'frontend-visitor/public/images/lingshan_1.jpeg');
const LOGO = path.join(ROOT, 'frontend-visitor/public/images/logo.png');

const C = {
  green: '2D6A4F',
  greenDark: '173F32',
  greenLight: 'E7F0EA',
  gold: 'B07D4F',
  goldLight: 'F3E8DA',
  sand: 'F7F3ED',
  ink: '18242D',
  text: '33444C',
  muted: '65747A',
  line: 'D8D4CC',
  white: 'FFFFFF',
  warn: 'A85D3A',
};

const FONT = 'Microsoft YaHei';
const FONT_DISPLAY = 'STZhongsong';
const noBorder = { style: BorderStyle.NONE, size: 0, color: C.white };
const lineBorder = { style: BorderStyle.SINGLE, size: 5, color: C.line };
const greenBorder = { style: BorderStyle.SINGLE, size: 8, color: C.green };

function run(text, opts = {}) {
  return new TextRun({ text, font: opts.font || FONT, size: opts.size || 22, color: opts.color || C.text, bold: !!opts.bold, italics: !!opts.italics });
}

function p(text, opts = {}) {
  const children = Array.isArray(text) ? text : [run(text, opts)];
  return new Paragraph({
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    spacing: { before: opts.before || 0, after: opts.after === undefined ? 130 : opts.after, line: opts.line || 360 },
    indent: opts.indent === false ? undefined : { firstLine: opts.firstLine === undefined ? 440 : opts.firstLine },
    keepNext: !!opts.keepNext,
    keepLines: !!opts.keepLines,
    children,
  });
}

function label(text) {
  return new Paragraph({
    spacing: { before: 140, after: 90 },
    keepNext: true,
    children: [run(text, { size: 19, bold: true, color: C.gold })],
  });
}

function heading(text, level = 1) {
  if (level === 1) {
    return new Paragraph({
      spacing: { before: 360, after: 150 },
      keepNext: true,
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.gold, space: 6 } },
      children: [run(text, { size: 32, bold: true, color: C.greenDark, font: FONT_DISPLAY })],
    });
  }
  return new Paragraph({
    spacing: { before: 260, after: 100 },
    keepNext: true,
    children: [run(text, { size: 26, bold: true, color: C.green })],
  });
}

function quote(text) {
  return new Table({
    columnWidths: [9320],
    margins: { top: 180, bottom: 180, left: 260, right: 260 },
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9320, type: WidthType.DXA },
      borders: { top: noBorder, bottom: noBorder, right: noBorder, left: greenBorder },
      shading: { fill: C.greenLight, type: ShadingType.CLEAR },
      children: [new Paragraph({
        spacing: { after: 0, line: 360 },
        children: [run(text, { size: 23, bold: true, color: C.greenDark })],
      })],
    })] })],
  });
}

function callout(title, text, tone = 'green') {
  const fill = tone === 'gold' ? C.goldLight : C.greenLight;
  const accent = tone === 'gold' ? C.gold : C.green;
  return new Table({
    columnWidths: [9320],
    margins: { top: 150, bottom: 150, left: 220, right: 220 },
    rows: [new TableRow({
      cantSplit: true,
      children: [new TableCell({
        width: { size: 9320, type: WidthType.DXA },
        borders: { top: { ...lineBorder, color: accent }, bottom: { ...lineBorder, color: accent }, left: { ...lineBorder, color: accent }, right: { ...lineBorder, color: accent } },
        shading: { fill, type: ShadingType.CLEAR },
        children: [new Paragraph({ spacing: { after: 70 }, children: [run(title, { size: 20, bold: true, color: accent })] }), p(text, { indent: false, after: 0, line: 330 })],
      })],
    })],
  });
}

function statCard(value, title, note, fill = C.greenLight, accent = C.green) {
  return new TableCell({
    width: { size: 2255, type: WidthType.DXA },
    borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder },
    shading: { fill, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 150, bottom: 150, left: 150, right: 150 },
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 55 }, children: [run(value, { size: 30, bold: true, color: accent })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 35 }, children: [run(title, { size: 18, bold: true, color: C.ink })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0, line: 260 }, children: [run(note, { size: 15, color: C.muted })] }),
    ],
  });
}

function evidenceTable(rows) {
  const widths = [1900, 1800, 5620];
  const cell = (text, width, opts = {}) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: { top: lineBorder, bottom: lineBorder, left: lineBorder, right: lineBorder },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      spacing: { before: 45, after: 45, line: 275 },
      children: [run(text, { size: opts.header ? 18 : 17, bold: !!opts.header, color: opts.header ? C.white : (opts.color || C.text) })],
    })],
  });
  return new Table({
    columnWidths: widths,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    rows: [
      new TableRow({ tableHeader: true, children: [cell('验证维度', widths[0], { fill: C.green, header: true, center: true }), cell('当前结果', widths[1], { fill: C.green, header: true, center: true }), cell('正确解读', widths[2], { fill: C.green, header: true, center: true })] }),
      ...rows.map((r, i) => new TableRow({ children: [cell(r[0], widths[0], { fill: i % 2 ? C.sand : C.white }), cell(r[1], widths[1], { fill: i % 2 ? C.sand : C.white, center: true, color: r[3] || C.greenDark }), cell(r[2], widths[2], { fill: i % 2 ? C.sand : C.white })] })),
    ],
  });
}

function bullet(text, ref = 'bullets') {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 95, line: 335 },
    children: [run(text, { size: 21 })],
  });
}

function numbered(title, body) {
  return new Paragraph({
    numbering: { reference: 'numbers', level: 0 },
    spacing: { after: 120, line: 350 },
    children: [run(`${title}：`, { size: 21, bold: true, color: C.greenDark }), run(body, { size: 21 })],
  });
}

const header = new Header({ children: [new Paragraph({
  alignment: AlignmentType.RIGHT,
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.gold, space: 4 } },
  spacing: { after: 40 },
  children: [run('LINGGUIDE  ·  挑战赛参赛材料', { size: 15, bold: true, color: C.gold })],
})] });

const footer = new Footer({ children: [new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 80 },
  children: [run('灵境导游  |  ', { size: 15, color: C.muted }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: C.muted })],
})] });

const cover = [
  new Paragraph({ spacing: { after: 90 }, children: [run('CHALLENGE  ·  2026', { size: 18, bold: true, color: C.gold })] }),
  new Paragraph({ spacing: { after: 20 }, children: [run('灵 境 导 游', { size: 54, bold: true, color: C.greenDark, font: FONT_DISPLAY })] }),
  new Paragraph({ spacing: { after: 45 }, children: [run('会倾听，也会带路的 AI 数字人导游', { size: 27, color: C.ink })] }),
  new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 14, color: C.gold, space: 8 } }, spacing: { after: 180 }, children: [run('挑战赛参赛理由及作品亮点', { size: 22, bold: true, color: C.green })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 110 }, children: [new ImageRun({ type: 'jpeg', data: fs.readFileSync(HERO), transformation: { width: 500, height: 500 }, altText: { title: '灵山胜境', description: '灵山大佛与山水景观', name: '灵山胜境封面图' } })] }),
  quote('让游客获得一位“讲得有依据、带路有个性、出错有边界”的数字人导游；让景区拥有一套“知识可运营、服务可观察、经验可复制”的智能服务底座。'),
  new Paragraph({ spacing: { before: 170, after: 70 }, alignment: AlignmentType.CENTER, children: [run('不是给景区加一个聊天框，而是为一次文化抵达建立可信回应。', { size: 20, italics: true, color: C.muted })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

const body = [
  heading('一、为什么参加挑战赛'),
  p('上一轮软件杯未能晋级，让我们真正意识到：一个竞赛作品的价值，不在于功能列表有多长，而在于它是否抓住了真实问题，是否完成了从技术到用户价值的闭环，是否经得起追问和验证。'),
  p('景区从来不缺介绍文字，真正稀缺的是一位能够在游客需要时出现、听懂问题、讲清文化、规划路线，并在不知道时坦诚说“不知道”的导游。许多游客走到一座建筑前，只看到“宏伟”；离开一段历史时，只记住“打卡”。与此同时，人工讲解受时间、语言、客流与成本限制，传统导览又往往是固定音频和静态页面，难以回应“我现在最想知道什么、下一步最适合去哪里”。'),
  quote('人工智能能否既有数字人的温度，也有事实可信的底线；既服务游客的一次旅程，也沉淀景区长期运营的能力？'),
  p('“灵境导游”给出的答案，是把大模型、可解释混合 RAG、实时工具、个性化路线、地图导航、语音交互和 3D 数字人整合为一个完整闭环。游客提出问题后，系统不会把所有内容都交给大模型“猜”，而是先判断问题属于 FAQ、景点与路线、长文档知识还是实时天气，再调用合适的数据路径；最终回答附带可展开的来源依据。没有可靠证据时，系统选择明确拒答，而不是用流畅语言掩盖不确定性。'),
  p('挑战赛强调创新实践与社会价值，这正是我们希望再次出发的原因：让文化不再只是牌匾上的文字，让智能导览不再只是“会聊天的页面”，让可信 AI 真正走入公共文化与文旅服务场景。上一轮的遗憾没有成为终点，而成为我们重新审视用户、重构系统、补齐证据链的起点。我们希望用一个能运行、能验证、能解释、能持续生长的作品，证明学生团队也可以把真实行业问题做到深处。'),

  heading('二、作品核心亮点'),
  heading('亮点 1｜从“会回答”升级为“回答有依据”', 2),
  p('景区知识同时包含专名、数字、时间、历史文化、路线实体和实时天气，单一向量检索很难兼顾。系统建立分层路由：高频确定事实走 FAQ，景点和路线走结构化数据，专名、数字和时间走 FTS5/BM25，语义改写走 BGE 向量检索，实时天气走高德工具。'),
  p('关键词与向量结果经 RRF 融合后，还必须回查 SQLite 中的 canonical Chunk，并通过身份、状态、置信度与时效检查，才能成为 Evidence。回答引用由服务端校验；过期天气、孤儿向量和未知引用不能进入事实回答。'),
  callout('核心价值', '不只是让模型“说得像”，而是让每一个重要事实“查得到出处”；不知道时敢于拒答，本身也是可信服务能力。'),

  heading('亮点 2｜文本、语音、表情与 3D 数字人共用同一条可信回答链', 2),
  p('游客可通过文本或语音发问，回答可转为 TTS 语音，并驱动 3D 数字人的说话状态和情绪表达；同时页面保留 Citation，确保“屏幕上看到的、耳朵里听到的、数字人讲出的”来自同一份回答语义。'),
  p('系统不是把数字人当作装饰动画，而是把它作为文化表达的交互载体：降低阅读门槛，增强陪伴感，让讲解从静态信息变为可对话、可追问的体验。'),
  callout('核心价值', '技术不只提高信息获取效率，也改善人与文化内容相遇的方式。', 'gold'),

  heading('亮点 3｜真实景点约束下的个性化路线', 2),
  p('系统结合游客兴趣、游览时长和对话上下文生成半日或一日路线，并通过真实景点白名单与结构化数据约束结果；当大模型不可用时，仍可进行确定性补全，降低虚构景点风险。路线可保存、再次查看，并在高德地图中显示景点标记与步行路径；规划失败时明确降级提示，不伪装成精确导航。'),
  callout('核心价值', '把“想看什么、能走多久、下一站去哪”连接起来，减少信息很多却不会安排的决策负担。'),

  heading('亮点 4｜实时信息具备来源、时效和失败边界', 2),
  p('天气问题通过工具调用处理，而不是从历史文档中拼接答案。系统记录查询时间、有效期和工具状态，仅 fresh 数据可形成可靠 Evidence；stale 或 error 状态不会被包装成实时事实。地点解析优先采用游客明确给出的城市或区县，并对景区别名进行地域约束。'),
  callout('核心价值', '将“是否过期”纳入答案可信度，让实时服务既有用，也不误导。', 'gold'),

  heading('亮点 5｜游客端与管理端形成“服务—反馈—优化”双端闭环', 2),
  p('游客端覆盖智能问答、Citation、景点详情、兴趣路线、地图天气、收藏与反馈等旅程环节；管理端支持景点和路线内容维护、知识文档与 FAQ 管理、游客反馈处理、数字人配置，以及 RAG 索引健康、测试检索和匿名运行摘要。'),
  p('最近运行摘要只聚合请求数、P50/P95、降级率、异常率及各通道耗时，不返回用户问题和回答正文，兼顾现场诊断与数据最小化。'),
  callout('核心价值', 'AI 不再是一次性演示，而是景区可以维护、观察、纠错和持续优化的服务系统。'),

  heading('亮点 6｜把“稳定演示”当作工程能力，而不是临场运气', 2),
  p('系统采用 shadow build → validate → activate 的索引发布流程。新索引只有在 canonical、FTS、向量数量、ID、内容指纹、Embedding 模型和分块配置全部一致后才会激活；构建或校验失败不会替换当前 active 索引。'),
  callout('核心价值', '创新不止体现在模型选型，更体现在把不确定的 AI 系统做成可验证的工程系统。', 'gold'),

  heading('三、当前可验证成果'),
  new Table({
    columnWidths: [2255, 80, 2255, 80, 2255, 80, 2255],
    rows: [new TableRow({ children: [
      statCard('36/36/36', '三路索引一致', 'canonical / FTS / vector'),
      new TableCell({ width: { size: 80, type: WidthType.DXA }, borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }, children: [new Paragraph({ children: [] })] }),
      statCard('40 条', '演示门禁通过', '人工复核固定竞赛样例', C.goldLight, C.gold),
      new TableCell({ width: { size: 80, type: WidthType.DXA }, borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }, children: [new Paragraph({ children: [] })] }),
      statCard('≈3.34s', '本次评测 P95', '当前环境重新执行结果'),
      new TableCell({ width: { size: 80, type: WidthType.DXA }, borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }, children: [new Paragraph({ children: [] })] }),
      statCard('250 / 4', '后端回归', '250 通过，4 失败', 'FBE9E1', C.warn),
    ] })],
  }),
  new Paragraph({ spacing: { after: 170 }, children: [] }),
  evidenceTable([
    ['冻结知识索引', '36 / 36 / 36', 'canonical Chunk、FTS 行、向量条目数量一致，ID、指纹与配置校验通过'],
    ['FAQ 数据', '15 / 15', 'JSON 与 SQLite mirror 当前快照一致'],
    ['冻结演示评测', '40 条，门禁通过', '固定竞赛样例中，路由、有证据回答、拒答、FAQ、重复稳定与 Citation 指标均通过'],
    ['本次评测延迟', 'P95 约 3.34 秒', '2026-08-01 当前环境重新执行结果，不等同于高并发 SLA'],
    ['真实服务场景', '7 类通过（冻结记录）', '覆盖 FAQ、文档、连续追问、路线、天气、拒答与 trace'],
    ['当前前端构建', '游客端、管理端通过', '2026-08-01 重新执行 TypeScript 检查与 Vite 生产构建成功'],
    ['当前后端回归', '250 通过、4 失败', '失败集中在路线降级数据一致性/多语言用例；已进入修复清单', C.warn],
  ]),
  callout('证据口径说明', '40 条演示门禁用于验证固定竞赛场景，不宣称开放世界准确率为 100%。历史 12 条小样本召回基线 Recall@5 为 0.50，提示检索泛化仍需继续优化。我们选择如实披露边界，因为可信是本作品的技术目标，也是参赛态度。', 'gold'),

  heading('四、创新价值：不是技术堆叠，而是三重转变'),
  numbered('从信息展示到即时陪伴', '游客不再被动寻找页面，而是可以随时提问、追问、听讲解并获得下一步建议。'),
  numbered('从模型生成到证据治理', '回答先经过路由、检索、回查、过滤和引用校验；“不乱答”与“能回答”同等重要。'),
  numbered('从单次交付到持续运营', '景区可维护内容、查看检索状态、处理反馈并优化知识缺口，使系统具有复制到其他景区的基础。'),
  p('项目采用“景区数据适配层 + 通用 AI 编排层 + 双端应用层”的思路。更换景区时，核心工作集中在景点、路线、FAQ、知识文档、地图坐标与品牌数字人配置，而可信检索、引用治理、工具降级和管理诊断能力可以复用。这使作品具有从灵山胜境示范场景走向博物馆、历史街区、遗址公园与城市文化空间的潜力。'),

  heading('五、社会价值与应用前景'),
  bullet('让优质讲解更普惠：为自由行游客、亲子家庭、老年游客和语言需求不同的游客提供更低门槛的文化讲解。'),
  bullet('缓解高峰服务压力：承接高频咨询与基础路线建议，使人工服务更专注于复杂需求与线下关怀。'),
  bullet('促进文化被理解而非只被打卡：通过可追问的故事化讲解，把建筑、历史和礼仪转化为游客愿意听、听得懂、记得住的内容。'),
  bullet('帮助中小景区获得可持续的智能能力：采用轻量单实例架构与可替换模型接口，降低演示和私有化部署门槛。'),
  bullet('形成文旅数据改进闭环：在遵循数据最小化原则的前提下，通过匿名运行摘要和游客主动反馈发现知识缺口与服务问题。'),

  heading('六、我们的态度与挑战赛目标'),
  p('我们不把尚未完成的功能写成成果，也不把固定样例的通过率包装成开放场景的绝对准确率。当前版本定位于受控内网和竞赛演示环境：完整 ASR/TTS/数字人长稳、真实断线重连、路线降级一致性、开放问题召回泛化、生产级认证与隐私合规仍是下一阶段重点。'),
  p('但我们已经证明，这不是停留在概念图里的设想：它有可运行的游客端与管理端，有真实的知识索引和地图数据，有可展开的 Citation，有无证据拒答，有工具失败降级，有自动化门禁，也有主动保留的失败记录。'),
  p('如果获得挑战赛机会，我们希望完成三件事：第一，修复当前 4 项路线降级回归并扩大真实问法评测；第二，完成语音—可信回答—TTS—3D 数字人的连续长稳验收；第三，形成可快速适配第二个文化场景的模板，验证项目并非只服务一处景区。'),
  quote('上一轮未能晋级，让我们学会少一点“我们什么都有”，多一点“我们真正解决了什么”。这一次，我们想带来的不是一位永远自信的 AI 导游，而是一位有温度、有依据、有边界，也能陪景区一起成长的 AI 导游。'),

  new Paragraph({ children: [new PageBreak()] }),
  heading('附录｜报名表精简版参赛理由'),
  p('上一轮软件杯未能晋级，让我们重新认识到：竞赛作品不应只是功能堆叠，而应真正解决问题并经得起验证。景区不缺静态介绍，缺的是一位能随时倾听、讲清文化、规划路线，并在不知道时坦诚拒答的导游。'),
  p('“灵境导游”将可解释混合 RAG、实时天气工具、个性化路线、地图、语音和 3D 数字人整合为游客端与管理端双闭环。系统会先判断问题类型，再选择 FAQ、结构化数据、关键词检索、向量检索或实时工具；所有候选需回查 canonical 知识并经过 Evidence 过滤，回答 Citation 由服务端校验，无可靠证据时不编造。游客得到的不只是“会说话的数字人”，而是一位回答有出处、带路有个性、异常有边界的 AI 导游；景区获得的也不只是展示页面，而是一套可维护、可诊断、可复制的智能服务底座。'),
  p('当前系统已完成 36 条 canonical/FTS/vector 索引一致性校验，40 条人工复核的冻结竞赛演示门禁通过，游客端与管理端生产构建通过；同时我们如实保留 4 项路线降级回归失败与小样本召回短板。我们希望通过挑战赛继续补齐长稳、多语言与跨景区复制验证，让可信 AI 真正服务公共文化传播。上一轮的遗憾不是终点，而是我们从“做出功能”走向“做成作品”的起点。'),
  new Paragraph({ spacing: { before: 260, after: 120 }, alignment: AlignmentType.CENTER, children: [new ImageRun({ type: 'png', data: fs.readFileSync(LOGO), transformation: { width: 110, height: 110 }, altText: { title: '无锡灵山', description: '项目景区标识', name: '无锡灵山标识' } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [run('灵境导游 · 让每一次抵达都有回应', { size: 19, bold: true, color: C.greenDark })] }),
];

const doc = new Document({
  creator: '灵境导游项目团队',
  title: '灵境导游——挑战赛参赛理由及作品亮点',
  subject: '挑战赛参赛材料',
  description: '灵境导游项目参赛理由、作品亮点、社会价值与验证成果',
  keywords: '灵境导游, AI数字人, 智慧文旅, RAG, 挑战赛',
  styles: {
    default: { document: { run: { font: FONT, size: 22, color: C.text }, paragraph: { spacing: { line: 360 } } } },
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 520, hanging: 260 } } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 320 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1080, right: 1293, bottom: 1080, left: 1293, header: 520, footer: 520 },
        pageNumbers: { start: 1, formatType: 'decimal' },
      },
      titlePage: true,
    },
    headers: { default: header },
    footers: { default: footer },
    children: [...cover, ...body],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log(OUTPUT);
});
