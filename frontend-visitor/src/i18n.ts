import { createI18n } from 'vue-i18n'

export const LOCALE_KEY = 'lingguide_locale'
export type AppLocale = 'zh-CN' | 'en' | 'ja' | 'ko'

function initialLocale(): AppLocale {
  const saved = localStorage.getItem(LOCALE_KEY)
  return saved === 'en' || saved === 'ja' || saved === 'ko' || saved === 'zh-CN' ? saved : 'zh-CN'
}

const zhCN = {
  common: {
    back: '返回', loading: '加载中...', retry: '重试', developing: '功能开发中', operationFailed: '操作失败',
    loginExpired: '登录状态已失效，请重新登录', spot: '景点', route: '路线', submit: '提交', cancel: '取消', delete: '删除',
  },
  tab: { home: '导览', chat: '对话', route: '路线', profile: '我的' },
  auth: {
    brand: '灵境导游', subtitle: 'AI智慧导览 · 灵山胜境', login: '登录', register: '注册', phone: '请输入手机号',
    code: '验证码', getCode: '获取验证码', resend: '重新获取', password: '请输入密码', setPassword: '设置密码（6-20位）',
    confirmPassword: '确认密码', passwordMismatch: '两次密码输入不一致', forgot: '忘记密码？', reset: '重置密码',
    newPassword: '请输入新密码（6-20位）', resetSuccess: '密码重置成功，请登录', codeSent: '验证码已发送', codeDev: '验证码：{code}（开发模式直接显示）',
    codeFailed: '获取验证码失败', requestFailed: '请求失败', loginSuccess: '登录成功', registerSuccess: '注册成功',
    termsPrefix: '我已阅读并同意', userAgreement: '「用户服务协议」', and: '和', privacy: '「隐私政策」',
    submitLogin: '登 录', submitRegister: '注 册', submitReset: '重置密码', other: '其他方式', wechat: '微信', oneTap: '一键登录',
    footer: '登录即表示您同意我们的服务条款与隐私政策', scenicAlt: '灵山胜境', thirdPartyDeveloping: '第三方登录开发中',
  },
  home: {
    scenic: '灵山胜境', subtitle: 'AI智慧导览', aiGuide: 'AI导游', routePlan: '路线规划', videos: '景区视频', map: '景区地图',
    spots: '景区景点', spotCount: '共{count}处', notice: '景区公告', noticeText: '九龙灌浴表演时间：10:00 / 11:30 / 14:00 / 16:00，请提前10分钟到达观赏位置',
    mapDeveloping: '景区地图入口开发中', notifications: '消息通知',
  },
  chat: {
    title: '小灵 · AI导游', online: '在线', offline: '离线', enableAvatar: '启用数字人', disableAvatar: '关闭数字人', newChat: '新对话',
    hello: '您好，我是小灵', intro: '您的灵山胜境 AI 导游，随时为您讲解景点、推荐路线、解答疑问', assistant: '小灵', references: '参考资料（{count}）',
    scenicSource: '景区资料', page: '第{page}页', fragment: '片段 {start}-{end}', dataTime: '数据时间 {time}', degraded: '当前回答已降级：{reason}',
    partialUnavailable: '部分服务暂不可用', noEvidence: '未找到可核验证据，已按保守策略拒答。', avatarSpeak: '数字人播报', stopAvatar: '停止播报', stop: '停止', voice: '语音', copy: '复制', routeRecommend: '路线推荐',
    input: '输入您的问题...', inputHint: '按 Enter 发送 · 支持语音输入', avatarAuto: '· 数字人将自动讲解', avatarEnabled: '已启用 3D 数字人',
    avatarDisabled: '已关闭 3D 数字人', ttsFailed: '语音播报失败', copied: '已复制', noVoice: '未检测到语音', listening: '正在聆听...（再次点击结束）',
    microphoneDenied: '无法访问麦克风，请检查权限', asrFailed: '语音识别失败：{message}', timeout: '处理超时，请稍后重试。', unavailable: '服务暂时不可用，请稍后重试。', aiError: 'AI 服务暂时不可用，请稍后重试。', aiConnectionError: 'AI 服务连接失败，请稍后重试。', aiTimeout: 'AI 处理超时，请稍后重试。', aiGenerationFailed: 'AI 暂时无法生成回答，请稍后重试。',
    wsFailed: 'WebSocket 连接失败，请确认后端服务已启动', quick1: '灵山大佛有多高？', quick2: '梵宫有什么特色？', quick3: '九龙灌浴表演时间是？', quick4: '推荐一条游览路线', quick5: '灵山的历史文化', replayAvatar: '让数字人重新播报', pauseVoice: '暂停', resumeVoice: '继续',
  },
  avatar: {
    wakeHint: '点击下方按钮唤醒 AI 数字人', wake: '唤醒数字人', loading: '资源加载中 {progress}%', waking: '正在唤醒数字人...', speaking: '讲解中', stop: '停止', replay: '重播',
    idle: '待命中 · 随时为您讲解', disconnected: '未连接', readConfig: '读取角色配置', connected: '已连接', connectFailed: '连接失败', sdkMissing: '星云 SDK 未加载，请刷新页面',
    unavailable: '当前数字人角色尚未完成服务器配置', defaultRole: '灵境讲解员', wakingRole: '正在唤醒{name}', ready: '{name}已就绪', failed: '数字人连接失败：{message}', network: '请检查网络', happy: '😊 开心', neutral: '😐 平静', concerned: '😟 关切',
  },
  routePage: {
    title: '个性化路线推荐', aiPlan: 'AI 智能规划', aiDesc: '根据您的偏好定制专属路线', interests: '兴趣偏好', duration: '游览时长', halfDay: '半天', fullDay: '全天',
    planning: 'AI 规划中...', plan: 'AI 智能规划', replan: '重新规划', savedRoutes: '已保存路线', count: '{count} 条', loadingSaved: '正在加载已保存路线...', reload: '重新加载',
    loadingSteps: ['分析兴趣偏好…', '匹配景点…', '优化游览顺序…', '生成路线建议…'],
    emptySaved: '生成满意的路线后，可保存到当前账号长期查看', presets: '预设经典路线', all: '全部', showOnMap: '在地图上查看路线', snapshotExpired: '路线快照已失效，请在对话页重新提出路线规划需求。',
    aiRecommended: 'AI 推荐路线', aboutDuration: '约{duration}', planFailed: '路线规划失败，请重新尝试', savedLoadFailed: '已保存路线加载失败', saved: '路线已保存', saveFailed: '路线保存失败',
    deleteConfirm: '确定删除“{title}”吗？', deleteTitle: '删除已保存路线', deleted: '路线已删除', deleteFailed: '路线删除失败', buddhism: '佛教文化', nature: '自然风光', history: '历史古迹',
    family: '亲子游乐', architecture: '建筑艺术', food: '美食素斋',
  },
  routeCard: {
    saved: '已保存', recommended: '小灵推荐', stations: '路线站点', tips: '小灵提示', evidence: '路线依据（{count}）', scenicSource: '景区资料', dataTime: '数据时间：{time}', trace: '追踪号：{id}',
    viewMap: '在地图查看', saving: '保存中', save: '保存路线', deleting: '删除中', delete: '删除路线',
  },
  map: {
    weatherLoading: '天气加载中…', humidity: '湿度 {value}%', wind: '{direction}风{power}级', refresh: '刷新', scenicMap: '灵山胜境景区地图', mapLoading: '地图加载中...', clickLoad: '点击加载地图',
    weatherConditions: { '00': '晴', '01': '多云', '02': '阴', '03': '阵雨', '04': '雷阵雨', '05': '雷阵雨伴有冰雹', '06': '雨夹雪', '07': '小雨', '08': '中雨', '09': '大雨', '10': '暴雨', '11': '大暴雨', '12': '特大暴雨', '13': '阵雪', '14': '小雪', '15': '中雪', '16': '大雪', '17': '暴雪', '18': '雾', '19': '冻雨', '20': '沙尘暴', '21': '小到中雨', '22': '中到大雨', '23': '大到暴雨', '24': '暴雨到大暴雨', '25': '大暴雨到特大暴雨', '26': '小到中雪', '27': '中到大雪', '28': '大到暴雪', '29': '浮尘', '30': '扬沙', '31': '强沙尘暴', '53': '霾' },
    windDirections: { '0': '无', '1': '北', '2': '东北', '3': '东', '4': '东南', '5': '南', '6': '西南', '7': '西', '8': '西北', '9': '北', '10': '东北', '11': '东', '12': '东南', '13': '南', '14': '西南', '15': '西', '16': '西北' },
    locate: '定位', route: '路线', panorama: '全景', weatherFailed: '天气获取失败', weatherUnavailable: '天气服务暂不可用', today: '今天', tomorrow: '明天', afterTomorrow: '后天',
    noIntro: '暂无介绍', details: '查看详情 →', routeLabel: '游览路线', notEnough: '匹配到的景点不足，无法规划路线', spotsNotEnough: '景点不足，无法规划路线', planning: '规划步行路线中…',
    unmatched: '{label}：存在未匹配景点，无法形成连续路线', noSegment: '{label}：没有可规划的有效路段', success: '{label}：步行路线已生成（{stations} 站 / {segments} 段）{suffix}',
    partial: '{label}：{success}/{total} 段规划成功，{fallback} 段以虚线显示{suffix}', failed: '{label}：步行规划失败，各段以虚线显示{suffix}', unmatchedSuffix: '，{count} 个景点未匹配',
    filter: '筛选', filterTitle: '选择显示的景点', selectAll: '全选', selectNone: '全不选', popularOnly: '仅热门', applyFilter: '应用', cancelFilter: '取消', hiddenCount: '已隐藏 {count} 个景点',
    gpsNoPermission: 'GPS权限被拒绝，已显示景区中心', gpsError: 'GPS定位失败，已显示景区中心',
    nearbySpot: '您已到达{name}附近', nearbySpotDesc: '点击听取景点讲解',
    guide: '听讲解', dismiss: '忽略',
    customPin: '标记', pinModeHint: '点击地图添加自定义标记', pinName: '标记名称', pinNamePlaceholder: '给这个位置起个名字…', pinSave: '保存', pinCancel: '取消', pinDeleteTip: '右键标记可删除',
    pauseRoute: '暂停', resumeRoute: '继续', stopRoute: '停止',
  },
  spotDetail: {
    notFound: '景点不存在', notFoundDesc: '景点「{name}」暂未收录或已被移除', home: '返回首页', duration: '游览时长', distance: '距入口', bestSeason: '最佳季节', intro: '景点介绍',
    highlights: '核心亮点', info: '实用信息', hours: '开放时间', ticket: '门票信息', tips: '游览贴士', nearby: '周边景点', aiGuide: 'AI讲解', navigate: '导航前往', navigationDeveloping: '地图导航功能开发中',
    guideQuestion: '请给我讲解一下{name}',
  },
  favorite: { add: '收藏', added: '已收藏', addSuccess: '收藏成功', removeSuccess: '已取消收藏' },
  video: { title: '景区视频', hint: '点击跳转抖音播放' },
  profile: {
    title: '个人中心', defaultName: '游客用户', subtitle: '灵山胜境 · 智慧导览', editName: '编辑昵称', nickname: '昵称', nicknamePlaceholder: '请输入昵称', save: '保存', saved: '资料已更新', saveFailed: '资料更新失败',
    visitsStat: '游览次数', favoritesStat: '我的收藏', routesStat: '收藏路线', conversationsStat: '对话次数', quick: '快捷功能', ticket: '门票价格', parking: '停车导航', vegetarian: '素斋介绍', emergency: '紧急求助',
    visits: '游览记录', visitsDesc: '查看历史游览景点', favorites: '我的收藏', favoritesDesc: '收藏的景点与路线', notifications: '消息通知', notificationsDesc: '景区公告与提醒',
    voice: '语音设置', voiceDesc: '导游音色、语速与音量', language: '语言切换', languageDesc: '中文 / English', offline: '离线地图', offlineDesc: '下载景区离线地图',
    privacy: '隐私政策', about: '关于灵境导游', feedback: '意见反馈', logout: '退出登录', system: 'AI智慧导览系统', developing: '{name}开发中',
  },
  visits: { title: '游览记录', empty: '暂无游览记录', hint: '快去探索景区吧', visitedAt: '游览时间：{time}', loadFailed: '游览记录加载失败' },
  favorites: { title: '我的收藏', empty: '暂无收藏内容', hint: '遇到喜欢的景点就收藏吧', routeUnavailable: '该路线详情暂不可用', loadFailed: '收藏加载失败' },
  notifications: { title: '消息通知', empty: '暂无新消息', hint: '景区公告会在这里显示', markRead: '标为已读', loadFailed: '消息加载失败', connected: '实时消息已连接', disconnected: '实时消息重连中' },
  voice: {
    title: '语音设置', type: '导游音色', rate: '语速', volume: '音量', savedHint: '设置会自动保存并用于普通语音播报',
    voices: { xiaoyan: '温柔女声', xiaoyu: '知性女声', xiaomei: '稳重男声', xiaofeng: '亲切男声' }, rates: { slow: '慢速', normal: '正常', fast: '快速' },
  },
  language: { title: '语言切换', zhCN: '简体中文', en: '英语', ja: '日语', ko: '韩语', changed: '语言已切换' },
  feedback: { title: '意见反馈', category: '反馈分类', categories: { suggestion: '意见建议', complaint: '问题投诉', consultation: '咨询', praise: '表扬', other: '其他' }, placeholder: '请描述您遇到的问题或建议...', submit: '提交反馈', required: '请输入反馈内容', success: '感谢您的反馈！', history: '历史反馈', empty: '暂无历史反馈', pending: '处理中', replied: '已回复', reply: '回复：{reply}', loadFailed: '反馈历史加载失败' },
  tickets: { title: '门票价格', adult: '成人票', adultPrice: '¥210 起', concession: '优惠票', concessionPrice: '¥105 起', free: '免票人群', freeDesc: '符合景区政策的儿童及其他优待人群', note: '票价与优惠政策可能调整，请以景区购票页面和现场公示为准。', buy: '购票服务开发中' },
  vegetarian: { title: '素斋介绍', intro: '灵山素食融合江南风味与佛教饮食文化，适合游览途中清淡用餐。', places: '推荐地点', place1: '灵山蔬食馆', place1Desc: '提供素面、素点心与套餐。', place2: '梵宫餐厅', place2Desc: '以景区当日开放及现场菜单为准。', note: '预约功能开发中，请到店咨询营业时间与余位。' },
  privacy: { title: '隐私政策', policy: '灵境导游隐私政策', updated: '更新日期：2026 年 6 月 21 日', collectTitle: '一、信息收集', collectIntro: '我们仅收集必要的服务信息，包括：', collect1: '账号注册信息（手机号、昵称）', collect2: '游览记录数据（访问的景点、路线）', collect3: '设备信息（用于优化服务体验）', useTitle: '二、信息使用', useIntro: '收集的信息仅用于：', use1: '提供个性化导览服务', use2: '优化 AI 推荐算法', use3: '改进产品功能', protectTitle: '三、信息保护', protect: '我们采用行业标准的安全措施保护您的个人信息，不会将您的信息出售或共享给第三方。', contactTitle: '四、联系我们', contact: '如有隐私相关问题，请联系：privacy@lingguide.com' },
  about: { title: '关于灵境导游', subtitle: 'LINGGUIDE · AI 智慧导览系统', product: '产品介绍', intro: '灵境导游是一款具备多模态交互能力的 AI 数字人导游应用，为游客提供实时智能问答、个性化路线讲解、情感互动服务。', features: '核心功能', f1: 'AI 数字人实时对话', f2: '3D 数字人形象', f3: '个性化路线推荐', f4: '景区景点语音讲解', f5: '抖音官方视频集成', demo: '示范景区', demoText: '无锡灵山胜境（佛教文化主题 5A 级景区）', contact: '联系我们', email: '邮箱：contact@lingguide.com' },
}

