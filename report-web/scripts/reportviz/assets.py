"""内联 CSS / JS 资源（自包含，无外部依赖）。"""

CSS = r"""
:root{--bg:#080c1a;--panel:rgba(255,255,255,.05);--panel2:rgba(255,255,255,.08);
--ink:#e8ecf1;--muted:#7a8699;--line:rgba(255,255,255,.07);--accent:#6366f1;
--accent2:#a78bfa;--up:#ef4444;--down:#22c55e;--warn:#f59e0b;
--side:rgba(8,12,26,.85);--grad:linear-gradient(135deg,#667eea,#764ba2);
--glow:0 0 30px rgba(99,102,241,.15);--glow2:0 0 60px rgba(118,75,162,.1)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",-apple-system,sans-serif;background:var(--bg);color:var(--ink);line-height:1.8;letter-spacing:0;overflow-x:hidden;font-size:17px}
body::before{content:"";position:fixed;inset:0;background:radial-gradient(ellipse at 20% 20%,rgba(99,102,241,.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 80%,rgba(118,75,162,.06) 0%,transparent 50%),radial-gradient(ellipse at 50% 50%,rgba(99,102,241,.04) 0%,transparent 70%);pointer-events:none;z-index:0}
a{color:var(--accent2);text-decoration:none;transition:.2s}
a:hover{color:#c4b5fd;text-shadow:0 0 8px rgba(167,139,250,.4)}
code{font-family:"Cascadia Code","Fira Code",monospace;font-size:.88em;background:rgba(99,102,241,.1);color:#c4b5fd;padding:2px 7px;border-radius:5px;border:1px solid rgba(99,102,241,.15)}
pre{background:rgba(0,0,0,.4);border:1px solid var(--line);border-radius:12px;padding:16px 18px;overflow:auto;font-size:.85em;line-height:1.6;backdrop-filter:blur(10px)}
pre code{background:none;border:none;padding:0;color:#a5b4fc}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:rgba(255,255,255,.03)}
::-webkit-scrollbar-thumb{background:rgba(99,102,241,.3);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(99,102,241,.5)}

.progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,#6366f1,#a78bfa,#ec4899);z-index:999;border-radius:0 3px 3px 0;box-shadow:0 0 12px rgba(99,102,241,.5)}
.reveal{opacity:1;transform:none;transition:opacity .5s cubic-bezier(.22,1,.36,1),transform .5s cubic-bezier(.22,1,.36,1)}
html.js .reveal:not(.on){opacity:0;transform:translateY(18px)}
.reveal.on{opacity:1;transform:translateY(0)}

.sidebar{position:fixed;top:0;left:0;bottom:0;width:280px;background:var(--side);backdrop-filter:blur(24px);border-right:1px solid rgba(255,255,255,.1);z-index:100;overflow-y:auto;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:14px;padding:22px 22px 18px;border-bottom:1px solid var(--line)}
.brand-mark{width:38px;height:38px;border-radius:10px;background:var(--grad);display:flex;align-items:center;justify-content:center;flex:none;box-shadow:0 4px 16px rgba(99,102,241,.4)}
.brand-mark svg{width:20px;height:20px}
.brand-name{font-weight:700;font-size:17px;color:#fff}
.brand-sub{font-size:11px;color:var(--muted)}
.toc-title{padding:18px 22px 8px;font-size:10px;letter-spacing:3px;color:var(--muted);text-transform:uppercase}
.toc{list-style:none;margin:0;padding:0 12px 20px;flex:1;overflow-y:auto}
.toc li{margin:2px 0}
.toc a{display:block;padding:10px 16px;border-radius:8px;color:#b0bac8;font-size:16px;line-height:1.5;border-left:2px solid transparent;transition:.2s}
.toc a:hover{background:rgba(99,102,241,.08);color:#fff;padding-left:18px;box-shadow:inset 0 0 16px rgba(99,102,241,.06)}
.toc a.active{background:rgba(99,102,241,.14);color:#c4b5fd;border-left-color:var(--accent2);box-shadow:inset 0 0 24px rgba(99,102,241,.06)}
.toc .l3{padding-left:28px;font-size:13px}
.toc .l4{padding-left:40px;font-size:12px;color:var(--muted)}
.side-foot{margin-top:auto;padding:16px 20px;font-size:11px;color:var(--muted);border-top:1px solid var(--line)}

.main{margin-left:280px;position:relative;z-index:1}
.hero{padding:48px 56px 34px;border-bottom:1px solid var(--line)}
.hero-tags{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}
.tag{font-size:13px;color:#c4b5fd;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.25);padding:4px 12px;border-radius:20px;font-weight:500;letter-spacing:1px}
.tag.hi{background:var(--grad);color:#fff;border:none;box-shadow:0 2px 12px rgba(99,102,241,.3)}
.hero h1{margin:0 0 14px;font-size:36px;font-weight:800;line-height:1.3;background:linear-gradient(135deg,#fff 40%,#a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-meta{color:var(--muted);font-size:15px;display:flex;flex-wrap:wrap;gap:8px 28px}
.hero-meta b{color:#a5b4fc;font-weight:600}

.dashboard{max-width:1100px;margin:0 auto;padding:24px 56px 0}
.idx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:20px 0}
.idx-card{background:var(--panel);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:24px 26px;backdrop-filter:blur(16px);transition:transform .3s ease,border-color .3s ease,box-shadow .3s ease;position:relative;overflow:hidden}
.idx-card::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--grad);opacity:.6}
.idx-card:hover{background:var(--panel2);border-color:rgba(99,102,241,.25);box-shadow:var(--glow);transform:translateY(-3px)}
.idx-name{font-size:12px;color:var(--muted);margin-bottom:6px;letter-spacing:1px}
.idx-pt{font-size:26px;font-weight:700;font-family:monospace;color:#fff}
.idx-val{font-size:32px;font-weight:800;font-family:monospace}
.idx-val.up{color:var(--up)}.idx-val.down{color:var(--down)}

.dash-row{display:flex;justify-content:center;margin:16px 0}
.dash-cell{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;backdrop-filter:blur(12px)}
.donut text{font-family:inherit}
.donut-big{font-size:24px;font-weight:800}
.donut-sm{font-size:11px;fill:var(--muted)}
.donut-xs{font-size:10px}

.sec-block{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.sec-t{font-size:12px;color:var(--muted);margin-bottom:8px;letter-spacing:2px}
.hbar,.cchart{width:100%;height:auto;display:block}
.hbar text,.cchart text{font-family:inherit}
.cl{font-size:12px;fill:#8a94a6}
.cv{font-size:12px;fill:#e8ecf1;font-weight:600}
.cbar{transition:width .8s cubic-bezier(.22,1,.36,1)}

.mgn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.mgn-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:4px;backdrop-filter:blur(12px)}
.mgn-card .k{font-size:11px;color:var(--muted)}
.mgn-card .v{font-size:22px;font-weight:700;font-family:monospace;color:#fff}
.mgn-card .v.up{color:var(--up)}.mgn-card .v.down{color:var(--down)}

.content{max-width:1100px;margin:0 auto;padding:32px 56px 48px}
.content h2{font-size:24px;margin:48px 0 22px;padding:14px 20px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;border-left:3px solid rgba(99,102,241,.6);backdrop-filter:blur(14px);letter-spacing:.02em}
.content h3{font-size:20px;margin:28px 0 12px;padding-bottom:10px;border-bottom:1px solid var(--line);color:#c4b5fd}
.content h4{font-size:17px;margin:20px 0 8px;color:var(--accent2)}
.content h2[id^="risk"],.content h2[id^="sec-12"],.content h2[id^="sec-13"]{border-left-color:var(--up);background:rgba(239,68,68,.06)}
p{margin:14px 0;line-height:1.85;max-width:860px}
ul,ol{margin:12px 0;padding-left:28px;max-width:860px}
li{margin:7px 0;line-height:1.75}
li .kv-k{color:var(--muted);margin-right:10px;font-size:.95em}
li .kv-v{font-weight:700;font-family:monospace;color:#fff;font-size:1.25em;padding:2px 6px;border-radius:5px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.04)}
li .kv-v.up{color:var(--up)}.li .kv-v.down{color:var(--down)}

.tw{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:12px;backdrop-filter:blur(10px)}
table{border-collapse:collapse;width:100%;font-size:15px;background:rgba(0,0,0,.25)}
th{background:rgba(99,102,241,.08);color:#a5b4fc;text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap;font-weight:600;font-size:12px;letter-spacing:1px}
td{padding:9px 14px;border-bottom:1px solid rgba(255,255,255,.03);white-space:nowrap}
tbody tr:hover{background:rgba(99,102,241,.05)}
tbody tr:last-child td{border-bottom:none}

.tc{margin:14px 0 20px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.tc-t{font-size:11px;color:var(--muted);margin-bottom:8px;letter-spacing:2px}
.gauge{width:100%;max-width:220px;height:auto;display:block;margin:0 auto}
.gauge-val{font-size:26px;font-weight:800;font-family:monospace}
.gauge-lbl{font-size:11px;fill:var(--muted)}

blockquote{margin:20px 0;padding:18px 24px;background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.15);border-left:4px solid var(--warn);border-radius:0 12px 12px 0;color:#fde68a;backdrop-filter:blur(10px)}
blockquote p{margin:6px 0}
hr{border:none;height:1px;background:linear-gradient(90deg,transparent,var(--line),transparent);margin:24px 0}

.foot{max-width:1020px;margin:0 auto;padding:20px 48px 50px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);margin-top:20px}
#top{position:fixed;right:24px;bottom:24px;width:48px;height:48px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:#fff;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(0,0,0,.4);backdrop-filter:blur(10px);transition:.2s;z-index:100}
#top:hover{background:rgba(99,102,241,.15);border-color:var(--accent);box-shadow:var(--glow)}
#top svg{width:20px;height:20px}

@media(max-width:920px){
.sidebar{position:static;width:auto;height:auto}
.toc{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:4px;padding:4px 12px 12px}
.toc li{flex:none}.toc a{border-left:none;border-bottom:2px solid transparent;white-space:nowrap;border-radius:0}
.toc a.active{border-bottom-color:var(--accent2)}
.toc .l3,.toc .l4{padding-left:10px}.toc-title{display:none}.side-foot{display:none}
.main{margin-left:0}.hero{padding:28px 20px}.hero h1{font-size:22px}
.dashboard{padding:16px 16px 0}.content{padding:20px 16px}.foot{padding:16px 20px 30px}
}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{box-shadow:0 0 20px rgba(99,102,241,.1)}50%{box-shadow:0 0 40px rgba(99,102,241,.25)}}
.idx-card:hover{animation:pulse 2s infinite}
.rating-banner{display:flex;align-items:center;gap:20px;padding:24px 32px;border-radius:16px;margin:0 0 18px;backdrop-filter:blur(16px)}
.rating-banner.rt-buy{background:linear-gradient(135deg,rgba(251,146,60,.15) 0%,rgba(239,68,68,.1) 100%);border:1px solid rgba(251,146,60,.3);box-shadow:0 0 20px rgba(251,146,60,.08);padding:20px 28px}
.rating-banner.rt-sell{background:linear-gradient(135deg,rgba(34,197,94,.12),rgba(34,197,94,.04));border:1px solid rgba(34,197,94,.25)}
.rt-label{font-size:12px;color:var(--muted);letter-spacing:3px;text-transform:uppercase}
.rt-val{font-size:40px;font-weight:800;background:linear-gradient(135deg,#ef4444,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-buy .rt-val{background:linear-gradient(135deg,#ef4444,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-sell .rt-val{background:linear-gradient(135deg,#22c55e,#14b8a6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-tgt{margin-left:auto;font-size:18px;font-weight:700;color:var(--warn);font-family:monospace}
.sm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:16px 0;align-items:start}
.sm-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;backdrop-filter:blur(12px);transition:.3s;animation:fadeUp .5s both;animation-delay:var(--d,0s)}
.sm-card:hover{background:var(--panel2);border-color:rgba(99,102,241,.3);transform:translateY(-2px);box-shadow:var(--glow)}
.sm-k{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.sm-v{font-size:28px !important;font-weight:700;font-family:monospace;color:#fff}
.sm-v.up{color:var(--up)}.sm-v.down{color:var(--down)}
.pz-wrap{margin:16px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;backdrop-filter:blur(12px)}
.pz-title{font-size:12px;color:var(--muted);letter-spacing:2px;margin-bottom:12px}
.pz-bar{position:relative;height:24px;border-radius:9999px;overflow:visible;background:linear-gradient(90deg,#22c55e 0%,#eab308 50%,#ef4444 100%);opacity:.7}
.pz-zone90{position:absolute;top:0;left:0;right:0;height:100%;border-radius:12px;background:linear-gradient(90deg,rgba(34,197,94,.15),rgba(255,255,255,.05),rgba(239,68,68,.15))}
.pz-zone70{position:absolute;top:2px;height:calc(100% - 4px);border-radius:10px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.2)}
.pz-mark{position:absolute;top:-6px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:4px;z-index:2}
.pz-dot{width:12px;height:12px;border-radius:50%;border:2px solid rgba(255,255,255,.4);box-shadow:0 0 0 4px rgba(255,255,255,.15),0 0 12px rgba(255,255,255,.4)}
.pz-lbl{font-size:10px;color:var(--muted);white-space:nowrap;font-family:monospace}
.pz-labels{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:8px;font-family:monospace}
.sg-wrap{text-align:center;padding:8px}
.sg-title{font-size:12px;color:var(--muted);letter-spacing:2px;margin-bottom:6px}
.gauge-xs{font-size:9px}
.dash-row{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:16px 0}
.dash-cell{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:12px;backdrop-filter:blur(12px);min-width:200px}
.content h2{position:relative;overflow:hidden}
.content h2::after{content:"";position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,rgba(99,102,241,.4),transparent 70%)}
.content strong{color:#c4b5fd;font-weight:700}
.content h2 + p, .content h2 + ul {margin-top:12px}
.hm-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.hm-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
.hm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;align-items:stretch}
.hm-tile{border-radius:8px;padding:12px 16px;text-align:center;transition:.2s;cursor:default;border:1px solid rgba(255,255,255,.06);backdrop-filter:blur(8px)}
.hm-tile:hover{transform:scale(1.04);border-color:rgba(255,255,255,.1)}
.hm-n{display:block;font-size:12px;color:#c0cad6;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hm-v{display:block;font-size:19px;font-weight:800;font-family:monospace}
.num{font-family:monospace;font-weight:700;color:#a5b4fc;font-size:1.2em;padding:2px 6px;border-radius:5px;background:rgba(99,102,241,.1);text-shadow:0 0 12px rgba(165,180,252,.2)}
.sm-card.has-ring{display:flex;align-items:center;gap:10px}
.sm-ring{flex:none}
.sm-body{flex:1;min-width:0}
.mring{display:block}
.idx-val{font-size:26px !important;font-weight:800 !important;text-shadow:0 0 20px rgba(255,255,255,.08)}
.idx-card .idx-name{font-size:11px;letter-spacing:1px;text-transform:uppercase}
.idx-card .idx-pt{font-size:17px;font-family:monospace;color:#a5b4fc;font-weight:600}
.sm-v{font-size:22px !important}
.content li .kv-v{font-size:1.1em !important;padding:1px 4px;border-radius:4px;background:rgba(255,255,255,.03)}
.content .num{padding:1px 3px;border-radius:4px;background:rgba(99,102,241,.08)}
.dash-two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}
.mc-wrap,.ob-wrap,.ml-wrap,.fb-wrap,.ts-wrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;backdrop-filter:blur(12px);margin:10px 0}
.mc-title,.ob-title,.ml-title,.fb-title,.ts-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:12px;text-transform:uppercase}
.mc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px}
.mc-chip{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.12);border-radius:8px;padding:10px 12px;text-align:center;transition:transform .2s ease}
.mc-k{display:block;font-size:10px;color:var(--muted);margin-bottom:2px}
.mc-v{display:block;font-size:18px;font-weight:700;font-family:monospace;color:#a5b4fc}
.ob-row{display:flex;align-items:center;gap:10px;margin:6px 0}
.ob-n{width:60px;font-size:12px;color:var(--muted);flex:none}
.ob-track{flex:1;height:8px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden}
.ob-fill{height:100%;border-radius:9999px;box-shadow:inset 0 1px 2px rgba(255,255,255,.1);transition:width .8s cubic-bezier(.22,1,.36,1)}
.ob-v{width:70px;text-align:right;font-size:15px;font-family:monospace;font-weight:600;flex:none}
.mlchart{width:100%;height:auto;display:block}
.ml-line{filter:drop-shadow(0 0 6px rgba(99,102,241,.4))}
.ml-legend{display:flex;gap:16px;align-items:center;font-size:11px;color:var(--muted);margin-top:8px}
.ml-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:middle}
.ax-lbl{font-size:9px;fill:var(--muted);font-family:monospace}
.fb-row{display:flex;align-items:center;gap:12px;margin:8px 0}
.fb-k{width:56px;font-size:12px;color:var(--muted);flex:none}
.fb-track{flex:1;height:10px;background:rgba(255,255,255,.04);border-radius:5px;overflow:hidden}
.fb-fill{height:100%;border-radius:9999px;background:linear-gradient(90deg,#3b82f6,#60a5fa);box-shadow:inset 0 1px 2px rgba(255,255,255,.1),0 2px 8px rgba(59,130,246,.25);transition:width .8s cubic-bezier(.22,1,.36,1)}
.fb-v{width:70px;text-align:right;font-size:16px;font-family:monospace;font-weight:600;color:#a5b4fc;flex:none}
.ts-grid{display:flex;flex-wrap:wrap;gap:8px}
.ts-pill{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 14px;display:flex;align-items:center;gap:8px}
.ts-k{font-size:11px;color:var(--muted)}
.ts-v{font-size:14px;font-weight:700;font-family:monospace}
@media(max-width:768px){.dash-two{grid-template-columns:1fr}}

.ff-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 20px;backdrop-filter:blur(12px)}
.ff-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
.ff-bar{height:10px;background:rgba(255,255,255,.04);border-radius:5px;overflow:hidden;margin:8px 0}
.ff-fill{height:100%;border-radius:5px;width:65%;transition:width 1s cubic-bezier(.22,1,.36,1)}
.ff-val{font-size:24px;font-weight:700;font-family:monospace;text-align:center}

.wf-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;backdrop-filter:blur(12px)}
.wf-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
.wf-chart{width:100%;height:auto;display:block}
.rb-wrap{display:flex;align-items:center;gap:12px;padding:10px 0}
.rb-title{font-size:11px;color:var(--muted);letter-spacing:1px;flex:none}
.rb-bar{display:flex;gap:3px;flex:1;max-width:200px}
.rb-seg{height:10px;flex:1;border-radius:2px}
.rb-lbl{font-size:13px;font-weight:700;font-family:monospace;flex:none}
/* ===== 要点横幅 ===== */
.kp-wrap{margin:20px 0 8px;background:linear-gradient(135deg,rgba(99,102,241,.10),rgba(34,211,238,.05));border:1px solid rgba(99,102,241,.22);border-radius:14px;padding:16px 18px;backdrop-filter:blur(14px)}
.kp-title{font-size:12px;letter-spacing:3px;color:#a5b4fc;text-transform:uppercase;margin-bottom:12px}
.kp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px}
.kp-card{position:relative;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px 14px 12px 16px;overflow:hidden}
.kp-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
.kp-gain::before{background:hsl(354,92%,58%)}
.kp-loss::before{background:hsl(158,88%,52%)}
.kp-neutral::before{background:#22d3ee}
.kp-k{display:block;font-size:11px;color:var(--muted);letter-spacing:1px}
.kp-v{display:block;font-size:21px;font-weight:800;font-family:monospace;margin:4px 0 2px;color:#fff}
.kp-gain .kp-v{color:hsl(354,95%,68%)}
.kp-loss .kp-v{color:hsl(158,90%,60%)}
.kp-neutral .kp-v{color:#67e8f9}
.kp-sub{display:block;font-size:11px;color:var(--muted)}
.bc-wrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.bc-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:12px;text-transform:uppercase}
.bc-stack{display:flex;height:36px;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,.08)}
.bc-seg{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;font-family:monospace;color:#0b1020;transition:width .9s cubic-bezier(.22,1,.36,1)}
.bc-up{background:linear-gradient(90deg,hsl(354,80%,46%),hsl(354,92%,60%))}
.bc-down{background:linear-gradient(90deg,hsl(158,70%,40%),hsl(158,85%,52%))}
.bc-axis{display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:6px;font-family:monospace}
.bc-limits{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}
.bc-limit{display:flex;align-items:center;gap:10px}
.bc-lk{font-size:12px;color:var(--muted);flex:none;width:32px}
.bc-lt{flex:1;height:10px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden}
.bc-lf{height:100%;border-radius:5px;transition:width .9s cubic-bezier(.22,1,.36,1)}
.bc-lv{font-size:15px;font-weight:800;font-family:monospace;flex:none;width:36px;text-align:right}
.bc-upv{color:hsl(354,95%,66%)}
.bc-downv{color:hsl(158,90%,58%)}
.mc2-wrap{text-align:center;padding:4px}
.mc2-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:6px;text-transform:uppercase}
.mc2-donut{width:100%;max-width:170px;height:auto;display:block;margin:0 auto}
.mc2-big{font-size:17px;font-weight:800;font-family:monospace;fill:#fff}
.mc2-sm{font-size:10px;fill:var(--muted)}
.mc2-legend{display:flex;justify-content:center;gap:14px;font-size:11px;color:var(--muted);margin-top:6px}
.mc2-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}
.sb-wrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.sb-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
.sb-chart{width:100%;height:auto;display:block}
.sb-n{font-size:12px;fill:#c0cad6}
.sb-v{font-size:12px;font-weight:700;font-family:monospace}
.idx-card::before{background:var(--acc,#6366f1) !important}
.idx-card:hover{border-color:var(--acc,#6366f1) !important}
.idx-name{color:var(--acc,#7a8699) !important}
.mc-chip{border-left:3px solid var(--acc,#6366f1)}
.hm-tile{transition:transform .18s ease,box-shadow .18s ease}
.hm-tile:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.35)}
.dash-sec{margin:32px 0}
.dash-sec-t{font-size:12px;color:var(--accent2);letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;padding-left:12px;border-left:3px solid var(--accent)}

"""


