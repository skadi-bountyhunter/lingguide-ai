/**
 * 灵境导游 — 导览页 + 详情页 组件
 * 
 * 包含：HomePage、SpotDetailPage、TabBar 组件及所需数据常量
 * 依赖：React、Tailwind CSS v4（配合 index.css 主题变量）
 * 
 * 使用示例：
 * ```tsx
 * import { HomePage, SpotDetailPage, TabBar, SCENIC_SPOTS } from "./GuidePages";
 * 
 * function App() {
 *   const [page, setPage] = useState<"home" | "chat" | "route" | "profile">("home");
 *   const [selectedSpot, setSelectedSpot] = useState<typeof SCENIC_SPOTS[number] | null>(null);
 * 
 *   if (selectedSpot) {
 *     return (
 *       <SpotDetailPage
 *         spot={selectedSpot}
 *         onBack={() => setSelectedSpot(null)}
 *         onAiGuide={() => { / * 跳转对话页 * / }}
 *       />
 *     );
 *   }
 * 
 *   return (
 *     <>
 *       <HomePage onNavigate={setPage} onSelectSpot={setSelectedSpot} />
 *       <TabBar active={page} onChange={setPage} />
 *     </>
 *   );
 * }
 * ```
 */

import { useState, useRef, useEffect } from "react";

/* ═══ TYPE ═══ */
type Page = "home" | "chat" | "route" | "profile";

