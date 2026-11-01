"""
broke.ly — Student Expense Analyzer
Run locally:  streamlit run app.py
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analyzer import ParseError, inr, parse_input, personality, report_text, suggest, summarize

ROOT = Path(__file__).parent
SAMPLES = {
    "October month (CSV)": ROOT / "sample_data" / "october_expenses.csv",
    "Messy notes (text)": ROOT / "sample_data" / "quick_notes.txt",
    "Hostel foodie (CSV with categories)": ROOT / "sample_data" / "hostel_foodie.csv",
    "Weekend shopper (CSV)": ROOT / "sample_data" / "weekend_shopper.csv",
    "Tight budget day scholar (text)": ROOT / "sample_data" / "tight_budget_notes.txt",
    "Subscription hoarder (text)": ROOT / "sample_data" / "subscription_hoarder.txt",
    "Bank export, semicolons (CSV)": ROOT / "sample_data" / "semicolon_bank_export.csv",
}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB

INK = "#111111"
PALETTE = {
    "Food & Dining": "#FF6FB5", "Rent & Bills": "#7DD3FC", "Transport": "#FFB020",
    "Shopping": "#B8FF3B", "Entertainment": "#C4A1FF", "Groceries": "#4DE1C1",
    "Education": "#FFE45C", "Health & Fitness": "#FF7A7A", "Personal Care": "#FFB38A",
    "Others": "#D4D4D4",
}
EXTRA = ["#A0E7E5", "#FBE7C6", "#B4F8C8", "#FFAEBC", "#E0BBE4"]

st.set_page_config(page_title="broke.ly · Student Expense Analyzer", page_icon="💸",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Styles (neo-brutalist: cream paper, thick ink borders, hard shadows)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap');
:root { --ink:#111; --paper:#FFF6D6; --pink:#FF6FB5; --lime:#B8FF3B; --sky:#7DD3FC; --amber:#FFB020; --lilac:#C4A1FF; }
html, body, .stApp, [class*="st-"], p, li, label, input, textarea, button { font-family:'Space Grotesk', sans-serif !important; }
.material-symbols-rounded, [data-testid="stIconMaterial"], span[class*="material"] { font-family:'Material Symbols Rounded' !important; }
.stApp { background-color:var(--paper); background-image:radial-gradient(#11111122 1px, transparent 1px); background-size:22px 22px; color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stAppDeployButton"] { visibility:hidden; }
.block-container { max-width:1150px; padding-top:1.6rem; padding-bottom:3rem; }
h1, h2, h3, .display { font-family:'Archivo Black', sans-serif !important; color:var(--ink); letter-spacing:-.5px; }

/* buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  background:var(--lime); color:var(--ink); border:3px solid var(--ink); border-radius:12px;
  box-shadow:5px 5px 0 var(--ink); font-weight:700; padding:.55rem 1.3rem; transition:all .12s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { transform:translate(-2px,-2px); box-shadow:7px 7px 0 var(--ink); color:var(--ink); border-color:var(--ink); background:var(--lime); }
.stButton > button:active, .stDownloadButton > button:active { transform:translate(3px,3px); box-shadow:2px 2px 0 var(--ink); }
.stButton > button[kind="secondary"], [data-testid="stBaseButton-secondary"] { background:#fff; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] { background:var(--pink) !important; font-size:1.05rem; }
.stButton > button:focus-visible { outline:3px solid var(--sky); outline-offset:3px; }

/* inputs */
[data-testid="stFileUploaderDropzone"] { background:#fff; border:3px dashed var(--ink); border-radius:16px; }
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div {
  border:3px solid var(--ink) !important; border-radius:12px !important; box-shadow:4px 4px 0 var(--ink); background:#fff !important; }
textarea, input { color:var(--ink) !important; background:#fff !important; }
[data-testid="stRadio"] [role="radiogroup"] { gap:.6rem; flex-wrap:wrap; }
[data-testid="stRadio"] [role="radiogroup"] > label { background:#fff; border:3px solid var(--ink); border-radius:999px; padding:.35rem .95rem; box-shadow:3px 3px 0 var(--ink); margin:0; }
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { background:var(--amber); }
[data-testid="stWidgetLabel"] p { font-weight:700; font-size:1rem; }
[data-testid="stAlert"] { border:3px solid var(--ink); border-radius:14px; box-shadow:4px 4px 0 var(--ink); }
[data-testid="stExpander"] details { border:3px solid var(--ink); border-radius:14px; background:#fff; box-shadow:4px 4px 0 var(--ink); }
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] { border:3px solid var(--ink); border-radius:16px; background:#fff; box-shadow:5px 5px 0 var(--ink); overflow:hidden; padding:4px; }

/* custom blocks */
.nav { display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem; }
.logo { font-family:'Archivo Black'; font-size:1.6rem; }
.logo span { background:var(--pink); border:3px solid var(--ink); padding:0 .35rem; margin-left:2px; box-shadow:3px 3px 0 var(--ink); }
.pill { background:#fff; border:3px solid var(--ink); border-radius:999px; padding:.25rem .8rem; font-weight:700; font-size:.85rem; box-shadow:3px 3px 0 var(--ink); }
.hero h1 { font-size:clamp(2.2rem, 6vw, 4.2rem); line-height:1.02; margin:0 0 .6rem; }
.hero .hl { background:var(--lime); padding:0 .3rem; border:3px solid var(--ink); display:inline-block; transform:rotate(-1.5deg); }
.hero p { font-size:1.15rem; max-width:640px; margin:0; }
.marquee { overflow:hidden; border-top:3px solid var(--ink); border-bottom:3px solid var(--ink); background:var(--ink); color:var(--paper); margin:1.6rem 0; padding:.45rem 0; white-space:nowrap; }
.marquee div { display:inline-block; animation:scroll 28s linear infinite; font-family:'Archivo Black'; font-size:1rem; letter-spacing:1px; }
@keyframes scroll { from { transform:translateX(0) } to { transform:translateX(-50%) } }
.section { font-family:'Archivo Black'; font-size:1.5rem; margin:2rem 0 .8rem; display:flex; align-items:center; gap:.6rem; }
.section .num { background:var(--ink); color:var(--paper); border-radius:10px; padding:.05rem .55rem; font-size:1rem; }
.stats { display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:16px; margin-bottom:1.4rem; }
.stat { border:3px solid var(--ink); border-radius:16px; padding:1rem 1.1rem; box-shadow:5px 5px 0 var(--ink); background:#fff; }
.stat .k { font-size:.85rem; font-weight:700; text-transform:lowercase; opacity:.75; }
.stat .v { font-family:'Archivo Black'; font-size:1.9rem; line-height:1.15; word-break:break-word; }
.stat .s { font-size:.85rem; margin-top:.15rem; }
.persona { border:3px solid var(--ink); border-radius:18px; background:var(--lilac); padding:1.2rem 1.4rem; box-shadow:6px 6px 0 var(--ink); margin-bottom:1.4rem; display:flex; gap:1.1rem; align-items:center; flex-wrap:wrap; }
.persona .tag { background:var(--ink); color:#fff; border-radius:999px; padding:.15rem .7rem; font-size:.8rem; font-weight:700; }
.persona .name { font-family:'Archivo Black'; font-size:1.7rem; line-height:1.1; margin:.35rem 0 .2rem; }
.persona .emoji { font-size:3rem; border:3px solid var(--ink); background:#fff; border-radius:16px; width:84px; height:84px; display:flex; align-items:center; justify-content:center; box-shadow:4px 4px 0 var(--ink); transform:rotate(-4deg); }
.bar-row { margin:.55rem 0; }
.bar-top { display:flex; justify-content:space-between; font-weight:700; font-size:.95rem; }
.bar-track { height:18px; border:3px solid var(--ink); border-radius:8px; background:#fff; overflow:hidden; margin-top:3px; }
.bar-fill { height:100%; border-right:3px solid var(--ink); }
.tips { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px; }
.tip { border:3px solid var(--ink); border-radius:16px; padding:1rem 1.1rem; box-shadow:5px 5px 0 var(--ink); background:#fff; }
.tip.alert { background:#FFD1D1; } .tip.win { background:#E4FFC2; } .tip.tip { background:#FFF0C2; }
.tip .t { font-weight:700; font-size:1.05rem; margin:.35rem 0 .3rem; }
.tip .b { font-size:.95rem; line-height:1.45; }
.tip .badge { display:inline-block; border:2px solid var(--ink); border-radius:999px; padding:0 .55rem; font-size:.75rem; font-weight:700; background:#fff; }
.empty { border:3px dashed var(--ink); border-radius:18px; padding:2rem; text-align:center; background:#ffffffaa; }
.foot { text-align:center; margin-top:3rem; font-weight:500; opacity:.8; }
@media (max-width: 640px) { .stat .v { font-size:1.5rem; } .persona .name { font-size:1.35rem; } }
</style>
""", unsafe_allow_html=True)


