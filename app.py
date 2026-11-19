import os
"""Where AI Pays: a company's top AI use cases from a few answers. Run: streamlit run app.py"""
import html
import importlib
import io
from datetime import date

import pandas as pd
import streamlit as st

import finder as F
import kit

F = importlib.reload(F)  # Streamlit Cloud keeps old copies of imported files after an update; always use the latest
kit = importlib.reload(kit)

kit.page("Where AI Pays", "Find the AI projects that pay back first in your company", mark="compass", icon="🧭",
         meta="For owners and managers · nothing you type is stored", badge="Free · no sign-up", theme="space")

kit.demo(os.environ.get("DEMO_VIDEO", "https://janis-saulitis-portfolio.netlify.app/media/finder.mp4"), "Where AI Pays in 1 minute",
         "1. Pick your **industry** and what takes your team the most time.\n2. Roughly how much of it there is: emails, documents, invoices, customers.\n3. Read the top ideas: what each saves after running costs, when it pays back, and the risk.\n4. Open one for the first steps and the maths, or **download the one-page plan**.")

RISK = {"low": ("good", "low risk"), "medium": ("warn", "medium risk"), "high": ("bad", "high risk")}


def months(x):
    if x == float("inf"):
        return "doesn't pay back at this volume"
    return "under a month" if x < 1 else f"{x:.0f} month{'s' if round(x) != 1 else ''}"


def pdf_plan(company, industry, top, assumptions) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    for n, f in [("DV", "DejaVuSans.ttf"), ("DVB", "DejaVuSans-Bold.ttf")]:
        try:
            pdfmetrics.registerFont(TTFont(n, f"/usr/share/fonts/truetype/dejavu/{f}"))
            body, bold = "DV", "DVB"
        except Exception:
            body, bold = "Helvetica", "Helvetica-Bold"
    s = lambda size, b=False, c="#14201b": ParagraphStyle("p", fontName=bold if b else body, fontSize=size,
                                                       leading=size * 1.35, textColor=colors.HexColor(c))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=14 * mm, title="AI plan", author="Where AI Pays")
    els = [Paragraph(f"AI plan for {company or 'your company'}", s(18, True)),
           Paragraph(f"{F.INDUSTRIES[industry]} · {date.today():%d.%m.%Y}", s(9.5, c="#56645d")), Spacer(1, 5 * mm)]
    for i, r in enumerate(top, 1):
        els += [Paragraph(f"{i}. {r['name']}", s(12, True, "#1f7a57")),
                Paragraph(r["does"], s(9.5)),
                Paragraph((f"Saves about <b>{r['hours']:.0f} hours</b> a month, worth <b>€{r['monthly_value']:,.0f}</b>"
                           if r["hours"] >= 1 else f"Prevents about <b>€{r['monthly_value']:,.0f}</b> of losses a month")
                          + f"; running cost about €{r['tool_cost']:,.0f}. Setup about {r['weeks']:g} weeks "
                          f"(€{r['setup']:,.0f}), pays back in {months(r['payback_months'])}. "
                          + (r["risk_note"] if r["risk_note"].lower().startswith(r["risk"])
                             else f"{r['risk'].capitalize()} risk: {r['risk_note']}"), s(9.5)),
                Paragraph("First steps: " + " → ".join(r["steps"]), s(9.5, c="#56645d")), Spacer(1, 3.5 * mm)]
    els += [Spacer(1, 2 * mm), Paragraph("Assumptions: " + assumptions, s(8.5, c="#56645d")),
            Paragraph("Estimates are rough and meant for choosing where to start, not for budgeting. "
                      "Made with Where AI Pays · janis-saulitis-portfolio.netlify.app", s(8.5, c="#56645d"))]
    doc.build(els)
    return buf.getvalue()


layout = st.container(key="answer_first")  # on phones the answer column moves above the questions
left, right = layout.columns([5, 7], gap="large")