/* ═══ DATA ═══ */
const SCENIC_SPOTS = [
  {
    name: "灵山大佛", icon: "🗿", image: "/images/lingshan_3.jpeg",
    desc: "通高88米的世界最高露天青铜释迦牟尼立像，右手施无畏印，左手施与愿印，庄严震撼",
    tags: ["佛教文化", "建筑艺术"], duration: "1.5h", distance: "0.8km",
    fullDesc: "灵山大佛坐落于无锡马山秦履峰南侧，通高88米，其中佛体79米，莲花瓣9米，是迄今为止世界上最高的露天青铜释迦牟尼立像。大佛右手指天施「无畏印」，寓意众生无所畏惧；左手指地施「与愿印」，寓意心想事成。整座大佛采用锡青铜材料铸造，总用铜量达700吨，由1560块铜壁板拼接而成，每块铜壁板均经精密计算与打磨，确保大佛表面光滑如镜。\n\n大佛所在的小灵山，因唐玄奘西天取经归来见此山形酷似印度灵鹫山而得名。站在大佛脚下仰望，那份庄严与震撼令人肃然起敬；登临大佛基座远眺，太湖烟波浩渺，尽收眼底。",
    highlights: ["88米世界最高青铜立像", "700吨锡青铜铸造", "无畏印与与愿印", "登基座远眺太湖"],
    hours: "7:30 - 17:30（夏季）/ 7:30 - 17:00（冬季）",
    ticket: "含在灵山胜境门票内（210元/人）",
    tips: ["建议顺时针绕佛三圈祈福", "登基座需另购抱佛脚票（30元）", "大佛脚下可免费领取平安符", "日落时分光影效果最佳"],
    bestSeason: "四季皆宜，秋季天高气爽最佳",
    nearby: ["梵宫", "九龙灌浴", "降魔浮雕"],
  },
  {
    name: "梵宫", icon: "✨", image: "/images/lingshan_1.jpeg",
    desc: "被誉为「东方卢浮宫」的佛教艺术殿堂，穹顶壁画超千平方米，琉璃墙面光彩夺目",
    tags: ["建筑艺术", "佛教文化"], duration: "1h", distance: "0.5km",
    fullDesc: "灵山梵宫是一座集佛教文化、建筑艺术于一体的大型佛教艺术殿堂，总建筑面积达7万平方米，被誉为「东方卢浮宫」。梵宫整体建筑采用唐代风格，融合了中国传统木构建筑与佛教石窟艺术精髓，气势恢宏而不失典雅。\n\n步入梵宫，首先映入眼帘的是高达30余米的穹顶壁画，面积超过千平方米，描绘佛教经典故事，色彩斑斓、气势磅礴。琉璃墙面是世界最大的琉璃作品，超过2000平方米，光彩夺目。大型油画融合东西方艺术精髓，宝相阁珍藏各类佛教艺术珍品，每一处细节都令人叹为观止。",
    highlights: ["千平方米穹顶壁画", "世界最大琉璃墙面", "大型东西方融合油画", "宝相阁佛教珍品"],
    hours: "7:30 - 17:00（梵宫圣境演出：10:00 / 14:00）",
    ticket: "含在灵山胜境门票内",
    tips: ["梵宫内部禁止拍照摄像", "建议跟随免费讲解员参观", "圣境演出需提前30分钟入场", "穿鞋套入内（现场提供）"],
    bestSeason: "室内景点，四季皆宜",
    nearby: ["灵山大佛", "五印坛城", "菩提大道"],
  },
  {
    name: "九龙灌浴", icon: "🐉", image: "/images/lingshan_5.jpeg",
    desc: "大型音乐动态群雕表演，莲花开启时九龙喷水，伴随悠扬佛乐，场面蔚为壮观",
    tags: ["佛教文化", "亲子游乐"], duration: "0.5h", distance: "0.3km",
    fullDesc: "九龙灌浴是灵山胜境最具代表性的动态景观，根据佛教典籍中释迦牟尼诞生时九龙喷水沐浴的传说而建。大型音乐动态群雕由莲花、九龙和太子佛像组成，莲花直径达9米，六瓣莲花在音乐声中缓缓开启，金身太子佛像从中升起，九龙同时喷出高达数米的水柱，伴随悠扬佛乐，场面蔚为壮观。\n\n表演全程约6分钟，莲花开启前有佛经诵读，开启瞬间九龙齐喷水，水雾弥漫如临仙境。莲花闭合后，周围水池中的水被视为圣水，游客可用手触摸祈福。",
    highlights: ["9米直径巨型莲花", "九龙齐喷水柱", "金身太子佛像", "圣水祈福体验"],
    hours: "每日四场：10:00 / 11:30 / 14:00 / 16:00",
    ticket: "含在灵山胜境门票内",
    tips: ["提前10分钟到达正面观赏位", "表演约6分钟，请耐心等待", "可接圣水祈福（自备容器）", "带小朋友建议站前排"],
    bestSeason: "春夏季节水景最美",
    nearby: ["灵山大佛", "降魔浮雕", "菩提大道"],
  },
  {
    name: "五印坛城", icon: "🏛️", image: "/images/lingshan_4.jpeg",
    desc: "藏传佛教文化体验圣地，融合汉藏建筑风格，内部供奉各类佛教艺术珍品",
    tags: ["建筑艺术", "历史古迹"], duration: "0.5h", distance: "0.4km",
    fullDesc: "五印坛城是灵山胜境中独具特色的藏传佛教文化体验圣地，整座建筑仿照藏族传统坛城形制建造，融合汉藏建筑风格，外观金碧辉煌、庄严华美。坛城共六层，总高度达31.8米，建筑面积约5000平方米。\n\n内部供奉各类藏传佛教艺术珍品，包括精美的唐卡、酥油花、坛城沙画等。每层设有不同的主题展示区，从藏传佛教的历史渊源到艺术传承，层层递进。顶层可俯瞰灵山胜境全景，远眺太湖风光。五印坛城不仅是宗教圣地，更是汉藏文化交融的生动见证。",
    highlights: ["31.8米藏式坛城建筑", "唐卡与酥油花艺术", "坛城沙画展示", "顶层俯瞰灵山全景"],
    hours: "7:30 - 17:00",
    ticket: "含在灵山胜境门票内",
    tips: ["可体验转经筒祈福", "内部有藏文化互动体验", "顶层观景台视野极佳", "尊重藏传佛教礼仪"],
    bestSeason: "四季皆宜，冬季雪景别有韵味",
    nearby: ["梵宫", "灵山大佛", "菩提大道"],
  },
  {
    name: "降魔浮雕", icon: "🛕", image: "/images/lingshan_7.jpeg",
    desc: "大型浮雕群讲述释迦牟尼降魔成道故事，雕刻精美，感悟佛法智慧",
    tags: ["佛教文化", "历史古迹"], duration: "0.3h", distance: "0.2km",
    fullDesc: "降魔浮雕位于灵山大佛基座北侧，是一组大型浮雕群，生动讲述了释迦牟尼在菩提树下降魔成道的佛教故事。浮雕全长约30米，高约8米，采用传统石雕工艺，人物造型生动传神，场景气势恢宏。\n\n浮雕以释迦牟尼端坐菩提树下禅定为画面中心，周围环绕着魔王波旬率领的魔军，或怒目圆睁、或张牙舞爪，与佛祖的安详从容形成鲜明对比。最终魔军溃散，佛祖悟道成佛。整组浮雕不仅是一件精美的艺术品，更蕴含着「以静制动、以善克恶」的深刻佛理。",
    highlights: ["30米大型石雕群", "降魔成道故事", "传统石雕工艺", "佛理感悟"],
    hours: "7:30 - 17:30（户外，全天可观赏）",
    ticket: "含在灵山胜境门票内",
    tips: ["建议结合大佛参观一并游览", "浮雕旁有解说牌可自助阅读", "清晨光线适合拍照", "可静坐感悟禅意"],
    bestSeason: "四季皆宜，清晨光影最佳",
    nearby: ["灵山大佛", "九龙灌浴", "菩提大道"],
  },
  {
    name: "菩提大道", icon: "🌿", image: "/images/lingshan_6.jpeg",
    desc: "漫步菩提树下，感受禅意与宁静，沿途可欣赏太湖风光与园林景观",
    tags: ["自然风光", "美食素斋"], duration: "0.5h", distance: "0.6km",
    fullDesc: "菩提大道是灵山胜境中最具禅意的漫步步道，全长约800米，两侧菩提树成荫，四季景色各异。大道以释迦牟尼在菩提树下悟道为文化主题，沿途设有禅意小品、石刻经文和休憩亭台，一步一景，处处体现东方禅学美学。\n\n漫步其间，可远眺太湖烟波，近赏园林景观。春日菩提新绿，夏日浓荫蔽日，秋日金叶满地，冬日枝影婆娑。大道中段设有素食体验区，可品尝灵山特色素斋，在禅意中感受味蕾的清净。大道尽头连接杏坛广场，是休憩与感悟的绝佳场所。",
    highlights: ["800米菩提树荫步道", "禅意小品与石刻经文", "太湖远眺观景", "灵山特色素斋体验"],
    hours: "全天开放",
    ticket: "含在灵山胜境门票内",
    tips: ["素斋需提前预约（11:30前到达）", "建议穿舒适步行鞋", "沿途有休憩亭台可小坐", "秋末金叶铺地最为浪漫"],
    bestSeason: "秋季（10-11月）金叶最美",
    nearby: ["梵宫", "五印坛城", "九龙灌浴"],
  },
];