const en = {
  ...zhCN,
  common: { back: 'Back', loading: 'Loading...', retry: 'Retry', developing: 'Coming soon', operationFailed: 'Operation failed', loginExpired: 'Your session has expired. Please sign in again.', spot: 'Attraction', route: 'Route', submit: 'Submit', cancel: 'Cancel', delete: 'Delete' },
  tab: { home: 'Explore', chat: 'Chat', route: 'Routes', profile: 'Me' },
  auth: { brand: 'LingGuide', subtitle: 'AI guide · Lingshan Scenic Area', login: 'Sign in', register: 'Register', phone: 'Phone number', code: 'Verification code', getCode: 'Get code', resend: 'Resend', password: 'Password', setPassword: 'Set password (6–20 characters)', confirmPassword: 'Confirm password', passwordMismatch: 'Passwords do not match', forgot: 'Forgot password?', reset: 'Reset password', newPassword: 'New password (6–20 characters)', resetSuccess: 'Password reset. Please sign in.', codeSent: 'Code sent', codeDev: 'Code: {code} (development mode)', codeFailed: 'Failed to get code', requestFailed: 'Request failed', loginSuccess: 'Signed in', registerSuccess: 'Registered', termsPrefix: 'I have read and agree to', userAgreement: 'Terms of Service', and: 'and', privacy: 'Privacy Policy', submitLogin: 'SIGN IN', submitRegister: 'REGISTER', submitReset: 'RESET PASSWORD', other: 'Other options', wechat: 'WeChat', oneTap: 'One-tap login', footer: 'By signing in, you agree to our Terms and Privacy Policy', scenicAlt: 'Lingshan Scenic Area', thirdPartyDeveloping: 'Third-party sign-in is coming soon' },
  home: { scenic: 'Lingshan Scenic Area', subtitle: 'AI smart guide', aiGuide: 'AI Guide', routePlan: 'Plan Route', videos: 'Videos', map: 'Scenic Map', spots: 'Attractions', spotCount: '{count} places', notice: 'Notice', noticeText: 'Nine Dragons Bathing showtimes: 10:00 / 11:30 / 14:00 / 16:00. Please arrive 10 minutes early.', mapDeveloping: 'Scenic map entry is coming soon', notifications: 'Notifications' },
  chat: { ...zhCN.chat, title: 'Xiaoling · AI Guide', online: 'Online', offline: 'Offline', enableAvatar: 'Enable avatar', disableAvatar: 'Disable avatar', newChat: 'New chat', hello: "Hello, I'm Xiaoling", intro: 'Your AI guide for attractions, routes, and travel questions at Lingshan.', assistant: 'Xiaoling', references: 'Sources ({count})', scenicSource: 'Scenic source', page: 'Page {page}', fragment: 'Excerpt {start}-{end}', dataTime: 'Data date {time}', degraded: 'Limited answer: {reason}', partialUnavailable: 'Some services are unavailable', noEvidence: 'No verifiable evidence was found, so a conservative response was used.', avatarSpeak: 'Avatar voice', stopAvatar: 'Stop avatar', stop: 'Stop', voice: 'Voice', copy: 'Copy', routeRecommend: 'Route', replayAvatar: 'Replay with avatar', input: 'Ask a question...', inputHint: 'Press Enter to send · Voice input supported', avatarAuto: '· Avatar will explain automatically', avatarEnabled: '3D avatar enabled', avatarDisabled: '3D avatar disabled', ttsFailed: 'Voice playback failed', copied: 'Copied', noVoice: 'No speech detected', listening: 'Listening... Tap again to finish', microphoneDenied: 'Microphone access unavailable. Check permissions.', asrFailed: 'Speech recognition failed: {message}', timeout: 'Request timed out. Please try again.', unavailable: 'Service is temporarily unavailable.', aiError: 'The AI service is temporarily unavailable. Please try again.', aiConnectionError: 'Could not connect to the AI service. Please try again.', aiTimeout: 'The AI request timed out. Please try again.', aiGenerationFailed: 'The AI could not generate a response. Please try again.', wsFailed: 'WebSocket connection failed. Check the server.', quick1: 'How tall is the Lingshan Grand Buddha?', quick2: 'What is special about Brahma Palace?', quick3: 'When is the Nine Dragons Bathing show?', quick4: 'Recommend a sightseeing route', quick5: 'History and culture of Lingshan' },
  spotDetail: { notFound: 'Attraction not found', notFoundDesc: '“{name}” is not available or has been removed.', home: 'Back to Home', duration: 'Visit time', distance: 'From entrance', bestSeason: 'Best season', intro: 'Introduction', highlights: 'Highlights', info: 'Practical info', hours: 'Opening hours', ticket: 'Tickets', tips: 'Visitor tips', nearby: 'Nearby attractions', aiGuide: 'AI Guide', navigate: 'Navigate', navigationDeveloping: 'Navigation is coming soon', guideQuestion: 'Please introduce {name}' },
  favorite: { add: 'Favorite', added: 'Favorited', addSuccess: 'Added to favorites', removeSuccess: 'Removed from favorites' },
  video: { title: 'Scenic Videos', hint: 'Open in Douyin' },
  profile: { ...zhCN.profile, title: 'Profile', defaultName: 'Visitor', subtitle: 'Lingshan · Smart guide', editName: 'Edit nickname', nickname: 'Nickname', nicknamePlaceholder: 'Enter a nickname', save: 'Save', saved: 'Profile updated', saveFailed: 'Failed to update profile', visitsStat: 'Visits', favoritesStat: 'Favorites', routesStat: 'Saved routes', conversationsStat: 'Chats', quick: 'Quick services', ticket: 'Ticket prices', parking: 'Parking', vegetarian: 'Vegetarian dining', emergency: 'Emergency help', visits: 'Visit history', visitsDesc: 'View visited attractions', favorites: 'Favorites', favoritesDesc: 'Saved attractions and routes', notifications: 'Notifications', notificationsDesc: 'Notices and reminders', voice: 'Voice settings', voiceDesc: 'Voice, speed, and volume', language: 'Language', languageDesc: 'English / 中文', offline: 'Offline map', offlineDesc: 'Download the scenic map', privacy: 'Privacy Policy', about: 'About LingGuide', feedback: 'Feedback', logout: 'Sign out', system: 'AI smart guide system', developing: '{name} is coming soon' },
  visits: { title: 'Visit History', empty: 'No visit history', hint: 'Explore an attraction to get started', visitedAt: 'Visited: {time}', loadFailed: 'Failed to load visit history' },
  favorites: { title: 'Favorites', empty: 'No favorites yet', hint: 'Save attractions you like', routeUnavailable: 'Route details are not available yet', loadFailed: 'Failed to load favorites' },
  notifications: { title: 'Notifications', empty: 'No notifications', hint: 'Scenic notices will appear here', markRead: 'Mark read', loadFailed: 'Failed to load notifications', connected: 'Live updates connected', disconnected: 'Reconnecting live updates' },
  voice: { title: 'Voice Settings', type: 'Guide voice', rate: 'Speed', volume: 'Volume', savedHint: 'Settings are saved automatically and used for regular voice playback', voices: { xiaoyan: 'Gentle Female Voice', xiaoyu: 'Sophisticated Female Voice', xiaomei: 'Calm Male Voice', xiaofeng: 'Friendly Male Voice' }, rates: { slow: 'Slow', normal: 'Normal', fast: 'Fast' } },
  language: { title: 'Language', zhCN: 'Simplified Chinese', en: 'English', ja: 'Japanese', ko: 'Korean', changed: 'Language changed' },
  feedback: { title: 'Feedback', category: 'Category', categories: { suggestion: 'Suggestion', complaint: 'Complaint', consultation: 'Question', praise: 'Praise', other: 'Other' }, placeholder: 'Describe your issue or suggestion...', submit: 'Submit feedback', required: 'Enter feedback first', success: 'Thank you for your feedback!', history: 'Feedback history', empty: 'No previous feedback', pending: 'In progress', replied: 'Replied', reply: 'Reply: {reply}', loadFailed: 'Failed to load feedback history' },
  tickets: { title: 'Ticket Prices', adult: 'Adult', adultPrice: 'From ¥210', concession: 'Discount ticket', concessionPrice: 'From ¥105', free: 'Free admission', freeDesc: 'Eligible children and other visitors covered by scenic-area policies', note: 'Prices and discounts may change. Check the official booking page or on-site notice.', buy: 'Ticket booking is coming soon' },
  vegetarian: { title: 'Vegetarian Dining', intro: 'Lingshan vegetarian food blends Jiangnan flavors with Buddhist culinary culture.', places: 'Recommended venues', place1: 'Lingshan Vegetarian Restaurant', place1Desc: 'Vegetarian noodles, snacks, and set meals.', place2: 'Brahma Palace Restaurant', place2Desc: 'Subject to daily opening and the on-site menu.', note: 'Reservations are coming soon. Ask the venue for hours and availability.' },
  avatar: { wakeHint: 'Click below to wake the AI avatar', wake: 'Wake avatar', loading: 'Loading assets {progress}%', waking: 'Waking avatar...', speaking: 'Explaining', stop: 'Stop', idle: 'Standing by · Ready to explain', disconnected: 'Disconnected', readConfig: 'Loading character', connected: 'Connected', connectFailed: 'Connection failed', sdkMissing: 'Xmov SDK is not loaded. Refresh the page.', unavailable: 'The avatar is not configured on the server', defaultRole: 'LingGuide Presenter', wakingRole: 'Waking {name}', ready: '{name} is ready', failed: 'Avatar connection failed: {message}', network: 'Check your network', happy: '😊 Happy', neutral: '😐 Calm', concerned: '😟 Concerned' },
  routePage: { title: 'Personalized Routes', aiPlan: 'AI Route Planning', aiDesc: 'Create a route based on your preferences', interests: 'Interests', duration: 'Visit duration', halfDay: 'Half day', fullDay: 'Full day', planning: 'Planning...', plan: 'Plan with AI', replan: 'Plan again', savedRoutes: 'Saved routes', count: '{count} routes', loadingSaved: 'Loading saved routes...', reload: 'Reload', loadingSteps: ['Analyzing your interests…', 'Matching attractions…', 'Optimizing visit order…', 'Generating route suggestions…'], emptySaved: 'Save a route to view it from this account later', presets: 'Classic routes', all: 'All', showOnMap: 'View route on map', snapshotExpired: 'This route snapshot has expired. Ask for a new route in Chat.', aiRecommended: 'AI recommended route', aboutDuration: 'About {duration}', planFailed: 'Route planning failed. Try again.', savedLoadFailed: 'Failed to load saved routes', saved: 'Route saved', saveFailed: 'Failed to save route', deleteConfirm: 'Delete “{title}”?', deleteTitle: 'Delete saved route', deleted: 'Route deleted', deleteFailed: 'Failed to delete route', buddhism: 'Buddhist culture', nature: 'Nature', history: 'History', family: 'Family fun', architecture: 'Architecture', food: 'Vegetarian food' },
  routeCard: { saved: 'Saved', recommended: 'Xiaoling recommends', stations: 'Route stops', tips: 'Xiaoling tip', evidence: 'Route sources ({count})', scenicSource: 'Scenic source', dataTime: 'Data date: {time}', trace: 'Trace: {id}', viewMap: 'View on map', saving: 'Saving', save: 'Save route', deleting: 'Deleting', delete: 'Delete route' },
  map: { weatherLoading: 'Loading weather…', humidity: 'Humidity {value}%', wind: '{direction} wind {power}', refresh: 'Refresh', scenicMap: 'Lingshan Scenic Area map', mapLoading: 'Loading map...', clickLoad: 'Click to load map', weatherConditions: { '00': 'Clear', '01': 'Cloudy', '02': 'Overcast', '03': 'Showers', '04': 'Thundershowers', '05': 'Hailstorm', '06': 'Sleet', '07': 'Light rain', '08': 'Moderate rain', '09': 'Heavy rain', '10': 'Storm', '11': 'Heavy storm', '12': 'Torrential rain', '13': 'Snow showers', '14': 'Light snow', '15': 'Moderate snow', '16': 'Heavy snow', '17': 'Blizzard', '18': 'Fog', '19': 'Freezing rain', '20': 'Dust storm', '21': 'Light to moderate rain', '22': 'Moderate to heavy rain', '23': 'Heavy rain to storm', '24': 'Storm to heavy storm', '25': 'Heavy to torrential rain', '26': 'Light to moderate snow', '27': 'Moderate to heavy snow', '28': 'Heavy snow to blizzard', '29': 'Dust', '30': 'Sand', '31': 'Strong sandstorm', '53': 'Haze' }, windDirections: { '0': 'Calm', '1': 'N', '2': 'NE', '3': 'E', '4': 'SE', '5': 'S', '6': 'SW', '7': 'W', '8': 'NW', '9': 'N', '10': 'NE', '11': 'E', '12': 'SE', '13': 'S', '14': 'SW', '15': 'W', '16': 'NW' }, locate: 'Locate', route: 'Route', panorama: 'Overview', weatherFailed: 'Failed to get weather', weatherUnavailable: 'Weather service unavailable', today: 'Today', tomorrow: 'Tomorrow', afterTomorrow: 'Day after tomorrow', noIntro: 'No introduction', details: 'View details →', routeLabel: 'Sightseeing route', notEnough: 'Not enough matched attractions for a route', spotsNotEnough: 'Not enough attractions for a route', planning: 'Planning walking route…', unmatched: '{label}: unmatched attractions prevent a continuous route', noSegment: '{label}: no valid segments to plan', success: '{label}: walking route ready ({stations} stops / {segments} segments){suffix}', partial: '{label}: {success}/{total} segments planned, {fallback} shown as dashed lines{suffix}', failed: '{label}: walking plan failed; segments are shown as dashed lines{suffix}', unmatchedSuffix: ', {count} attractions unmatched', filter: 'Filter', filterTitle: 'Select spots to display', selectAll: 'Select all', selectNone: 'Deselect all', popularOnly: 'Popular only', applyFilter: 'Apply', cancelFilter: 'Cancel', hiddenCount: '{count} attractions hidden',
    gpsNoPermission: 'GPS permission denied; showing scenic area center', gpsError: 'GPS unavailable; showing scenic area center',
    nearbySpot: 'You are near {name}', nearbySpotDesc: 'Tap to hear the guide',
    guide: 'Guide', dismiss: 'Dismiss',
    customPin: 'Pin', pinModeHint: 'Tap the map to add a custom pin', pinName: 'Pin name', pinNamePlaceholder: 'Name this location…', pinSave: 'Save', pinCancel: 'Cancel', pinDeleteTip: 'Right-click to delete',
    pauseRoute: 'Pause', resumeRoute: 'Resume', stopRoute: 'Stop' },
  privacy: { title: 'Privacy Policy', policy: 'LingGuide Privacy Policy', updated: 'Updated: June 21, 2026', collectTitle: '1. Information collected', collectIntro: 'We collect only information needed to provide the service:', collect1: 'Account information (phone number and nickname)', collect2: 'Visit history (attractions and routes)', collect3: 'Device information to improve the experience', useTitle: '2. How information is used', useIntro: 'Collected information is used only to:', use1: 'Provide personalized guide services', use2: 'Improve AI recommendations', use3: 'Improve product features', protectTitle: '3. Information protection', protect: 'We use industry-standard safeguards and do not sell or share your personal information with third parties.', contactTitle: '4. Contact us', contact: 'Privacy questions: privacy@lingguide.com' },
  about: { title: 'About LingGuide', subtitle: 'LINGGUIDE · AI smart guide system', product: 'Product', intro: 'LingGuide is a multimodal AI avatar guide offering real-time answers, personalized routes, and emotional interaction for visitors.', features: 'Features', f1: 'Real-time AI avatar chat', f2: '3D avatar', f3: 'Personalized route recommendations', f4: 'Audio guides for attractions', f5: 'Official Douyin videos', demo: 'Demo destination', demoText: 'Wuxi Lingshan Scenic Area (Buddhist culture 5A attraction)', contact: 'Contact', email: 'Email: contact@lingguide.com' },
}