JS = r"""
(()=> {
  const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting)e.target.classList.add("on")})},{threshold:.08});
  document.querySelectorAll(".reveal").forEach(el=>io.observe(el));
  const links=[...document.querySelectorAll(".toc a")];
  const map=new Map(links.map(a=>[a.getAttribute("href").slice(1),a]));
  const sio=new IntersectionObserver(es=>{
    let cur=null;for(const e of es){if(e.isIntersecting)cur=e.target}
    if(cur){links.forEach(a=>a.classList.remove("active"));const m=map.get(cur.id);if(m)m.classList.add("active")}
  },{rootMargin:"-10% 0px -80% 0px"});
  document.querySelectorAll("h2[id],h3[id]").forEach(h=>sio.observe(h));
  document.querySelectorAll(".cbar").forEach(r=>{
    const w=r.dataset.w;if(w){requestAnimationFrame(()=>{setTimeout(()=>r.style.width=w+"px",200)})}
  });
  document.querySelectorAll(".idx-val[data-val]").forEach(el=>{
    const target=parseFloat(el.dataset.val);const dur=800;const st=performance.now();
    const step=(now)=>{const p=Math.min(1,(now-st)/dur);const v=target*p;
      el.textContent=(v>=0?"+":"")+v.toFixed(2)+"%";if(p<1)requestAnimationFrame(step)};
    requestAnimationFrame(step);
  });
  const bar=document.querySelector(".progress"),topBtn=document.querySelector("#top");
  const onScroll=()=>{const h=document.documentElement;
    if(bar)bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+"%";
    if(topBtn)topBtn.style.display=h.scrollTop>600?"flex":"none"};
  window.addEventListener("scroll",onScroll,{passive:true});
  if(topBtn)topBtn.addEventListener("click",()=>window.scrollTo({top:0,behavior:"smooth"}));
  onScroll();
})();

"""
