"""Visual system and safe HTML fragments for the Streamlit app."""
from __future__ import annotations

from html import escape


COLORS = {
    "ink": "#102326",
    "muted": "#5D7072",
    "teal": "#087F82",
    "cyan": "#32A9D6",
    "mint": "#DFF3EE",
    "paper": "#FFFFFF",
    "canvas": "#F4F8F7",
    "line": "#D8E5E3",
    "coral": "#C76052",
    "amber": "#B87916",
}


APP_CSS = """
<style>
  :root {
    --ink: #102326;
    --muted: #5D7072;
    --teal: #087F82;
    --cyan: #32A9D6;
    --mint: #DFF3EE;
    --canvas: #F4F8F7;
    --line: #D8E5E3;
    --coral: #C76052;
    --amber: #B87916;
  }

  .stApp { background: var(--canvas); color: var(--ink); }
  .block-container { max-width: 1440px; padding-top: 1.45rem; padding-bottom: 3rem; }
  [data-testid="stSidebar"] { background: #102326; border-right: 0; }
  [data-testid="stSidebar"] * { color: #F4FBF9; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color: #102326; }
  [data-testid="stSidebar"] .stCaption,
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: #A9C5C2 !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15); }
  [data-testid="stSidebar"] .stButton > button {
    width: 100%; border: 1px solid rgba(255,255,255,.32); background: rgba(255,255,255,.07);
    color: white; border-radius: 8px; font-weight: 650;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    border-color: #66D3C5; background: rgba(102,211,197,.12); color: white;
  }

  h1, h2, h3 { color: var(--ink); letter-spacing: -0.025em; }
  h1 { font-weight: 690; }
  h2, h3 { font-weight: 650; }
  p, li { color: var(--ink); }
  a { color: var(--teal); }

  .brand-lockup { margin: .25rem 0 1.8rem; }
  .brand-name { font-size: .78rem; letter-spacing: .32em; font-weight: 750; color: #66D3C5; }
  .brand-product { margin-top: .45rem; font-size: 1.22rem; line-height: 1.2; font-weight: 680; color: white; }
  .brand-sub { margin-top: .45rem; color: #A9C5C2; font-size: .82rem; line-height: 1.45; }

  .page-header { padding: .2rem .1rem .45rem; }
  .eyebrow { color: var(--teal); font-size: .72rem; font-weight: 750; letter-spacing: .24em; text-transform: uppercase; }
  .page-title { color: var(--ink); font-size: clamp(1.8rem, 3vw, 2.65rem); line-height: 1.06; font-weight: 690; letter-spacing: -.035em; margin: .38rem 0 .42rem; }
  .page-subtitle { color: var(--muted); font-size: 1rem; max-width: 760px; line-height: 1.55; }
  .header-rule { height: 4px; width: 100%; margin-top: 1rem; border-radius: 10px; background: linear-gradient(90deg, var(--cyan), #66D3C5 70%, transparent); }

  .status-strip {
    display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; margin: .45rem 0 1rem;
    padding: .72rem .9rem; border: 1px solid #C9DEDA; border-left: 4px solid var(--teal);
    background: #ECF7F4; border-radius: 8px; color: #315356; font-size: .84rem;
  }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--teal); display: inline-block; }
  .status-separator { color: #9AB1AF; }

  .metric-card {
    min-height: 144px; padding: 1rem 1rem .9rem; border: 1px solid var(--line); border-radius: 10px;
    background: white; box-shadow: 0 1px 1px rgba(16,35,38,.025);
  }
  .metric-kicker { color: var(--muted); font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 720; }
  .metric-value { margin-top: .42rem; color: var(--ink); font-size: clamp(1.55rem, 2.2vw, 2.15rem); line-height: 1.05; font-weight: 710; letter-spacing: -.035em; }
  .metric-detail { margin-top: .55rem; color: var(--muted); font-size: .78rem; line-height: 1.35; }
  .metric-accent { color: var(--teal); }
  .metric-warning { color: var(--amber); }
  .metric-danger { color: var(--coral); }

  .panel {
    background: white; border: 1px solid var(--line); border-radius: 10px; padding: 1.05rem 1.1rem;
    margin-bottom: .8rem;
  }
  .panel-title { color: var(--ink); font-size: 1rem; font-weight: 680; margin-bottom: .25rem; }
  .panel-copy { color: var(--muted); font-size: .86rem; line-height: 1.55; }

  .badge { display: inline-flex; align-items: center; border-radius: 999px; padding: .27rem .58rem; font-size: .7rem; font-weight: 720; letter-spacing: .035em; }
  .badge-teal { color: #075F62; background: #D9F1EC; border: 1px solid #BFE4DC; }
  .badge-amber { color: #7A5008; background: #FFF2D8; border: 1px solid #F0D9A7; }
  .badge-coral { color: #8B3D32; background: #FBE5E1; border: 1px solid #EDC7C0; }
  .badge-neutral { color: #526769; background: #EDF2F1; border: 1px solid #D8E3E1; }

  .kv-grid { display: grid; grid-template-columns: minmax(120px,.8fr) 1.4fr; gap: .52rem .8rem; margin-top: .7rem; }
  .kv-key { color: var(--muted); font-size: .78rem; }
  .kv-value { color: var(--ink); font-size: .82rem; font-weight: 610; word-break: break-word; }

  .pipeline { display: grid; grid-template-columns: repeat(5, 1fr); gap: .55rem; margin: .75rem 0 1rem; }
  .pipeline-step { position: relative; min-height: 93px; padding: .78rem; border: 1px solid var(--line); border-radius: 8px; background: white; }
  .pipeline-index { color: var(--teal); font-size: .66rem; font-weight: 760; letter-spacing: .12em; }
  .pipeline-name { color: var(--ink); font-size: .84rem; font-weight: 670; margin-top: .32rem; }
  .pipeline-copy { color: var(--muted); font-size: .71rem; line-height: 1.35; margin-top: .28rem; }

  .evidence-item { border-left: 3px solid #66BEB6; padding: .15rem 0 .15rem .78rem; margin: .78rem 0; }
  .evidence-label { color: var(--teal); font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 730; }
  .evidence-text { color: var(--ink); font-size: .84rem; line-height: 1.5; margin-top: .18rem; }

  .callout { border: 1px solid #E4D6B9; border-left: 4px solid var(--amber); background: #FFF9EC; padding: .8rem .9rem; border-radius: 8px; color: #5C4A29; font-size: .82rem; line-height: 1.5; }
  .callout.info { border-color: #C9DEDA; border-left-color: var(--teal); background: #ECF7F4; color: #315356; }
  .callout.critical { border-color: #EDC7C0; border-left-color: var(--coral); background: #FFF4F2; color: #713C35; }

  [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid var(--line); }
  [data-testid="stTabs"] button { color: var(--muted); font-weight: 620; padding-left: .85rem; padding-right: .85rem; }
  [data-testid="stTabs"] button[aria-selected="true"] { color: var(--teal); }
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--teal); }
  [data-testid="stExpander"] { background: white; border-color: var(--line); border-radius: 8px; }
  [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .stDownloadButton > button { border-radius: 8px; border-color: var(--teal); color: var(--teal); font-weight: 650; }
  .stDownloadButton > button:hover { border-color: #075F62; color: #075F62; background: #ECF7F4; }

  .footer { border-top: 1px solid var(--line); margin-top: 2.2rem; padding: 1rem 0 0; color: var(--muted); font-size: .72rem; line-height: 1.55; }

  @media (max-width: 900px) {
    .pipeline { grid-template-columns: 1fr; }
    .metric-card { min-height: 122px; }
  }
</style>
"""


def safe(value: object) -> str:
    return escape(str(value), quote=True)


def badge(label: str, tone: str = "neutral") -> str:
    tone = tone if tone in {"teal", "amber", "coral", "neutral"} else "neutral"
    return f'<span class="badge badge-{tone}">{safe(label)}</span>'


def metric_card(label: str, value: str, detail: str, tone: str = "accent") -> str:
    tone_class = {
        "accent": "metric-accent",
        "warning": "metric-warning",
        "danger": "metric-danger",
        "neutral": "",
    }.get(tone, "")
    return (
        '<div class="metric-card">'
        f'<div class="metric-kicker">{safe(label)}</div>'
        f'<div class="metric-value {tone_class}">{safe(value)}</div>'
        f'<div class="metric-detail">{safe(detail)}</div>'
        '</div>'
    )


def key_value_grid(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div class="kv-key">{safe(key)}</div><div class="kv-value">{safe(value)}</div>'
        for key, value in items
    )
    return f'<div class="kv-grid">{rows}</div>'


def evidence_item(label: str, text: str) -> str:
    return (
        '<div class="evidence-item">'
        f'<div class="evidence-label">{safe(label)}</div>'
        f'<div class="evidence-text">{safe(text)}</div>'
        '</div>'
    )