const ja = {
  common: {
    back: '戻る', loading: '読み込み中...', retry: '再試行', developing: '開発中', operationFailed: '操作に失敗しました',
    loginExpired: 'ログインの有効期限が切れました。再度ログインしてください', spot: 'スポット', route: 'ルート', submit: '送信', cancel: 'キャンセル', delete: '削除',
  },
  tab: { home: '観光案内', chat: 'チャット', route: 'ルート', profile: 'マイページ' },
  auth: {
    brand: 'LingGuide', subtitle: 'AIスマートガイド · 霊山勝境', login: 'ログイン', register: '新規登録', phone: '電話番号を入力',
    code: '認証コード', getCode: 'コードを取得', resend: '再取得', password: 'パスワードを入力', setPassword: 'パスワードを設定（6～20文字）',
    confirmPassword: 'パスワードを確認', passwordMismatch: 'パスワードが一致しません', forgot: 'パスワードをお忘れですか？', reset: 'パスワードを再設定',
    newPassword: '新しいパスワードを入力（6～20文字）', resetSuccess: 'パスワードを再設定しました。ログインしてください', codeSent: '認証コードを送信しました', codeDev: '認証コード：{code}（開発モードで表示）',
    codeFailed: '認証コードを取得できませんでした', requestFailed: 'リクエストに失敗しました', loginSuccess: 'ログインしました', registerSuccess: '登録が完了しました',
    termsPrefix: '以下を読み、同意します：', userAgreement: '「利用規約」', and: 'および', privacy: '「プライバシーポリシー」',
    submitLogin: 'ログイン', submitRegister: '新規登録', submitReset: 'パスワードを再設定', other: 'その他の方法', wechat: 'WeChat', oneTap: 'ワンタップログイン',
    footer: 'ログインすると、利用規約とプライバシーポリシーに同意したものとみなされます', scenicAlt: '霊山勝境', thirdPartyDeveloping: '外部サービスでのログインは開発中です',
  },
  home: {
    scenic: '霊山勝境', subtitle: 'AIスマートガイド', aiGuide: 'AIガイド', routePlan: 'ルート計画', videos: '観光動画', map: '園内マップ',
    spots: '観光スポット', spotCount: '全{count}か所', notice: '園内からのお知らせ', noticeText: '九龍灌浴の上演時間：10:00 / 11:30 / 14:00 / 16:00。観覧場所には10分前までにお越しください',
    mapDeveloping: '園内マップへの入口は開発中です', notifications: 'お知らせ',
  },
  chat: {
    title: '小霊 · AIガイド', online: 'オンライン', offline: 'オフライン', enableAvatar: 'デジタルヒューマンを有効にする', disableAvatar: 'デジタルヒューマンを無効にする', newChat: '新しい会話',
    hello: 'こんにちは、小霊です', intro: '霊山勝境のAIガイドとして、スポットの解説やルートの提案、ご質問への回答をいつでも承ります', assistant: '小霊', references: '参考資料（{count}件）',
    scenicSource: '観光地資料', page: '{page}ページ', fragment: '抜粋 {start}～{end}', dataTime: 'データ日時：{time}', degraded: '現在の回答は制限されています：{reason}',
    partialUnavailable: '一部のサービスを現在ご利用いただけません', noEvidence: '確認可能な根拠が見つからなかったため、慎重な方針に基づき回答を控えました', avatarSpeak: 'デジタルヒューマンで読み上げ', stopAvatar: 'デジタルヒューマンを停止', stop: '停止', voice: '音声', copy: 'コピー', routeRecommend: 'ルート提案',
    input: '質問を入力してください...', inputHint: 'Enterで送信 · 音声入力にも対応', avatarAuto: '· デジタルヒューマンが自動で解説します', avatarEnabled: '3Dデジタルヒューマンを有効にしました',
    avatarDisabled: '3Dデジタルヒューマンを無効にしました', ttsFailed: '音声を再生できませんでした', copied: 'コピーしました', noVoice: '音声を検出できませんでした', listening: '音声を認識中...（もう一度押すと終了）',
    microphoneDenied: 'マイクにアクセスできません。権限を確認してください', asrFailed: '音声認識に失敗しました：{message}', timeout: '処理がタイムアウトしました。しばらくしてから再試行してください', unavailable: 'サービスを一時的にご利用いただけません。しばらくしてから再試行してください', aiError: 'AIサービスを一時的に利用できません。しばらくしてから再試行してください', aiConnectionError: 'AIサービスに接続できません。しばらくしてから再試行してください', aiTimeout: 'AI処理がタイムアウトしました。しばらくしてから再試行してください', aiGenerationFailed: 'AIが回答を生成できませんでした。しばらくしてから再試行してください',
    wsFailed: 'WebSocketに接続できません。バックエンドサービスが起動しているか確認してください', quick1: '霊山大仏の高さは？', quick2: '梵宮の見どころは？', quick3: '九龍灌浴の上演時間は？', quick4: 'おすすめの観光ルートを教えて', quick5: '霊山の歴史と文化', replayAvatar: 'デジタルヒューマンでもう一度再生',
  },
  avatar: {
    wakeHint: '下のボタンを押してAIデジタルヒューマンを起動', wake: 'デジタルヒューマンを起動', loading: 'リソースを読み込み中 {progress}%', waking: 'デジタルヒューマンを起動中...', speaking: '解説中', stop: '停止',
    idle: '待機中 · いつでも解説できます', disconnected: '未接続', readConfig: 'キャラクター設定を読み込み中', connected: '接続済み', connectFailed: '接続に失敗しました', sdkMissing: 'Xmov SDKが読み込まれていません。ページを再読み込みしてください',
    unavailable: 'このデジタルヒューマンはサーバーでまだ設定されていません', defaultRole: 'LingGuide案内役', wakingRole: '{name}を起動中', ready: '{name}の準備ができました', failed: 'デジタルヒューマンへの接続に失敗しました：{message}', network: 'ネットワークを確認してください', happy: '😊 楽しい', neutral: '😐 穏やか', concerned: '😟 心配',
  },
  routePage: {
    title: 'おすすめのパーソナルルート', aiPlan: 'AIスマートプラン', aiDesc: 'お好みに合わせた専用ルートを作成します', interests: '興味・関心', duration: '観光時間', halfDay: '半日', fullDay: '1日',
    planning: 'AIが計画中...', plan: 'AIで計画', replan: 'もう一度計画', savedRoutes: '保存したルート', count: '{count}件', loadingSaved: '保存したルートを読み込み中...', reload: '再読み込み',
    loadingSteps: ['興味・関心を分析中…', 'スポットを照合中…', '観光順序を最適化中…', 'ルート案を作成中…'],
    emptySaved: '気に入ったルートを保存すると、このアカウントでいつでも確認できます', presets: '定番ルート', all: 'すべて', showOnMap: '地図でルートを確認', snapshotExpired: 'ルート情報の有効期限が切れました。チャット画面でもう一度ルート計画を依頼してください',
    aiRecommended: 'AIおすすめルート', aboutDuration: '約{duration}', planFailed: 'ルートを作成できませんでした。もう一度お試しください', savedLoadFailed: '保存したルートを読み込めませんでした', saved: 'ルートを保存しました', saveFailed: 'ルートを保存できませんでした',
    deleteConfirm: '「{title}」を削除しますか？', deleteTitle: '保存したルートを削除', deleted: 'ルートを削除しました', deleteFailed: 'ルートを削除できませんでした', buddhism: '仏教文化', nature: '自然景観', history: '歴史遺産',
    family: '家族で楽しむ', architecture: '建築芸術', food: '精進料理',
  },
  routeCard: {
    saved: '保存済み', recommended: '小霊のおすすめ', stations: 'ルートの立ち寄り地点', tips: '小霊からのヒント', evidence: 'ルートの根拠（{count}件）', scenicSource: '観光地資料', dataTime: 'データ日時：{time}', trace: '追跡番号：{id}',
    viewMap: '地図で見る', saving: '保存中', save: 'ルートを保存', deleting: '削除中', delete: 'ルートを削除',
  },
  map: {
    weatherLoading: '天気を読み込み中…', humidity: '湿度 {value}%', wind: '{direction}の風・風力{power}', refresh: '更新', scenicMap: '霊山勝境 園内マップ', mapLoading: '地図を読み込み中...', clickLoad: 'クリックして地図を読み込む', weatherConditions: { '00': '晴れ', '01': '曇り', '02': '曇天', '03': 'にわか雨', '04': '雷雨', '05': 'ひょうを伴う雷雨', '06': 'みぞれ', '07': '弱い雨', '08': '雨', '09': '強い雨', '10': '暴雨', '11': '大雨', '12': '豪雨', '13': 'にわか雪', '14': '小雪', '15': '雪', '16': '大雪', '17': '吹雪', '18': '霧', '19': '凍雨', '20': '砂嵐', '21': '弱い雨', '22': '雨', '23': '大雨', '24': '暴雨', '25': '豪雨', '26': '弱い雪', '27': '雪', '28': '大雪', '29': 'ほこり', '30': '砂じん', '31': '強い砂嵐', '53': '煙霧' }, windDirections: { '0': '無風', '1': '北', '2': '北東', '3': '東', '4': '南東', '5': '南', '6': '南西', '7': '西', '8': '北西', '9': '北', '10': '北東', '11': '東', '12': '南東', '13': '南', '14': '南西', '15': '西', '16': '北西' },
    locate: '現在地', route: 'ルート', panorama: '全景', weatherFailed: '天気情報を取得できませんでした', weatherUnavailable: '天気サービスを一時的にご利用いただけません', today: '今日', tomorrow: '明日', afterTomorrow: '明後日',
    noIntro: '紹介はまだありません', details: '詳細を見る →', routeLabel: '観光ルート', notEnough: '一致するスポットが足りないため、ルートを作成できません', spotsNotEnough: 'スポットが足りないため、ルートを作成できません', planning: '徒歩ルートを計画中…',
    unmatched: '{label}：一致しないスポットがあるため、連続したルートを作成できません', noSegment: '{label}：計画可能な有効区間がありません', success: '{label}：徒歩ルートを作成しました（{stations}地点 / {segments}区間）{suffix}',
    partial: '{label}：{total}区間中{success}区間を作成し、残り{fallback}区間を破線で表示します{suffix}', failed: '{label}：徒歩ルートを作成できなかったため、各区間を破線で表示します{suffix}', unmatchedSuffix: '、{count}か所のスポットが一致しません',
    filter: 'フィルター', filterTitle: '表示するスポットを選択', selectAll: '全選択', selectNone: '全解除', popularOnly: '人気のみ', applyFilter: '適用', cancelFilter: 'キャンセル', hiddenCount: '{count}件のスポットを非表示中',
    gpsNoPermission: 'GPS権限が拒否されました。観光地の中心を表示しています', gpsError: 'GPS利用不可。観光地の中心を表示しています',
    nearbySpot: '{name}の近くにいます', nearbySpotDesc: 'タップして解説を聴く',
    guide: '解説を聴く', dismiss: '閉じる',
    customPin: 'ピン', pinModeHint: '地図をタップしてピンを追加', pinName: 'ピンの名前', pinNamePlaceholder: 'この場所に名前をつけて…', pinSave: '保存', pinCancel: 'キャンセル', pinDeleteTip: '右クリックで削除',
    pauseRoute: '一時停止', resumeRoute: '再開', stopRoute: '停止',
  },
  spotDetail: {
    notFound: 'スポットが見つかりません', notFoundDesc: 'スポット「{name}」は未登録または削除されています', home: 'ホームへ戻る', duration: '所要時間', distance: '入口からの距離', bestSeason: 'おすすめの季節', intro: 'スポット紹介',
    highlights: '主な見どころ', info: 'お役立ち情報', hours: '営業時間', ticket: 'チケット情報', tips: '観光のヒント', nearby: '周辺スポット', aiGuide: 'AI解説', navigate: 'ナビを開始', navigationDeveloping: '地図ナビ機能は開発中です',
    guideQuestion: '{name}について説明してください',
  },
  favorite: { add: 'お気に入りに追加', added: 'お気に入り登録済み', addSuccess: 'お気に入りに追加しました', removeSuccess: 'お気に入りから削除しました' },
  video: { title: '観光動画', hint: 'タップするとDouyinで再生します' },
  profile: {
    title: 'マイページ', defaultName: 'ゲスト', subtitle: '霊山勝境 · スマートガイド', editName: 'ニックネームを編集', nickname: 'ニックネーム', nicknamePlaceholder: 'ニックネームを入力', save: '保存', saved: 'プロフィールを更新しました', saveFailed: 'プロフィールを更新できませんでした',
    visitsStat: '訪問回数', favoritesStat: 'お気に入り', routesStat: '保存ルート', conversationsStat: '会話回数', quick: 'クイックメニュー', ticket: 'チケット料金', parking: '駐車場案内', vegetarian: '精進料理', emergency: '緊急連絡',
    visits: '訪問履歴', visitsDesc: '過去に訪れたスポットを確認', favorites: 'お気に入り', favoritesDesc: '保存したスポットとルート', notifications: 'お知らせ', notificationsDesc: '園内のお知らせとご案内',
    voice: '音声設定', voiceDesc: 'ガイド音声・速度・音量', language: '言語を変更', languageDesc: '日本語 / 中文 / English / 한국어', offline: 'オフラインマップ', offlineDesc: '園内のオフラインマップをダウンロード',
    privacy: 'プライバシーポリシー', about: 'LingGuideについて', feedback: 'ご意見・ご要望', logout: 'ログアウト', system: 'AIスマートガイドシステム', developing: '{name}は開発中です',
  },
  visits: { title: '訪問履歴', empty: '訪問履歴はありません', hint: '観光スポットを巡ってみましょう', visitedAt: '訪問日時：{time}', loadFailed: '訪問履歴を読み込めませんでした' },
  favorites: { title: 'お気に入り', empty: 'お気に入りはありません', hint: '気になるスポットをお気に入りに追加しましょう', routeUnavailable: 'このルートの詳細は現在ご利用いただけません', loadFailed: 'お気に入りを読み込めませんでした' },
  notifications: { title: 'お知らせ', empty: '新しいお知らせはありません', hint: '園内からのお知らせがここに表示されます', markRead: '既読にする', loadFailed: 'お知らせを読み込めませんでした', connected: 'リアルタイム通知に接続しました', disconnected: 'リアルタイム通知に再接続中です' },
  voice: {
    title: '音声設定', type: 'ガイド音声', rate: '速度', volume: '音量', savedHint: '設定は自動保存され、通常の音声再生に使用されます',
    voices: { xiaoyan: '優しい女性の声', xiaoyu: '知的な女性の声', xiaomei: '落ち着いた男性の声', xiaofeng: '親しみやすい男性の声' }, rates: { slow: '遅い', normal: '標準', fast: '速い' },
  },
  language: { title: '言語を変更', zhCN: '簡体字中国語', en: '英語', ja: '日本語', ko: '韓国語', changed: '言語を変更しました' },
  feedback: { title: 'ご意見・ご要望', category: 'カテゴリー', categories: { suggestion: 'ご提案', complaint: '問題の報告', consultation: 'お問い合わせ', praise: 'お褒めの言葉', other: 'その他' }, placeholder: 'お気づきの点やご要望をご記入ください...', submit: '送信', required: '内容を入力してください', success: 'ご意見をお寄せいただきありがとうございます！', history: '送信履歴', empty: '送信履歴はありません', pending: '対応中', replied: '回答済み', reply: '回答：{reply}', loadFailed: '送信履歴を読み込めませんでした' },
  tickets: { title: 'チケット料金', adult: '大人券', adultPrice: '¥210～', concession: '割引券', concessionPrice: '¥105～', free: '無料対象者', freeDesc: '園内規定の条件を満たすお子様およびその他の優待対象者', note: '料金や割引制度は変更される場合があります。公式購入ページまたは現地の案内をご確認ください', buy: 'チケット購入サービスは開発中です' },
  vegetarian: { title: '精進料理のご案内', intro: '霊山の精進料理は、江南地方の味わいと仏教の食文化を融合し、観光の合間の軽いお食事におすすめです', places: 'おすすめ店舗', place1: '霊山精進料理店', place1Desc: '精進麺、精進点心、セットメニューをご用意しています', place2: '梵宮レストラン', place2Desc: '当日の営業状況および店頭メニューをご確認ください', note: '予約機能は開発中です。営業時間と空席状況は店舗でご確認ください' },
  privacy: {
    title: 'プライバシーポリシー', policy: 'LingGuideプライバシーポリシー', updated: '更新日：2026年6月21日', collectTitle: '1. 情報の収集', collectIntro: 'サービスに必要な以下の情報のみを収集します：',
    collect1: 'アカウント登録情報（電話番号、ニックネーム）', collect2: '訪問履歴データ（訪れたスポット、ルート）', collect3: '端末情報（サービス体験の改善に使用）', useTitle: '2. 情報の利用', useIntro: '収集した情報は、以下の目的にのみ使用します：',
    use1: 'パーソナライズされた観光案内の提供', use2: 'AIおすすめ機能の改善', use3: '製品機能の改善', protectTitle: '3. 情報の保護', protect: '業界標準のセキュリティ対策で個人情報を保護し、お客様の情報を第三者に販売または共有することはありません',
    contactTitle: '4. お問い合わせ', contact: 'プライバシーに関するお問い合わせ：privacy@lingguide.com',
  },
  about: {
    title: 'LingGuideについて', subtitle: 'LINGGUIDE · AIスマートガイドシステム', product: '製品紹介', intro: 'LingGuideは、マルチモーダルな対話に対応したAIデジタルヒューマン観光ガイドです。リアルタイムの質問応答、パーソナライズされたルート解説、感情豊かな対話を提供します',
    features: '主な機能', f1: 'AIデジタルヒューマンとのリアルタイム会話', f2: '3Dデジタルヒューマン', f3: 'パーソナルルートの提案', f4: '観光スポットの音声解説', f5: 'Douyin公式動画との連携', demo: 'モデル観光地',
    demoText: '無錫・霊山勝境（仏教文化をテーマとする中国国家5A級観光地）', contact: 'お問い合わせ', email: 'メール：contact@lingguide.com',
  },
}