def h(text) -> str:
    """Escape user text before putting it in HTML."""
    return html.escape(str(text))


def section(num: int, title: str) -> None:
    st.markdown(f'<div class="section"><span class="num">{num:02d}</span>{h(title)}</div>', unsafe_allow_html=True)


def show_chart(fig) -> None:
    """Plotly chart that works on both newer and older Streamlit versions."""
    cfg = {"displayModeBar": False, "responsive": True}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg)


def show_table(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True)


def colors_for(categories) -> dict:
    out, i = {}, 0
    for c in categories:
        if c in PALETTE:
            out[c] = PALETTE[c]
        else:
            out[c] = EXTRA[i % len(EXTRA)]
            i += 1
    return out


def style_fig(fig, height=360):
    fig.update_layout(
        height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Space Grotesk, sans-serif", color=INK, size=14),
        margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=INK, font=dict(color=INK, family="Space Grotesk")),
    )
    return fig


def read_upload(upload) -> str:
    data = upload.getvalue()
    if len(data) > MAX_BYTES:
        raise ParseError("That file is over 2 MB. Upload one month of expenses as CSV or TXT.")
    if not data.strip():
        raise ParseError("That file is empty. Add at least one expense and upload again.")
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            if "\x00" not in text:
                return text
        except UnicodeDecodeError:
            continue
    raise ParseError("Couldn't read the file's text. Save it as a plain CSV (UTF-8) and try again.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="nav"><div class="logo">broke<span>.ly</span></div><div class="pill">student expense analyzer</div></div>
<div class="hero">
  <h1>where did my<br><span class="hl">money go??</span></h1>
  <p>Drop your monthly expenses as a CSV or messy notes. We'll sort the spending, find the leaks,
  and give you budget tips that don't sound like your parents.</p>
</div>
<div class="marquee"><div>
FOOD ✦ RENT ✦ TRAVEL ✦ SHOPPING ✦ SUBSCRIPTIONS ✦ CHAI ✦ MAGGI ✦ METRO ✦ BOOKS ✦ MOVIES ✦
FOOD ✦ RENT ✦ TRAVEL ✦ SHOPPING ✦ SUBSCRIPTIONS ✦ CHAI ✦ MAGGI ✦ METRO ✦ BOOKS ✦ MOVIES ✦
</div></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 01 Input
# ---------------------------------------------------------------------------
section(1, "add your expenses")

mode = st.radio("How do you want to add them?", ["Upload a file", "Paste text", "Try sample data"],
                horizontal=True, key="mode")

raw_text, filename, upload = None, None, None
left, right = st.columns([3, 2], gap="large")

with left:
    if mode == "Upload a file":
        upload = st.file_uploader("Upload a CSV or TXT file", type=["csv", "txt"],
                                  help="CSV needs an amount column. Description, date and category columns are optional.")
        if upload is not None:
            filename = upload.name
    elif mode == "Paste text":
        raw_text = st.text_area(
            "One expense per line", height=220, key="pasted",
            placeholder="05/10/2026 Swiggy dinner 250\nUber to college ₹120\nNetflix 199\nRent 6500",
        )
        filename = "pasted.txt"
    else:
        choice = st.selectbox("Pick a sample", list(SAMPLES))
        filename = SAMPLES[choice].name
        raw_text = SAMPLES[choice].read_text(encoding="utf-8")
        st.caption("Preview of the first lines:")
        st.code("\n".join(raw_text.splitlines()[:7]), language=None)

with right:
    budget = st.number_input("Monthly budget in ₹ (optional)", min_value=0, max_value=10_000_000,
                             value=0, step=500, help="Leave it at 0 to skip the budget check.")
    st.markdown("""
<div class="stat" style="background:#fff;box-shadow:4px 4px 0 #111">
<div class="k">formats that work</div>
<div class="s" style="line-height:1.6">
<b>CSV:</b> Date, Description, Amount (Category optional)<br>
<b>Text:</b> <code>Swiggy 250</code> · <code>05/10 Uber ₹120</code> · <code>Rent - 6500/-</code>
</div></div>""", unsafe_allow_html=True)

c1, c2, _ = st.columns([1.3, 1, 3])
analyze = c1.button("Analyze my spending ⚡", type="primary")
if c2.button("Clear", type="secondary"):
    for k in ("result", "pasted"):
        st.session_state.pop(k, None)
    st.rerun()

if analyze:
    try:
        if mode == "Upload a file":
            if upload is None:
                raise ParseError("Choose a CSV or TXT file first.")
            if not upload.name.lower().endswith((".csv", ".txt")):
                raise ParseError("Only .csv and .txt files are supported.")
            raw_text = read_upload(upload)
        if not raw_text or not raw_text.strip():
            raise ParseError("Add some expenses first: upload a file, paste text, or try a sample.")
        result = parse_input(raw_text, filename)
        st.session_state["result"] = {"df": result.df, "warnings": result.warnings,
                                      "budget": float(budget) if budget else None, "source": filename}
    except ParseError as e:
        st.session_state.pop("result", None)
        st.error(str(e).replace("\n", "  \n"), icon="🚫")
    except Exception as e:  # last-resort safety net so the app never shows a stack trace
        st.session_state.pop("result", None)
        st.error(f"Something went wrong while reading that data ({type(e).__name__}). "
                 "Check the format and try again.", icon="🚫")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
res = st.session_state.get("result")
if not res:
    st.markdown('<div class="empty" style="margin-top:2rem"><div class="display" style="font-size:1.4rem">'
                'your dashboard shows up here ↓</div><div>Pick an input above and hit analyze.</div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="foot">built with vibe coding · Streamlit + Claude · made for broke students 💸</div>',
                unsafe_allow_html=True)
    st.stop()

df: pd.DataFrame = res["df"]
s = summarize(df, res["budget"])
tips = suggest(s)
p_name, p_line = personality(s)

if res["warnings"]:
    with st.expander(f"⚠️ {len(res['warnings'])} note(s) about your data"):
        for w in res["warnings"]:
            st.markdown(f"- {w}")

# 02 Overview -----------------------------------------------------------------
section(2, "the damage report")

budget_card = ""
if s["budget"]:
    left_amt = s["budget"] - s["total"]
    used = s["total"] / s["budget"] * 100
    bg = "#FFD1D1" if left_amt < 0 else "#E4FFC2"
    label = "over budget" if left_amt < 0 else "left in budget"
    budget_card = (f'<div class="stat" style="background:{bg}"><div class="k">{label}</div>'
                   f'<div class="v">{inr(abs(left_amt))}</div><div class="s">{used:.0f}% of {inr(s["budget"])} used</div></div>')
else:
    budget_card = (f'<div class="stat" style="background:#E4FFC2"><div class="k">needs vs wants</div>'
                   f'<div class="v">{s["needs"] / s["total"] * 100:.0f} / {s["wants"] / s["total"] * 100:.0f}</div>'
                   f'<div class="s">% of spending (target 50 / 30)</div></div>')

period = ""
if s["has_dates"]:
    a, b = s["period"]
    period = f"{a:%d %b} – {b:%d %b %Y}"

st.markdown(f"""
<div class="stats">
  <div class="stat" style="background:#FFD6EC"><div class="k">total spent</div><div class="v">{inr(s['total'])}</div>
    <div class="s">{s['count']} expenses{' · ' + period if period else ''}</div></div>
  <div class="stat" style="background:#D6F1FF"><div class="k">biggest category</div><div class="v">{h(s['top_category'])}</div>
    <div class="s">{s['top_share']:.0f}% of your money</div></div>
  <div class="stat" style="background:#FFF0C2"><div class="k">{'avg per day' if s['has_dates'] else 'avg per expense'}</div>
    <div class="v">{inr(s['daily_average'] if s['has_dates'] else s['average'])}</div>
    <div class="s">largest: {h(str(s['largest']['description'])[:28])} ({inr(s['largest']['amount'])})</div></div>
  {budget_card}
</div>
""", unsafe_allow_html=True)

EMOJI = {"The Foodie": "🍜", "The Subscription Collector": "📺", "The Weekend Warrior": "🎉",
         "The Cart Addict": "🛒", "The Main Character": "🎬", "The Road Runner": "🛺",
         "The Chai-and-Snacks Spender": "☕", "The Responsible Adult": "🧠",
         "The Balanced Budgeter": "⚖️", "The Overdraft Speedrunner": "🔥"}
st.markdown(f"""
<div class="persona"><div class="emoji">{EMOJI.get(p_name, '💸')}</div>
<div><span class="tag">your spending personality</span><div class="name">{h(p_name)}</div><div>{h(p_line)}</div></div></div>
""", unsafe_allow_html=True)

# 03 Categories -----------------------------------------------------------------
section(3, "where it went")
by_cat = s["by_category"]
cmap = colors_for(by_cat["category"])

col_a, col_b = st.columns([1, 1], gap="large")
with col_a:
    donut = go.Figure(go.Pie(
        labels=by_cat["category"], values=by_cat["total"], hole=.55, sort=False,
        marker=dict(colors=[cmap[c] for c in by_cat["category"]], line=dict(color=INK, width=3)),
        textinfo="percent", textfont=dict(family="Archivo Black", size=13, color=INK),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} · %{percent}<extra></extra>",
    ))
    donut.add_annotation(text=f"<b>{inr(s['total'])}</b><br>total", showarrow=False,
                         font=dict(family="Archivo Black", size=18, color=INK))
    show_chart(style_fig(donut, 380))