with left.container(border=True):
    st.markdown("#### Your company")
    company = st.text_input("Company name (optional, for the PDF)", placeholder="e.g. Baltic Freight")
    industry = st.selectbox("Industry", list(F.INDUSTRIES), format_func=F.INDUSTRIES.get, index=0)
    picked = st.multiselect("What takes your team the most time?", list(F.PAINS), format_func=lambda k: F.PAINS[k][0],
                            default=["emails", "documents", "invoices", "late_payments"])
    vols = {}
    if picked:
        st.markdown("**Roughly how much?**")
        for k in picked:
            vols[k] = st.number_input(F.PAINS[k][1], 0, 1_000_000, F.PAINS[k][2], step=max(1, F.PAINS[k][2] // 10), key=f"v_{k}")
    with st.expander("Costs and assumptions"):
        hourly = st.number_input("Cost of one hour of staff time, €", 5.0, 200.0, 15.0, 1.0,
                                 help="Salary plus taxes and overheads. Around €12–20 in the Baltics.")
        build = st.number_input("Cost of one week of setup work, €", 200.0, 10_000.0, 1_000.0, 100.0)
        adoption = st.slider("Share of the work AI actually takes over", 0.2, 1.0, 0.6, 0.05,
                             help="Rarely 100%: people still check, fix and handle the odd cases.")
        sensitive = st.toggle("We handle sensitive personal or financial data", value=industry in ("finance", "public"))

with right:
    if not vols:
        st.info("Tick at least one thing that takes your team time, and the ranking appears here.")
    else:
        res = F.assess(industry, vols, hourly, build, adoption, sensitive)
        top = res[:5]
        best = top[0]
        hours3 = sum(r["hours"] for r in top[:3])
        value3 = sum(r["net"] for r in top[:3])
        kit.answer("Where AI pays · your top three", f"€{value3:,.0f}<small> a month</small>",
                   "after running costs" + (f", plus <b>{hours3:,.0f} hours</b> of staff time freed" if hours3 >= 1 else "")
                   + f". Start with {html.escape(best['name'].lower())}: it pays back first, in {months(best['payback_months'])}.",
                   raw=True)
        st.markdown("#### Your top five")
        for i, r in enumerate(top, 1):
            with st.container(border=True):
                a, b = st.columns([3, 1])
                a.markdown(f"<span class='k-rank'>{i}</span>&nbsp;&nbsp;<b style='font-size:16.5px'>{html.escape(r['name'])}</b>",
                           unsafe_allow_html=True)
                b.markdown(f"<div style='text-align:right'><span class='k-chip {RISK[r['risk']][0]}'>{RISK[r['risk']][1]}</span></div>", unsafe_allow_html=True)
                gain = (f"Saves **{r['hours']:,.0f} h** a month" if r["hours"] >= 1
                        else f"Prevents about **€{r['monthly_value']:,.0f}** of losses a month")
                st.markdown(f"{gain} · **€{r['net']:,.0f}** a month after costs · "
                            f"pays back in **{months(r['payback_months'])}**")
                with st.expander("What it does and how to start"):
                    st.markdown(r["does"])
                    st.markdown("**First steps**\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(r["steps"], 1)))
                    st.caption(f"Risk: {r['risk_note']}")
                    st.caption(f"Maths: {r['units']:,.0f} a month × {r['minutes']:g} min × {adoption:.0%} taken over = "
                               f"{r['hours']:,.0f} h × €{hourly:g}"
                               + (f" + money saved directly" if r["key"] == "risk" else "")
                               + f" − €{r['tool_cost']:g} running cost. Setup {r['weeks']:g} weeks × €{build:,.0f}.")
                    if r["proof"]:
                        st.markdown(f"See one working: [{r['proof'][0]}]({r['proof'][1]})")
        assumptions = (f"staff hour €{hourly:g}, setup week €{build:,.0f}, AI takes over {adoption:.0%} of the work"
                       + ("; sensitive data handled" if sensitive else ""))
        st.download_button("Download the one-page plan (PDF)", pdf_plan(company, industry, top, assumptions),
                           file_name="ai-plan.pdf", mime="application/pdf", type="primary")
        if len(res) > 5:
            with st.expander(f"The other {len(res) - 5} options"):
                kit.table([{"u": r["name"], "h": f"{r['hours']:,.0f} h", "v": f"€{r['net']:,.0f}", "p": months(r["payback_months"]),
                            "r": r["risk"]} for r in res[5:]],
                          [kit.col("Use case", "u", "strong"), kit.col("Hours a month", "h", "num"),
                           kit.col("€ a month after costs", "v", "num"), kit.col("Pays back in", "p", "muted"),
                           kit.col("Risk", "r", "chip", {"low": "good", "medium": "warn", "high": "bad"})])

kit.footer("finder.py · every estimate shows its maths")