const CAROUSEL_ITEMS = [
  { image: "/images/lingshan_3.jpeg", title: "灵山大佛", subtitle: "88米世界最高青铜立像" },
  { image: "/images/lingshan_1.jpeg", title: "灵山梵宫", subtitle: "东方卢浮宫 · 佛教艺术殿堂" },
  { image: "/images/lingshan_5.jpeg", title: "九龙灌浴", subtitle: "大型音乐动态群雕表演" },
  { image: "/images/lingshan_7.jpeg", title: "五印坛城", subtitle: "藏传佛教文化圣地" },
];

/* ═══ TAB BAR ═══ */
function TabBar({ active, onChange }: { active: Page; onChange: (p: Page) => void }) {
  const tabs: { key: Page; label: string; icon: (a: boolean) => React.ReactNode }[] = [
    {
      key: "home",
      label: "导览",
      icon: (a) => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill={a ? "#2D6A4F" : "none"} stroke={a ? "#2D6A4F" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      ),
    },
    {
      key: "chat",
      label: "对话",
      icon: (a) => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill={a ? "#2D6A4F" : "none"} stroke={a ? "#2D6A4F" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      key: "route",
      label: "路线",
      icon: (a) => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={a ? "#2D6A4F" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
          <line x1="8" y1="2" x2="8" y2="18" />
          <line x1="16" y1="6" x2="16" y2="22" />
        </svg>
      ),
    },
    {
      key: "profile",
      label: "我的",
      icon: (a) => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={a ? "#2D6A4F" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      ),
    },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-2xl border-t border-black/[0.06]" style={{ zIndex: 1001, paddingBottom: "env(safe-area-inset-bottom, 0px)", boxShadow: "0 -2px 20px rgba(0,0,0,0.06)" }}>
      <div className="max-w-2xl mx-auto flex items-center justify-around" style={{ height: "56px" }}>
        {tabs.map((tab) => {
          const isActive = active === tab.key;
          return (
            <button key={tab.key} onClick={() => onChange(tab.key)}
              className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full transition-all duration-200 cursor-pointer active:scale-90">
              <div className={`transition-transform duration-200 ${isActive ? "scale-110" : "scale-100"}`}>
                {tab.icon(isActive)}
              </div>
              <span className={`text-[10px] font-semibold transition-colors duration-200 ${isActive ? "text-primary" : "text-text-muted"}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/* ═══ HOME PAGE ═══ */
function HomePage({ onNavigate, onSelectSpot }: { onNavigate: (p: Page) => void; onSelectSpot: (spot: typeof SCENIC_SPOTS[number]) => void }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const touchStartX = useRef(0);

  // Auto-scroll carousel
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % CAROUSEL_ITEMS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) {
      if (diff > 0) setCurrentSlide((prev) => (prev + 1) % CAROUSEL_ITEMS.length);
      else setCurrentSlide((prev) => (prev - 1 + CAROUSEL_ITEMS.length) % CAROUSEL_ITEMS.length);
    }
  };

  return (
    <div className="min-h-screen max-w-2xl mx-auto bg-bg-page pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-xl border-b border-black/[0.04]">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-bg flex items-center justify-center"><span className="text-base">🏯</span></div>
            <div>
              <h1 className="text-base font-bold text-text-primary leading-tight">灵山胜境</h1>
              <p className="text-[10px] text-text-muted">AI智慧导览</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-primary hover:bg-primary-bg transition-all cursor-pointer">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
            </button>
          </div>
        </div>
      </div>

      {/* Carousel */}
      <div className="relative overflow-hidden animate-fade-in" onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}>
        <div className="flex transition-transform duration-500 ease-out" style={{ transform: `translateX(-${currentSlide * 100}%)` }}>
          {CAROUSEL_ITEMS.map((item, idx) => (
            <div key={idx} className="w-full shrink-0 relative cursor-pointer" style={{ height: "220px" }} onClick={() => {
              const spot = SCENIC_SPOTS.find((s) => s.name === item.title);
              if (spot) onSelectSpot(spot);
            }}>
              <img src={item.image} alt={item.title} className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-5">
                <h2 className="text-white text-xl font-bold mb-0.5">{item.title}</h2>
                <p className="text-white/80 text-xs">{item.subtitle}</p>
              </div>
            </div>
          ))}
        </div>
        {/* Dots */}
        <div className="absolute bottom-3 right-4 flex items-center gap-1.5">
          {CAROUSEL_ITEMS.map((_, idx) => (
            <button key={idx} onClick={() => setCurrentSlide(idx)}
              className={`rounded-full transition-all duration-300 cursor-pointer ${currentSlide === idx ? "w-5 h-1.5 bg-white" : "w-1.5 h-1.5 bg-white/50"}`} />
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="px-4 py-4">
        <div className="grid grid-cols-4 gap-3 animate-fade-up" style={{ animationDelay: "0.1s" }}>
          {[
            { icon: "🤖", label: "AI导游", action: () => onNavigate("chat") },
            { icon: "🗺️", label: "路线规划", action: () => onNavigate("route") },
            { icon: "🎫", label: "门票预订", action: () => {} },
            { icon: "📍", label: "景区地图", action: () => {} },
          ].map((item) => (
            <button key={item.label} onClick={item.action}
              className="flex flex-col items-center gap-1.5 py-3 rounded-2xl bg-white hover:bg-primary-bg transition-all cursor-pointer active:scale-95"
              style={{ boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
              <span className="text-2xl">{item.icon}</span>
              <span className="text-[11px] text-text-secondary font-medium">{item.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Scenic Spots */}
      <div className="px-4 pb-4">
        <div className="flex items-center justify-between mb-3 animate-fade-up" style={{ animationDelay: "0.15s" }}>
          <div className="flex items-center gap-2">
            <span className="text-base">🏔️</span>
            <h2 className="text-[15px] font-bold text-text-primary">景区景点</h2>
          </div>
          <span className="text-xs text-text-muted">共{SCENIC_SPOTS.length}处</span>
        </div>

        <div className="space-y-3">
          {SCENIC_SPOTS.map((spot, idx) => (
            <div key={spot.name} className="card card-interactive overflow-hidden animate-fade-up cursor-pointer" style={{ animationDelay: `${0.1 + idx * 0.05}s` }} onClick={() => onSelectSpot(spot)}>
              <div className="flex">
                <div className="w-28 h-28 shrink-0 relative overflow-hidden">
                  <img src={spot.image} alt={spot.name} className="w-full h-full object-cover" />
                  <div className="absolute top-2 left-2 w-7 h-7 rounded-lg bg-white/90 backdrop-blur-sm flex items-center justify-center">
                    <span className="text-sm">{spot.icon}</span>
                  </div>
                </div>
                <div className="flex-1 p-3.5 flex flex-col justify-between min-w-0">
                  <div>
                    <h3 className="text-sm font-bold text-text-primary mb-1">{spot.name}</h3>
                    <p className="text-[11px] text-text-muted leading-relaxed line-clamp-2">{spot.desc}</p>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-0.5 text-[10px] text-text-muted">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                        {spot.duration}
                      </span>
                      <span className="flex items-center gap-0.5 text-[10px] text-text-muted">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
                        {spot.distance}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      {spot.tags.map((tag) => (
                        <span key={tag} className="text-[9px] text-primary bg-primary-bg px-1.5 py-0.5 rounded font-medium">{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Info Banner */}
      <div className="px-4 pb-6 animate-fade-up" style={{ animationDelay: "0.4s" }}>
        <div className="card p-4 bg-gradient-to-r from-primary/5 to-accent/5 border-primary/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-bg flex items-center justify-center shrink-0"><span className="text-xl">📢</span></div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-text-primary mb-0.5">景区公告</p>
              <p className="text-[11px] text-text-muted leading-relaxed">九龙灌浴表演时间：10:00 / 11:30 / 14:00 / 16:00，请提前10分钟到达观赏位置</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══ SPOT DETAIL PAGE ═══ */
function SpotDetailPage({ spot, onBack, onAiGuide }: {
  spot: typeof SCENIC_SPOTS[number];
  onBack: () => void;
  onAiGuide: () => void;
}) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const nearbySpots = SCENIC_SPOTS.filter((s) => spot.nearby.includes(s.name));

  return (
    <div className="min-h-screen max-w-2xl mx-auto bg-bg-page pb-24">
      {/* Hero Image */}
      <div className="relative" style={{ height: "320px" }}>
        {!imgLoaded && (
          <div className="absolute inset-0 bg-primary-bg animate-pulse" />
        )}
        <img
          src={spot.image}
          alt={spot.name}
          className="w-full h-full object-cover"
          onLoad={() => setImgLoaded(true)}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />

        {/* Back Button */}
        <button
          onClick={onBack}
          className="absolute top-4 left-4 w-9 h-9 rounded-full bg-black/30 backdrop-blur-md flex items-center justify-center cursor-pointer hover:bg-black/50 transition-all active:scale-90"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>

        {/* Share / Favorite */}
        <div className="absolute top-4 right-4 flex gap-2">
          <button className="w-9 h-9 rounded-full bg-black/30 backdrop-blur-md flex items-center justify-center cursor-pointer hover:bg-black/50 transition-all active:scale-90">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
          </button>
        </div>

        {/* Title Overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-5">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{spot.icon}</span>
            <h1 className="text-white text-2xl font-bold">{spot.name}</h1>
          </div>
          <div className="flex items-center gap-3">
            {spot.tags.map((tag) => (
              <span key={tag} className="text-[11px] text-white/90 bg-white/20 backdrop-blur-sm px-2.5 py-1 rounded-full font-medium">{tag}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Info Bar */}
      <div className="px-4 -mt-4 relative z-10">
        <div className="bg-white rounded-2xl p-4 flex items-center justify-around" style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>
          <div className="flex flex-col items-center gap-1">
            <div className="w-9 h-9 rounded-xl bg-primary-bg flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
            </div>
            <span className="text-[11px] text-text-muted">游览时长</span>
            <span className="text-sm font-bold text-text-primary">{spot.duration}</span>
          </div>
          <div className="w-px h-10 bg-black/[0.06]" />
          <div className="flex flex-col items-center gap-1">
            <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
            </div>
            <span className="text-[11px] text-text-muted">距入口</span>
            <span className="text-sm font-bold text-text-primary">{spot.distance}</span>
          </div>
          <div className="w-px h-10 bg-black/[0.06]" />
          <div className="flex flex-col items-center gap-1">
            <div className="w-9 h-9 rounded-xl bg-sage/20 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-sage)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
            </div>
            <span className="text-[11px] text-text-muted">最佳季节</span>
            <span className="text-[11px] font-bold text-text-primary leading-tight text-center">{spot.bestSeason.length > 8 ? spot.bestSeason.substring(0, 8) + "…" : spot.bestSeason}</span>
          </div>
        </div>
      </div>

      {/* Description */}
      <div className="px-4 mt-5">
        <div className="card p-4">
          <h2 className="text-[15px] font-bold text-text-primary mb-3 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-primary" />
            景点介绍
          </h2>
          {spot.fullDesc.split("\n\n").map((para, i) => (
            <p key={i} className="text-[13px] text-text-secondary leading-[1.8] mb-3 last:mb-0">{para}</p>
          ))}
        </div>
      </div>

      {/* Highlights */}
      <div className="px-4 mt-4">
        <div className="card p-4">
          <h2 className="text-[15px] font-bold text-text-primary mb-3 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-accent" />
            核心亮点
          </h2>
          <div className="grid grid-cols-2 gap-2.5">
            {spot.highlights.map((h, i) => (
              <div key={i} className="flex items-center gap-2.5 bg-primary-bg/50 rounded-xl px-3 py-2.5">
                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-primary">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <span className="text-[12px] text-text-primary font-medium leading-snug">{h}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Practical Info */}
      <div className="px-4 mt-4">
        <div className="card p-4">
          <h2 className="text-[15px] font-bold text-text-primary mb-3 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-mist" />
            实用信息
          </h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 mt-0.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
              </div>
              <div>
                <p className="text-[12px] text-text-muted mb-0.5">开放时间</p>
                <p className="text-[13px] text-text-primary font-medium">{spot.hours}</p>
              </div>
            </div>
            <div className="h-px bg-black/[0.04]" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-bg flex items-center justify-center shrink-0 mt-0.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M2 10h20" /></svg>
              </div>
              <div>
                <p className="text-[12px] text-text-muted mb-0.5">门票信息</p>
                <p className="text-[13px] text-text-primary font-medium">{spot.ticket}</p>
              </div>
            </div>
            <div className="h-px bg-black/[0.04]" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-sage/20 flex items-center justify-center shrink-0 mt-0.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-sage)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" /></svg>
              </div>
              <div>
                <p className="text-[12px] text-text-muted mb-0.5">最佳季节</p>
                <p className="text-[13px] text-text-primary font-medium">{spot.bestSeason}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="px-4 mt-4">
        <div className="card p-4">
          <h2 className="text-[15px] font-bold text-text-primary mb-3 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-sage" />
            游览贴士
          </h2>
          <div className="space-y-2.5">
            {spot.tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full bg-accent/10 flex items-center justify-center shrink-0 mt-0.5">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                </div>
                <p className="text-[12px] text-text-secondary leading-relaxed">{tip}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Nearby Spots */}
      {nearbySpots.length > 0 && (
        <div className="mt-4">
          <div className="px-4 mb-3">
            <h2 className="text-[15px] font-bold text-text-primary flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-mist" />
              周边景点
            </h2>
          </div>
          <div className="flex gap-3 overflow-x-auto px-4 pb-2 scrollbar-hide" style={{ scrollbarWidth: "none" }}>
            {nearbySpots.map((ns) => (
              <div key={ns.name} className="shrink-0 w-36 bg-white rounded-2xl overflow-hidden" style={{ boxShadow: "0 1px 6px rgba(0,0,0,0.05)" }}>
                <div className="h-24 overflow-hidden">
                  <img src={ns.image} alt={ns.name} className="w-full h-full object-cover" />
                </div>
                <div className="p-2.5">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-sm">{ns.icon}</span>
                    <span className="text-[12px] font-bold text-text-primary">{ns.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                    <span className="text-[10px] text-text-muted">{ns.duration}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-black/[0.04]" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        <div className="max-w-2xl mx-auto flex items-center gap-3 px-4 py-3">
          <button
            onClick={onAiGuide}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-white font-semibold text-sm cursor-pointer hover:bg-primary-light active:scale-[0.98] transition-all"
            style={{ boxShadow: "0 4px 16px rgba(45,106,79,0.25)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /></svg>
            AI讲解
          </button>
          <button
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-accent text-white font-semibold text-sm cursor-pointer hover:opacity-90 active:scale-[0.98] transition-all"
            style={{ boxShadow: "0 4px 16px rgba(176,125,79,0.25)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
            导航前往
          </button>
        </div>
      </div>
    </div>
  );
}

export { HomePage, SpotDetailPage, TabBar, SCENIC_SPOTS, CAROUSEL_ITEMS };
export type { Page };