const ko = {
  common: {
    back: '뒤로', loading: '불러오는 중...', retry: '다시 시도', developing: '개발 중', operationFailed: '작업에 실패했습니다',
    loginExpired: '로그인이 만료되었습니다. 다시 로그인해 주세요', spot: '명소', route: '경로', submit: '제출', cancel: '취소', delete: '삭제',
  },
  tab: { home: '관광 안내', chat: '대화', route: '경로', profile: '내 정보' },
  auth: {
    brand: 'LingGuide', subtitle: 'AI 스마트 가이드 · 링산 관광지', login: '로그인', register: '회원가입', phone: '휴대폰 번호를 입력하세요',
    code: '인증번호', getCode: '인증번호 받기', resend: '다시 받기', password: '비밀번호를 입력하세요', setPassword: '비밀번호 설정(6~20자)',
    confirmPassword: '비밀번호 확인', passwordMismatch: '비밀번호가 일치하지 않습니다', forgot: '비밀번호를 잊으셨나요?', reset: '비밀번호 재설정',
    newPassword: '새 비밀번호를 입력하세요(6~20자)', resetSuccess: '비밀번호가 재설정되었습니다. 로그인해 주세요', codeSent: '인증번호를 보냈습니다', codeDev: '인증번호: {code}(개발 모드에서 표시)',
    codeFailed: '인증번호를 받지 못했습니다', requestFailed: '요청에 실패했습니다', loginSuccess: '로그인되었습니다', registerSuccess: '회원가입이 완료되었습니다',
    termsPrefix: '다음을 읽고 동의합니다:', userAgreement: '「이용약관」', and: '및', privacy: '「개인정보 처리방침」',
    submitLogin: '로그인', submitRegister: '회원가입', submitReset: '비밀번호 재설정', other: '다른 방법', wechat: 'WeChat', oneTap: '간편 로그인',
    footer: '로그인하면 이용약관과 개인정보 처리방침에 동의한 것으로 간주됩니다', scenicAlt: '링산 관광지', thirdPartyDeveloping: '외부 서비스 로그인 기능은 개발 중입니다',
  },
  home: {
    scenic: '링산 관광지', subtitle: 'AI 스마트 가이드', aiGuide: 'AI 가이드', routePlan: '경로 계획', videos: '관광 영상', map: '관광 지도',
    spots: '관광 명소', spotCount: '총 {count}곳', notice: '관광지 공지', noticeText: '구룡관욕 공연 시간: 10:00 / 11:30 / 14:00 / 16:00. 관람 장소에 10분 일찍 도착해 주세요',
    mapDeveloping: '관광 지도 기능은 개발 중입니다', notifications: '알림',
  },
  chat: {
    title: '샤오링 · AI 가이드', online: '온라인', offline: '오프라인', enableAvatar: '디지털 휴먼 켜기', disableAvatar: '디지털 휴먼 끄기', newChat: '새 대화',
    hello: '안녕하세요, 샤오링입니다', intro: '링산 관광지의 AI 가이드로서 명소 해설, 경로 추천, 여행 관련 질문에 언제든 답해 드립니다', assistant: '샤오링', references: '참고 자료({count})',
    scenicSource: '관광지 자료', page: '{page}페이지', fragment: '발췌 {start}~{end}', dataTime: '데이터 시각 {time}', degraded: '현재 답변이 제한되었습니다: {reason}',
    partialUnavailable: '일부 서비스를 현재 이용할 수 없습니다', noEvidence: '확인 가능한 근거를 찾지 못해 신중한 정책에 따라 답변을 드리지 않았습니다', avatarSpeak: '디지털 휴먼 음성 해설', stopAvatar: '디지털 휴먼 정지', stop: '중지', voice: '음성', copy: '복사', routeRecommend: '경로 추천',
    input: '질문을 입력하세요...', inputHint: 'Enter 키로 전송 · 음성 입력 지원', avatarAuto: '· 디지털 휴먼이 자동으로 설명합니다', avatarEnabled: '3D 디지털 휴먼을 켰습니다',
    avatarDisabled: '3D 디지털 휴먼을 껐습니다', ttsFailed: '음성을 재생하지 못했습니다', copied: '복사했습니다', noVoice: '음성이 감지되지 않았습니다', listening: '듣는 중... (다시 누르면 종료)',
    microphoneDenied: '마이크에 접근할 수 없습니다. 권한을 확인해 주세요', asrFailed: '음성 인식에 실패했습니다: {message}', timeout: '처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요', unavailable: '서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도해 주세요', aiError: 'AI 서비스를 일시적으로 이용할 수 없습니다. 다시 시도해 주세요', aiConnectionError: 'AI 서비스에 연결할 수 없습니다. 다시 시도해 주세요', aiTimeout: 'AI 처리 시간이 초과되었습니다. 다시 시도해 주세요', aiGenerationFailed: 'AI가 답변을 생성하지 못했습니다. 다시 시도해 주세요',
    wsFailed: 'WebSocket 연결에 실패했습니다. 백엔드 서비스가 실행 중인지 확인해 주세요', quick1: '링산 대불의 높이는 얼마인가요?', quick2: '범궁의 특징은 무엇인가요?', quick3: '구룡관욕 공연 시간은 언제인가요?', quick4: '관광 경로를 추천해 주세요', quick5: '링산의 역사와 문화', replayAvatar: '디지털 휴먼으로 다시 재생',
  },
  avatar: {
    wakeHint: '아래 버튼을 눌러 AI 디지털 휴먼을 깨우세요', wake: '디지털 휴먼 깨우기', loading: '리소스 불러오는 중 {progress}%', waking: '디지털 휴먼을 깨우는 중...', speaking: '해설 중', stop: '중지',
    idle: '대기 중 · 언제든 해설해 드립니다', disconnected: '연결 안 됨', readConfig: '캐릭터 설정 불러오기', connected: '연결됨', connectFailed: '연결 실패', sdkMissing: 'Xmov SDK가 로드되지 않았습니다. 페이지를 새로고침해 주세요',
    unavailable: '현재 디지털 휴먼 캐릭터가 서버에 설정되지 않았습니다', defaultRole: 'LingGuide 해설사', wakingRole: '{name} 깨우는 중', ready: '{name} 준비 완료', failed: '디지털 휴먼 연결에 실패했습니다: {message}', network: '네트워크를 확인해 주세요', happy: '😊 행복', neutral: '😐 차분함', concerned: '😟 걱정',
  },
  routePage: {
    title: '맞춤 경로 추천', aiPlan: 'AI 스마트 계획', aiDesc: '취향에 맞는 전용 경로를 만들어 드립니다', interests: '관심사', duration: '관람 시간', halfDay: '반나절', fullDay: '하루',
    planning: 'AI가 계획 중...', plan: 'AI로 계획', replan: '다시 계획', savedRoutes: '저장한 경로', count: '{count}개', loadingSaved: '저장한 경로 불러오는 중...', reload: '다시 불러오기',
    loadingSteps: ['관심사 분석 중…', '명소 매칭 중…', '관람 순서 최적화 중…', '경로 제안 생성 중…'],
    emptySaved: '마음에 드는 경로를 저장하면 현재 계정에서 언제든 확인할 수 있습니다', presets: '대표 추천 경로', all: '전체', showOnMap: '지도에서 경로 보기', snapshotExpired: '경로 정보가 만료되었습니다. 대화 화면에서 경로 계획을 다시 요청해 주세요',
    aiRecommended: 'AI 추천 경로', aboutDuration: '약 {duration}', planFailed: '경로 계획에 실패했습니다. 다시 시도해 주세요', savedLoadFailed: '저장한 경로를 불러오지 못했습니다', saved: '경로를 저장했습니다', saveFailed: '경로를 저장하지 못했습니다',
    deleteConfirm: '“{title}” 경로를 삭제하시겠습니까?', deleteTitle: '저장한 경로 삭제', deleted: '경로를 삭제했습니다', deleteFailed: '경로를 삭제하지 못했습니다', buddhism: '불교 문화', nature: '자연 경관', history: '역사 유적',
    family: '가족 여행', architecture: '건축 예술', food: '채식 요리',
  },
  routeCard: {
    saved: '저장됨', recommended: '샤오링 추천', stations: '경로 지점', tips: '샤오링의 안내', evidence: '경로 근거({count})', scenicSource: '관광지 자료', dataTime: '데이터 시각: {time}', trace: '추적 번호: {id}',
    viewMap: '지도에서 보기', saving: '저장 중', save: '경로 저장', deleting: '삭제 중', delete: '경로 삭제',
  },
  map: {
    weatherLoading: '날씨 불러오는 중…', humidity: '습도 {value}%', wind: '{direction}풍 {power}급', refresh: '새로고침', scenicMap: '링산 관광지 지도', mapLoading: '지도 불러오는 중...', clickLoad: '눌러서 지도 불러오기', weatherConditions: { '00': '맑음', '01': '구름 조금', '02': '흐림', '03': '소나기', '04': '천둥번개', '05': '우박 동반 뇌우', '06': '진눈깨비', '07': '약한 비', '08': '비', '09': '강한 비', '10': '폭우', '11': '매우 강한 비', '12': '집중호우', '13': '눈보라', '14': '약한 눈', '15': '눈', '16': '강한 눈', '17': '폭설', '18': '안개', '19': '어는 비', '20': '황사 폭풍', '21': '약한 비', '22': '비', '23': '강한 비', '24': '폭우', '25': '집중호우', '26': '약한 눈', '27': '눈', '28': '폭설', '29': '먼지', '30': '모래바람', '31': '강한 모래바람', '53': '연무' }, windDirections: { '0': '무풍', '1': '북', '2': '북동', '3': '동', '4': '남동', '5': '남', '6': '남서', '7': '서', '8': '북서', '9': '북', '10': '북동', '11': '동', '12': '남동', '13': '남', '14': '남서', '15': '서', '16': '북서' },
    locate: '현재 위치', route: '경로', panorama: '전경', weatherFailed: '날씨를 불러오지 못했습니다', weatherUnavailable: '날씨 서비스를 일시적으로 이용할 수 없습니다', today: '오늘', tomorrow: '내일', afterTomorrow: '모레',
    noIntro: '소개가 없습니다', details: '상세 보기 →', routeLabel: '관광 경로', notEnough: '일치하는 명소가 부족하여 경로를 계획할 수 없습니다', spotsNotEnough: '명소가 부족하여 경로를 계획할 수 없습니다', planning: '도보 경로 계획 중…',
    unmatched: '{label}: 일치하지 않는 명소가 있어 연속된 경로를 만들 수 없습니다', noSegment: '{label}: 계획할 수 있는 유효 구간이 없습니다', success: '{label}: 도보 경로가 생성되었습니다({stations}개 지점 / {segments}개 구간){suffix}',
    partial: '{label}: {total}개 구간 중 {success}개 계획 완료, 나머지 {fallback}개는 점선으로 표시됩니다{suffix}', failed: '{label}: 도보 경로 계획에 실패하여 각 구간을 점선으로 표시합니다{suffix}', unmatchedSuffix: ', {count}개 명소가 일치하지 않습니다',
    filter: '필터', filterTitle: '표시할 명소 선택', selectAll: '전체 선택', selectNone: '전체 해제', popularOnly: '인기만', applyFilter: '적용', cancelFilter: '취소', hiddenCount: '{count}개 명소 숨김',
    gpsNoPermission: 'GPS 권한이 거부되었습니다. 관광지 중심을 표시합니다', gpsError: 'GPS를 사용할 수 없습니다. 관광지 중심을 표시합니다',
    nearbySpot: '{name} 근처에 있습니다', nearbySpotDesc: '탭하여 해설 듣기',
    guide: '해설 듣기', dismiss: '닫기',
    customPin: '핀', pinModeHint: '지도를 탭하여 커스텀 핀 추가', pinName: '핀 이름', pinNamePlaceholder: '이 위치에 이름을 붙여보세요…', pinSave: '저장', pinCancel: '취소', pinDeleteTip: '우클릭으로 삭제',
    pauseRoute: '일시정지', resumeRoute: '재개', stopRoute: '정지',
  },
  spotDetail: {
    notFound: '명소를 찾을 수 없습니다', notFoundDesc: '명소 “{name}”이(가) 등록되지 않았거나 삭제되었습니다', home: '홈으로', duration: '관람 시간', distance: '입구에서의 거리', bestSeason: '추천 계절', intro: '명소 소개',
    highlights: '주요 볼거리', info: '이용 정보', hours: '운영 시간', ticket: '입장권 정보', tips: '관람 팁', nearby: '주변 명소', aiGuide: 'AI 해설', navigate: '길 안내 시작', navigationDeveloping: '지도 길 안내 기능은 개발 중입니다',
    guideQuestion: '{name}에 대해 설명해 주세요',
  },
  favorite: { add: '즐겨찾기', added: '즐겨찾기 완료', addSuccess: '즐겨찾기에 추가했습니다', removeSuccess: '즐겨찾기에서 삭제했습니다' },
  video: { title: '관광 영상', hint: '누르면 Douyin에서 재생됩니다' },
  profile: {
    title: '내 정보', defaultName: '방문객', subtitle: '링산 관광지 · 스마트 가이드', editName: '닉네임 수정', nickname: '닉네임', nicknamePlaceholder: '닉네임을 입력하세요', save: '저장', saved: '프로필을 업데이트했습니다', saveFailed: '프로필을 업데이트하지 못했습니다',
    visitsStat: '방문 횟수', favoritesStat: '즐겨찾기', routesStat: '저장한 경로', conversationsStat: '대화 횟수', quick: '빠른 메뉴', ticket: '입장권 가격', parking: '주차장 안내', vegetarian: '채식 요리', emergency: '긴급 도움',
    visits: '방문 기록', visitsDesc: '방문했던 명소 보기', favorites: '즐겨찾기', favoritesDesc: '저장한 명소와 경로', notifications: '알림', notificationsDesc: '관광지 공지 및 안내',
    voice: '음성 설정', voiceDesc: '가이드 음색, 속도 및 볼륨', language: '언어 변경', languageDesc: '한국어 / 中文 / English / 日本語', offline: '오프라인 지도', offlineDesc: '관광지 오프라인 지도 다운로드',
    privacy: '개인정보 처리방침', about: 'LingGuide 소개', feedback: '의견 보내기', logout: '로그아웃', system: 'AI 스마트 가이드 시스템', developing: '{name} 기능은 개발 중입니다',
  },
  visits: { title: '방문 기록', empty: '방문 기록이 없습니다', hint: '관광 명소를 둘러보세요', visitedAt: '방문 시간: {time}', loadFailed: '방문 기록을 불러오지 못했습니다' },
  favorites: { title: '즐겨찾기', empty: '즐겨찾기가 없습니다', hint: '마음에 드는 명소를 즐겨찾기에 추가해 보세요', routeUnavailable: '이 경로의 상세 정보를 현재 이용할 수 없습니다', loadFailed: '즐겨찾기를 불러오지 못했습니다' },
  notifications: { title: '알림', empty: '새 알림이 없습니다', hint: '관광지 공지가 여기에 표시됩니다', markRead: '읽음으로 표시', loadFailed: '알림을 불러오지 못했습니다', connected: '실시간 알림이 연결되었습니다', disconnected: '실시간 알림에 다시 연결하는 중입니다' },
  voice: {
    title: '음성 설정', type: '가이드 음색', rate: '속도', volume: '볼륨', savedHint: '설정은 자동으로 저장되며 일반 음성 재생에 적용됩니다',
    voices: { xiaoyan: '부드러운 여성 음성', xiaoyu: '지적인 여성 음성', xiaomei: '차분한 남성 음성', xiaofeng: '친근한 남성 음성' }, rates: { slow: '느리게', normal: '보통', fast: '빠르게' },
  },
  language: { title: '언어 변경', zhCN: '중국어 간체', en: '영어', ja: '일본어', ko: '한국어', changed: '언어를 변경했습니다' },
  feedback: { title: '의견 보내기', category: '의견 유형', categories: { suggestion: '제안', complaint: '문제 신고', consultation: '문의', praise: '칭찬', other: '기타' }, placeholder: '문제나 제안 사항을 입력해 주세요...', submit: '의견 제출', required: '의견 내용을 입력해 주세요', success: '소중한 의견을 보내 주셔서 감사합니다!', history: '의견 내역', empty: '이전 의견이 없습니다', pending: '처리 중', replied: '답변 완료', reply: '답변: {reply}', loadFailed: '의견 내역을 불러오지 못했습니다' },
  tickets: { title: '입장권 가격', adult: '성인권', adultPrice: '¥210부터', concession: '할인권', concessionPrice: '¥105부터', free: '무료 입장 대상', freeDesc: '관광지 정책에 따라 무료입장 조건을 충족하는 어린이 및 기타 우대 대상자', note: '가격 및 할인 정책은 변경될 수 있습니다. 공식 예매 페이지나 현장 안내를 확인해 주세요', buy: '입장권 예매 서비스는 개발 중입니다' },
  vegetarian: { title: '채식 요리 소개', intro: '링산 채식은 장난 지역의 풍미와 불교 음식 문화를 결합한 담백한 요리로, 관광 중 가볍게 식사하기 좋습니다', places: '추천 장소', place1: '링산 채식관', place1Desc: '채식 면 요리, 채식 간식 및 세트 메뉴를 제공합니다', place2: '범궁 레스토랑', place2Desc: '당일 운영 여부와 현장 메뉴를 확인해 주세요', note: '예약 기능은 개발 중입니다. 운영 시간과 잔여 좌석은 매장에 문의해 주세요' },
  privacy: {
    title: '개인정보 처리방침', policy: 'LingGuide 개인정보 처리방침', updated: '업데이트 날짜: 2026년 6월 21일', collectTitle: '1. 정보 수집', collectIntro: '서비스에 필요한 다음 정보만 수집합니다:',
    collect1: '계정 등록 정보(휴대폰 번호, 닉네임)', collect2: '방문 기록 데이터(방문한 명소, 경로)', collect3: '기기 정보(서비스 경험 개선에 사용)', useTitle: '2. 정보 이용', useIntro: '수집한 정보는 다음 목적으로만 사용됩니다:',
    use1: '맞춤형 관광 안내 서비스 제공', use2: 'AI 추천 알고리즘 개선', use3: '제품 기능 개선', protectTitle: '3. 정보 보호', protect: '개인정보 보호를 위해 업계 표준 보안 조치를 적용하며, 이용자의 정보를 제3자에게 판매하거나 공유하지 않습니다',
    contactTitle: '4. 문의', contact: '개인정보 관련 문의: privacy@lingguide.com',
  },
  about: {
    title: 'LingGuide 소개', subtitle: 'LINGGUIDE · AI 스마트 가이드 시스템', product: '제품 소개', intro: 'LingGuide는 멀티모달 상호작용을 지원하는 AI 디지털 휴먼 관광 가이드 앱으로, 방문객에게 실시간 지능형 질의응답, 맞춤형 경로 해설, 감성 상호작용 서비스를 제공합니다',
    features: '주요 기능', f1: 'AI 디지털 휴먼 실시간 대화', f2: '3D 디지털 휴먼', f3: '맞춤형 경로 추천', f4: '관광 명소 음성 해설', f5: 'Douyin 공식 영상 연동', demo: '시범 관광지',
    demoText: '우시 링산 관광지(불교 문화를 주제로 한 중국 국가 5A급 관광지)', contact: '문의', email: '이메일: contact@lingguide.com',
  },
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en, ja, ko },
})

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
  localStorage.setItem(LOCALE_KEY, locale)
  document.documentElement.lang = locale
}

document.documentElement.lang = i18n.global.locale.value