with col_b:
    bars = "".join(
        f'<div class="bar-row"><div class="bar-top"><span>{h(r.category)} · {int(r.transactions)}</span>'
        f'<span>{inr(r.total)} · {r.share:.0f}%</span></div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{max(r.share, 2):.1f}%;background:{cmap[r.category]}"></div></div></div>'
        for r in by_cat.itertuples()
    )
    st.markdown(f'<div class="stat" style="padding:1rem 1.2rem">{bars}</div>', unsafe_allow_html=True)

# 04 Patterns ---------------------------------------------------------------------
section(4, "spending patterns")
if s["has_dates"]:
    daily = s["daily"].reset_index()
    daily.columns = ["day", "amount"]
    fig = px.bar(daily, x="day", y="amount")
    fig.update_traces(marker_color="#FFB020", marker_line_color=INK, marker_line_width=2,
                      hovertemplate="%{x|%d %b}<br>₹%{y:,.0f}<extra></extra>")
    fig.add_hline(y=s["daily_average"], line_dash="dash", line_color=INK, line_width=2,
                  annotation_text=f"avg {inr(s['daily_average'])}", annotation_position="top left")
    fig.update_xaxes(title=None, showgrid=False, linecolor=INK, linewidth=3, tickformat="%d %b")
    fig.update_yaxes(title=None, gridcolor="#EEE", tickprefix="₹", linecolor=INK, linewidth=3)
    show_chart(style_fig(fig, 320))
    if s["dates_reliable"]:
        st.markdown(f"**Weekends** took **{s['weekend_share']:.0f}%** of your spending. "
                    f"Your biggest day was **{s['peak_day']:%A, %d %b}** at **{inr(s['peak_day_amount'])}**.")
