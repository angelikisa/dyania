"""Visual system for the restrained clinical-review interface."""
from __future__ import annotations

from html import escape


def safe(value: object) -> str:
    return escape(str(value))


APP_CSS = """
<style>
:root { --canvas:#eef0f1; --paper:#fff; --ink:#22282d; --muted:#697279; --line:#d8dcdf; --soft:#f6f7f7; --teal:#286e6a; --teal-soft:#e8f1f0; --amber:#926c29; --amber-soft:#f6f0e5; --red:#9a4848; }
.stApp { background:var(--canvas); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stToolbar"], #MainMenu, footer { visibility:hidden; }
.block-container { max-width:1180px; padding:2.2rem 2.4rem 4rem; }
html, body, [class*="css"] { font-family:Inter,"Segoe UI",Arial,sans-serif; }
h1,h2,h3,h4 { color:var(--ink); letter-spacing:-.018em; }
p,label,.stCaption { color:var(--muted); }
.app-header { border-bottom:1px solid #cfd4d6; padding:0 0 1.25rem; margin-bottom:1.25rem; }
.app-kicker { color:var(--teal); font-size:.73rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.app-title { color:var(--ink); font-size:1.78rem; font-weight:660; margin:.28rem 0 .22rem; }
.app-subtitle { color:var(--muted); font-size:.93rem; max-width:760px; }
.research-label { display:inline-block; margin-top:.65rem; padding:.25rem .48rem; border:1px solid #c8cdcf; background:#f5f6f6; color:#5e666c; font-size:.68rem; font-weight:650; letter-spacing:.04em; text-transform:uppercase; }
.surface { background:var(--paper); border:1px solid var(--line); padding:1.15rem 1.25rem; margin-bottom:1rem; }
.patient-line { font-size:.9rem; color:var(--ink); }
.patient-line span { color:var(--muted); }
.metric-shell { background:var(--paper); border:1px solid var(--line); border-top:3px solid var(--teal); min-height:155px; padding:1.15rem 1.2rem; }
.metric-label { color:var(--muted); font-size:.74rem; font-weight:650; letter-spacing:.055em; text-transform:uppercase; }
.metric-value { color:var(--ink); font-size:2.05rem; line-height:1.12; font-weight:670; margin:.65rem 0 .35rem; letter-spacing:-.035em; }
.metric-detail { color:var(--muted); font-size:.78rem; line-height:1.4; }
.metric-shell.warning { border-top-color:var(--amber); } .metric-shell.critical { border-top-color:var(--red); }
.section { background:var(--paper); border:1px solid var(--line); margin-top:1rem; padding:1.35rem 1.45rem; }
.section-head { display:flex; align-items:baseline; justify-content:space-between; gap:1rem; padding-bottom:.8rem; margin-bottom:1rem; border-bottom:1px solid #e7e9ea; }
.section-title { color:var(--ink); font-size:1.05rem; font-weight:660; }
.section-note { color:var(--muted); font-size:.76rem; text-align:right; }
.stage-track { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:.8rem 0 1rem; }
.stage { border:1px solid var(--line); background:var(--soft); padding:.75rem .7rem; min-height:76px; }
.stage-num { color:var(--muted); font-size:.7rem; font-weight:700; text-transform:uppercase; }
.stage-name { color:var(--ink); font-size:.78rem; line-height:1.25; margin-top:.32rem; }
.stage.active { border:2px solid var(--teal); background:var(--teal-soft); padding:calc(.75rem - 1px) calc(.7rem - 1px); }
.stage.active .stage-num,.stage.active .stage-name { color:#174d4a; }
.fact-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.fact { background:var(--soft); border:1px solid #e2e5e6; padding:.75rem .85rem; }
.fact-label { color:var(--muted); font-size:.69rem; text-transform:uppercase; letter-spacing:.045em; }
.fact-value { color:var(--ink); font-size:.9rem; font-weight:620; margin-top:.2rem; }
.factor { display:grid; grid-template-columns:1.35fr .65fr; gap:1rem; padding:.72rem 0; border-bottom:1px solid #eceeef; }
.factor:last-child,.flag:last-child { border-bottom:0; }
.factor-name { color:var(--ink); font-size:.87rem; font-weight:620; }
.factor-copy { color:var(--muted); font-size:.76rem; margin-top:.18rem; }
.factor-effect { text-align:right; color:var(--ink); font-size:.83rem; font-weight:640; }
.factor-effect small { display:block; color:var(--muted); font-weight:400; margin-top:.15rem; }
.flag { display:grid; grid-template-columns:18px 1fr auto; gap:.65rem; align-items:start; padding:.72rem 0; border-bottom:1px solid #eceeef; }
.flag-dot { width:9px; height:9px; border-radius:50%; background:#aeb5b8; margin-top:.35rem; }
.flag.detected .flag-dot { background:var(--amber); }
.flag-name { color:var(--ink); font-size:.85rem; font-weight:620; }
.flag-copy { color:var(--muted); font-size:.74rem; margin-top:.14rem; max-width:530px; }
.flag-status { font-size:.7rem; font-weight:650; padding:.2rem .42rem; background:var(--soft); border:1px solid var(--line); color:var(--muted); white-space:nowrap; }
.flag.detected .flag-status { background:var(--amber-soft); border-color:#e2d3b6; color:#72531f; }
.followup { background:#f4f6f6; border-left:4px solid var(--teal); padding:1rem 1.1rem; }
.followup-title { color:var(--ink); font-size:1.03rem; font-weight:660; }
.followup-copy { color:var(--muted); font-size:.82rem; margin-top:.35rem; line-height:1.48; }
.evidence { border-left:2px solid #cfd5d7; padding:.35rem 0 .35rem .8rem; margin:.65rem 0; color:#4f595f; font-size:.79rem; }
.method-note { color:var(--muted); font-size:.78rem; line-height:1.55; }
.footer-note { color:#7b8388; font-size:.7rem; text-align:center; padding:1.6rem 0 0; }
div[data-testid="stFileUploader"] { background:var(--soft); border:1px solid var(--line); padding:.45rem .65rem; }
div[data-testid="stSelectbox"] label,div[data-testid="stFileUploader"] label { color:var(--ink)!important; font-size:.8rem!important; font-weight:620!important; }
.stButton>button,.stDownloadButton>button { border-radius:0; border:1px solid #bfc6c8; background:#fff; color:var(--ink); }
.stButton>button:hover,.stDownloadButton>button:hover { border-color:var(--teal); color:var(--teal); }
details { background:#fff!important; border:1px solid var(--line)!important; border-radius:0!important; }
@media(max-width:800px){.block-container{padding:1.2rem .9rem 3rem}.stage-track,.fact-grid{grid-template-columns:1fr 1fr}.section-head{display:block}.section-note{text-align:left;margin-top:.25rem}}
</style>
"""


def metric(label: str, value: str, detail: str, tone: str = "") -> str:
    return f'<div class="metric-shell {safe(tone)}"><div class="metric-label">{safe(label)}</div><div class="metric-value">{safe(value)}</div><div class="metric-detail">{safe(detail)}</div></div>'


def section_header(title: str, note: str = "") -> str:
    return f'<div class="section-head"><div class="section-title">{safe(title)}</div><div class="section-note">{safe(note)}</div></div>'
