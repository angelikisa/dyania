"""Professional visual system for the valve review interface."""
from __future__ import annotations

from html import escape


def safe(value: object) -> str:
    return escape(str(value))


APP_CSS = """
<style>
:root{--bg:#f1f2f2;--paper:#fff;--ink:#202629;--muted:#687176;--line:#d8dcde;--soft:#f6f7f7;--teal:#286e6a;--teal-soft:#e9f1f0;--amber:#8b6727;--red:#914545}
.stApp{background:var(--bg);color:var(--ink)}
[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"],#MainMenu,footer{visibility:hidden}
.block-container{max-width:1120px;padding:0 2rem 3.5rem}
html,body,[class*="css"]{font-family:Inter,"Segoe UI",Arial,sans-serif} p,label,.stCaption{color:var(--muted)}
.nav{height:64px;background:#252b2e;color:#fff;margin:0 calc(50% - 50vw) 2.1rem;padding:0 max(2rem,calc((100vw - 1080px)/2));display:flex;align-items:center;justify-content:space-between}
.nav-brand{font-size:1rem;font-weight:720;letter-spacing:.12em}.nav-brand span{color:#7db3ae}
.nav-links{display:flex;gap:1.6rem;font-size:.76rem;color:#c9ced0}.nav-active{color:#fff;border-bottom:2px solid #7db3ae;padding:22px 0 19px}
.page-intro{display:flex;align-items:end;justify-content:space-between;border-bottom:1px solid #cfd4d6;padding-bottom:1.25rem;margin-bottom:1.4rem}
.page-title{font-size:1.75rem;line-height:1.15;font-weight:670;letter-spacing:-.03em}.page-subtitle{font-size:.88rem;color:var(--muted);margin-top:.35rem;max-width:680px}
.prototype-note{font-size:.68rem;color:#767e82;white-space:nowrap}
.input-panel{background:var(--paper);border:1px solid var(--line);padding:1.2rem 1.35rem;margin-bottom:1.35rem}
.input-title{font-size:.96rem;font-weight:650}.input-copy{font-size:.78rem;color:var(--muted);margin:.2rem 0 .8rem}
.patient-line{font-size:.82rem;color:var(--ink);border-top:1px solid #e7e9ea;padding-top:.75rem;margin-top:.5rem}.patient-line span{color:var(--muted)}
.summary{background:var(--paper);border:1px solid var(--line);display:grid;grid-template-columns:1.45fr 1fr 1fr;margin-bottom:1.25rem}
.summary-main{padding:1.4rem 1.5rem;border-right:1px solid var(--line)}.summary-side{padding:1.4rem 1.3rem;border-right:1px solid var(--line)}.summary-side:last-child{border-right:0}
.summary-label{font-size:.68rem;color:var(--muted);font-weight:680;letter-spacing:.07em;text-transform:uppercase}
.summary-value{font-size:2.35rem;font-weight:690;line-height:1.08;margin:.55rem 0 .3rem;letter-spacing:-.04em}.summary-side .summary-value{font-size:1.45rem;letter-spacing:-.025em}
.summary-detail{font-size:.75rem;color:var(--muted);line-height:1.45}.risk-note{margin-top:.55rem;font-size:.7rem;color:#737b7f}
.section{background:var(--paper);border:1px solid var(--line);margin-top:1rem;padding:1.35rem 1.45rem}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;padding-bottom:.75rem;margin-bottom:.9rem;border-bottom:1px solid #e5e8e9}
.section-title{font-size:1.04rem;font-weight:660}.section-note{font-size:.73rem;color:var(--muted);text-align:right}
.factor{display:grid;grid-template-columns:1.2fr .8fr;gap:1rem;padding:.85rem .2rem;border-bottom:1px solid #eceeef;transition:background .15s ease}.factor:hover{background:#fafbfb}.factor:last-child{border-bottom:0}
.factor-name{font-size:.88rem;font-weight:640}.factor-copy{font-size:.75rem;color:var(--muted);margin-top:.18rem}.factor-effect{text-align:right;font-size:.82rem;font-weight:640}.factor-effect small{display:block;color:var(--muted);font-weight:400;margin-top:.17rem}
.stage-track{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:.6rem 0 1rem}.stage{border-top:4px solid #d5d9db;background:var(--soft);padding:.75rem;min-height:74px;margin-right:3px}.stage-num{font-size:.68rem;font-weight:700;color:var(--muted);text-transform:uppercase}.stage-name{font-size:.76rem;margin-top:.3rem;line-height:1.3}.stage.active{border-top-color:var(--teal);background:var(--teal-soft)}.stage.active .stage-num,.stage.active .stage-name{color:#194e4a}
.fact-grid{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #e5e8e9;border-left:1px solid #e5e8e9}.fact{padding:.75rem .85rem;border-right:1px solid #e5e8e9;border-bottom:1px solid #e5e8e9}.fact-label{font-size:.66rem;color:var(--muted);text-transform:uppercase;letter-spacing:.045em}.fact-value{font-size:.86rem;font-weight:610;margin-top:.2rem}
.evidence{border-left:2px solid #bcc5c7;padding:.35rem 0 .35rem .8rem;margin:.8rem 0 0;color:#50595e;font-size:.76rem}
.flag{display:grid;grid-template-columns:16px 1fr auto;gap:.65rem;align-items:start;padding:.75rem 0;border-bottom:1px solid #eceeef}.flag:last-child{border-bottom:0}.flag-dot{width:8px;height:8px;border-radius:50%;background:var(--amber);margin-top:.38rem}.flag-name{font-size:.85rem;font-weight:630}.flag-copy{font-size:.73rem;color:var(--muted);margin-top:.14rem}.flag-status{font-size:.68rem;font-weight:650;color:#70511d;background:#f6f0e5;padding:.2rem .42rem}
.followup-grid{display:grid;grid-template-columns:.9fr 1.5fr 1.1fr;border:1px solid #dfe3e4}.followup-cell{padding:1rem 1.1rem;border-right:1px solid #dfe3e4}.followup-cell:last-child{border-right:0}.followup-label{font-size:.66rem;color:var(--muted);font-weight:680;letter-spacing:.06em;text-transform:uppercase}.followup-value{font-size:.94rem;font-weight:640;margin-top:.34rem;line-height:1.35}.followup-foot{font-size:.71rem;color:var(--muted);margin-top:.75rem}
.method-note{font-size:.75rem;color:var(--muted);line-height:1.52}.footer-note{font-size:.68rem;color:#7a8286;text-align:center;padding:1.5rem 0 0}
div[data-testid="stFileUploader"]{background:var(--soft);border:1px dashed #bfc6c8;padding:.4rem .65rem}div[data-testid="stFileUploader"] label,div[data-testid="stSelectbox"] label{color:var(--ink)!important;font-size:.79rem!important;font-weight:620!important}
.stButton>button,.stDownloadButton>button{border-radius:2px;border:1px solid #bcc3c5;background:#fff;color:var(--ink)}.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--teal);color:var(--teal)}
details{background:#fff!important;border:1px solid var(--line)!important;border-radius:0!important}
@media(max-width:800px){.block-container{padding:0 .85rem 3rem}.nav{padding:0 1rem}.nav-links{display:none}.page-intro{display:block}.prototype-note{margin-top:.6rem}.summary{grid-template-columns:1fr}.summary-main,.summary-side{border-right:0;border-bottom:1px solid var(--line)}.stage-track,.fact-grid,.followup-grid{grid-template-columns:1fr}.followup-cell{border-right:0;border-bottom:1px solid #dfe3e4}.section-head{display:block}.section-note{text-align:left;margin-top:.2rem}}
</style>
"""


def section_header(title: str, note: str = "") -> str:
    return f'<div class="section-head"><div class="section-title">{safe(title)}</div><div class="section-note">{safe(note)}</div></div>'