else:
    st.info("Add dates to your expenses to see a day-by-day chart.", icon="📅")

top_col, small_col = st.columns([3, 2], gap="large")
with top_col:
    st.markdown("**Top 5 biggest expenses**")
    top = s["top_expenses"].copy()
    if "date" in top.columns:
        top["date"] = pd.to_datetime(top["date"]).dt.strftime("%d %b").fillna("—")
    top["amount"] = top["amount"].map(inr)
    top.columns = [c.title() for c in top.columns]
    show_table(top)
with small_col:
    st.markdown("**Small stuff adds up**")
    st.markdown(f"""<div class="stat" style="background:#FFF0C2">
<div class="k">buys under ₹100</div><div class="v">{s['small_count']}× = {inr(s['small_total'])}</div>
<div class="s">{s['small_total'] / s['total'] * 100:.0f}% of total spending</div></div>""", unsafe_allow_html=True)
    subs = ", ".join(h(x) for x in s["subscriptions"]) or "none found"
    st.markdown(f"""<div class="stat" style="background:#EDE3FF;margin-top:16px">
<div class="k">subscriptions</div><div class="s" style="font-size:1rem;font-weight:700">{subs}</div></div>""",
                unsafe_allow_html=True)

# 05 Suggestions ------------------------------------------------------------------
section(5, "glow-up tips for your wallet")
BADGE = {"alert": "🚨 fix this", "tip": "💡 try this", "win": "✅ nice"}
st.markdown('<div class="tips">' + "".join(
    f'<div class="tip {t["tone"]}"><span class="badge">{BADGE[t["tone"]]}</span>'
    f'<div class="t">{h(t["title"])}</div><div class="b">{h(t["body"])}</div></div>'
    for t in tips) + "</div>", unsafe_allow_html=True)

# 06 Data + downloads ---------------------------------------------------------------
section(6, "your categorized data")
with st.expander(f"See all {len(df)} expenses"):
    view = df.copy()
    if "date" in view.columns:
        view["date"] = pd.to_datetime(view["date"]).dt.strftime("%d %b %Y").fillna("—")
    cols = [c for c in ["date", "description", "category", "amount"] if c in view.columns]
    show_table(view[cols].rename(columns=str.title))

d1, d2, _ = st.columns([1.2, 1.2, 2])
export = df.copy()
if "date" in export.columns:
    export["date"] = pd.to_datetime(export["date"]).dt.strftime("%Y-%m-%d")
d1.download_button("Download CSV ⬇", export.to_csv(index=False).encode("utf-8"),
                   file_name="categorized_expenses.csv", mime="text/csv")
d2.download_button("Download report ⬇", report_text(s, tips).encode("utf-8"),
                   file_name="expense_report.txt", mime="text/plain")

st.markdown('<div class="foot">built with vibe coding · Streamlit + Claude · made for broke students 💸</div>',
            unsafe_allow_html=True)
