"""The visual product story, followed by the real Scout investigation.

I use five short visual stages to introduce the problem, information and
build decisions. Detailed EDA and results remain in Evidence & charts.
The speaker script lives in a separate document.
"""
from html import escape
from pathlib import Path

import streamlit as st

from src.scout_pitch_story import JOURNEY, TOTAL_CHAPTERS

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Scout · Product pitch", page_icon="🧭", layout="wide")

st.markdown("""
<style>
.stApp {background:radial-gradient(circle at 90% 0%,#243e36 0%,#111c1b 38%,#101719 75%);color:#eff5ef;}
.block-container {max-width:1240px;padding-top:1.1rem;padding-bottom:2rem;}
.pitch-kicker {color:#a9cfb9;font-size:.72rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;}
.pitch-head {font-size:clamp(2.1rem,3.8vw,3.5rem);font-weight:780;letter-spacing:-.045em;line-height:1.08;color:#f4f8f4;margin:7px 0;}
.pitch-sub {color:#c4d6cc;font-size:1.04rem;margin:0 0 10px;}
.path {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px;margin:10px 0 16px;}
.path-item {border-top:3px solid #38574b;background:#1c2b29;padding:9px 11px;border-radius:0 0 9px 9px;color:#aec2b6;font-size:.85rem;}
.path-item.active {border-color:#d4e994;background:#344c3a;color:#f4f8ed;font-weight:750;}
.path-item.done {border-color:#77a68b;color:#dbe9df;}
.path-item small {display:block;font-size:.67rem;letter-spacing:.08em;opacity:.85;margin-bottom:4px;}
.stage-head {font-size:clamp(1.65rem,2.8vw,2.6rem);font-weight:760;letter-spacing:-.028em;line-height:1.1;color:#f4f8f3;margin:6px 0 9px;}
.story-explain {color:#d6e4da;line-height:1.48;font-size:1.03rem;margin:0 0 12px;}
.panel {border:1px solid #3c5b50;border-radius:15px;background:#192a29;padding:19px;color:#e8f1e9;}
.panel h3 {font-size:1.12rem;margin:5px 0 9px;color:#e5f2e4;}
.panel p {font-size:1rem;color:#cbd9ce;line-height:1.45;margin:5px 0;}
.decision {background:#293e32;border-left:4px solid #d4e994;border-radius:0 10px 10px 0;padding:13px 17px;color:#ecf4e5;margin:14px 0 8px;line-height:1.45;font-size:1.03rem;}
.decision b {color:#e0efb0;}
.big-number {font-size:clamp(2.3rem,4.4vw,4.2rem);font-weight:800;line-height:1.06;color:#d4e994;letter-spacing:-.055em;}
.muted {font-size:.91rem;color:#becfc3;line-height:1.4;}
.checkout {background:#e9efea;border-radius:12px;padding:17px;color:#172522;border:1px solid #bdd0bd;}
.checkout .window {font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:#536961;font-weight:700;border-bottom:1px solid #ccd9cf;padding-bottom:10px;}
.checkout .product {display:flex;justify-content:space-between;margin:18px 0;font-size:1rem;font-weight:650;}
.checkout .pay {background:#2c5444;color:white;border-radius:7px;text-align:center;padding:11px;font-weight:700;}
.checkout .error {margin-top:12px;border:1px solid #b36d5e;background:#f9e3d8;color:#6d2f24;border-radius:7px;padding:11px;font-weight:700;}
.clue {padding:10px 0;border-bottom:1px solid #38534a;line-height:1.45;}
.clue:last-child {border-bottom:0;}
.clue b {color:#dcebdd;}
.track {height:13px;background:#34443b;border-radius:10px;overflow:hidden;margin:11px 0;}
.track span {display:block;height:100%;background:#d1e795;}
.compare {display:grid;grid-template-columns:1fr 1fr;gap:11px;}
.result-box {background:#1a2d2a;border:1px solid #416356;padding:15px;border-radius:12px;}
.result-box .big-number {font-size:2.6rem;}
.bad {border-color:#ae7868;background:#382b28;}
.bad .big-number {color:#f0b09b;}
.arrow {color:#b9d8a0;font-size:1.7rem;font-weight:750;text-align:center;margin:1px;}
.pipeline {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0;}
.pipe {border:1px solid #527762;background:#263e33;border-radius:12px;padding:13px 12px;min-height:110px;}
.pipe b {display:block;color:#d5eab6;font-size:1.04rem;margin:6px 0;}
.pipe p {color:#d0ddd0;font-size:.9rem;line-height:1.4;margin:0;}
.optional {border:1px dashed #729080;border-radius:10px;color:#c8dacc;padding:10px 14px;font-size:.95rem;margin:10px 0;}
.roadmap {border:1px solid #3c5d4e;background:#1a2c28;border-radius:14px;padding:20px;min-height:180px;}
.roadmap b {font-size:1.15rem;color:#d0e7a5;}
.roadmap p {color:#d1e0d4;line-height:1.5;}
@media(max-width:760px){.path-item{font-size:.7rem;padding:8px 4px}.pipeline{grid-template-columns:1fr 1fr}.compare{grid-template-columns:1fr}.pitch-head{font-size:2.05rem}}
</style>
""", unsafe_allow_html=True)

# The chapter number is separate from the section radio. Changing it does
# not alter the selected case or any saved investigation in SQLite.
if "scout_pitch_section" not in st.session_state:
    st.session_state["scout_pitch_section"] = "Intro to Scout"
if "scout_pitch_chapter" not in st.session_state:
    st.session_state["scout_pitch_chapter"] = 0

st.markdown(
    '<div class="pitch-kicker">SCOUT / INTRODUCTION</div>'
    '<div class="pitch-head">From a problem to a useful next decision.</div>'
    '<div class="pitch-sub">Why I built Scout, what I included and how it helps.</div>',
    unsafe_allow_html=True,
)
section = st.radio(
    "Presentation section", ["Intro to Scout", "Beyond the prototype"],
    key="scout_pitch_section", horizontal=True, label_visibility="collapsed",
)


def html(text: str) -> None:
    """Display static presentation content; no search or model call."""
    st.markdown(text, unsafe_allow_html=True)


if section == "Intro to Scout":
    chapter = min(max(int(st.session_state["scout_pitch_chapter"]), 0), TOTAL_CHAPTERS - 1)
    stage = JOURNEY[chapter]

    # Build one progress tile per milestone. Escape text before placing it
    # in HTML, so labels remain text rather than becoming markup.
    nodes = []
    for i, point in enumerate(JOURNEY):
        state = ""
        if i == chapter:
            state = "active"
        elif i < chapter:
            state = "done"
        nodes.append(
            '<div class="path-item ' + state + '"><small>'
            + str(i + 1).zfill(2) + ' / 05</small>'
            + escape(point["label"]) + '</div>'
        )
    html('<div class="path">' + "".join(nodes) + '</div>')
    html('<div class="pitch-kicker">' + escape(stage["kicker"]) + '</div>'
         '<div class="stage-head">' + escape(stage["heading"]) + '</div>'
         '<p class="story-explain">' + escape(stage["example"]) + '</p>')

    # I keep the detail on the evidence page so I can tell the product
    # story in a couple of minutes before the demo.
    if chapter == 0:
        a, b = st.columns([1, 1.3], gap="large")
        with a:
            html('<div class="checkout"><div class="window">Fictional online shop</div>'
                 '<div class="product"><span>Your basket</span><span>€34.00</span></div>'
                 '<div class="pay">Complete order</div>'
                 '<div class="error">504 · Checkout timed out<br><small>Order not completed</small></div></div>')
        with b:
            html('<div class="panel"><h3>What the team actually knows</h3>'
                 '<div class="clue"><b>What happened?</b> Customers cannot complete some orders.</div>'
                 '<div class="clue"><b>What caused it?</b> Unknown.</div>'
                 '<div class="clue"><b>Where do we start?</b> A useful first check, not a confident guess.</div></div>')
            st.caption("The intended user is an IT support investigator. The shop is a fictional example.")
    elif chapter == 1:
        a, b = st.columns(2, gap="large")
        with a:
            html('<div class="panel"><div class="pitch-kicker">Historical evidence</div>'
                 '<div class="big-number">41,000+</div><h3>Published incidents · SevAnalysis</h3>'
                 '<p>Real reported problems from many technology providers.</p>'
                 '<p><b>How I use them:</b> search descriptions and retain the original source links. Similar incidents are leads, not proof of the same cause.</p></div>')
        with b:
            html('<div class="panel"><div class="pitch-kicker">Technical knowledge</div>'
                 '<h3>Official documentation</h3>'
                 '<p>Microsoft, PostgreSQL, Kubernetes, AWS, MDN and other official sources.</p>'
                 '<p><b>How I use it:</b> short reference cards and six checked investigation guides explain what to check, how to check it and what the finding might mean.</p></div>')
        st.caption("SevAnalysis is CC BY-NC 4.0. My technical references link to the original documentation.")
    elif chapter == 2:
        a, b = st.columns(2, gap="large")
        with a:
            html('<div class="panel"><div class="pitch-kicker">My original idea</div>'
                 '<h3>Find the evidence → give it to Llama</h3>'
                 '<div class="big-number">#1</div><p>The expected Azure and HeyGen reports were ranked first.</p></div>')
        with b:
            html('<div class="panel bad"><div class="pitch-kicker">What happened in testing</div>'
                 '<h3>Correct evidence → incorrect response</h3>'
                 '<div class="big-number">No match.</div><p>The model still denied finding the expected report. It also produced unsupported advice in a separate practical test.</p></div>')
        st.caption("Observed examples; model wording paraphrased. Raw Llama results are provisional; full evaluation is in Evidence & charts.")
    elif chapter == 3:
        html('<div class="pipeline">'
             '<div class="pipe">01<b>Describe</b><p>Tell Scout what is going wrong.</p></div>'
             '<div class="pipe">02<b>Find & check</b><p>Retrieve sources and a reviewed next step.</p></div>'
             '<div class="pipe">03<b>Investigate</b><p>Record the result; move to the next relevant check.</p></div>'
             '<div class="pipe">04<b>Remember</b><p>SQLite saves the case, evidence and human review.</p></div>'
             '</div><div class="optional"><b>Optional AI interpretation:</b> Llama can help explore possible explanations. It is separate from the checked instructions and cannot verify its own answer.</div>')
        html('<div class="panel"><h3>Why the case matters</h3><p>In a real incident I do not ask one question, get an answer and go home. I investigate, record what I found and change my thinking. Scout keeps that journey together under one unique case ID.</p></div>')
    else:
        a, b = st.columns(2, gap="large")
        with a:
            html('<div class="panel"><div class="pitch-kicker">What Scout can do</div>'
                 '<h3>Help the person investigating</h3>'
                 '<div class="clue">Find published incidents and explain useful technical checks.</div>'
                 '<div class="clue">Keep findings, change the next step and build a traceable case.</div>'
                 '<div class="clue">Record human verification and evidence of recovery.</div></div>')
        with b:
            html('<div class="panel"><div class="pitch-kicker">What I left out at this stage</div>'
                 '<h3>Autonomous incident management</h3>'
                 '<div class="clue">No access to live company systems.</div>'
                 '<div class="clue">No automatic fixes or independent root-cause verification.</div>'
                 '<div class="clue">No claim of measured business savings or production readiness.</div></div>')
        st.caption("Working local prototype. Next: let’s investigate the shop that cannot complete its orders.")
    html('<div class="decision"><b>My decision → </b>' + escape(stage["decision"]) + '</div>')

    previous, following, live = st.columns([1, 1.2, 1.5], gap="small")
    with previous:
        if st.button("← Previous", key="pitch_previous", disabled=chapter == 0, use_container_width=True):
            st.session_state["scout_pitch_chapter"] = chapter - 1
            st.rerun()
    with following:
        if st.button("Next turning point →", key="pitch_next", disabled=chapter == TOTAL_CHAPTERS - 1, use_container_width=True):
            st.session_state["scout_pitch_chapter"] = chapter + 1
            st.rerun()
    with live:
        if st.button("▶ Enter the live Scout demo", key="pitch_enter_live", type="primary", use_container_width=True):
            st.session_state["scout_pitch_mode"] = True
            st.switch_page("pages/Scout.py")
else:
    st.markdown("### Act 3 · From prototype to product")
    html('<div class="stage-head">The opportunity: better decisions when something breaks.</div>'
         '<p class="story-explain">The prototype works as a local investigation aid. The commercial value is the next question to test.</p>')
    a, b, c = st.columns(3, gap="medium")
    with a:
        html('<div class="roadmap"><div class="pitch-kicker">01 / FIRST</div><b>Prove usefulness</b>'
             '<p>Test with real incident teams on fresh, independently reviewed cases. Measure relevance and time to a useful decision.</p></div>')
    with b:
        html('<div class="roadmap"><div class="pitch-kicker">02 / THEN</div><b>Build for real operations</b>'
             '<p>Secure access, shared case records, ticketing and monitoring integrations, and commercial data rights.</p></div>')
    with c:
        html('<div class="roadmap"><div class="pitch-kicker">03 / FINALLY</div><b>Test the business case</b>'
             '<p>Run a pilot. Compare effort, missed evidence and investigation outcomes with existing practice.</p></div>')
    html('<div class="decision"><b>The next step is not more AI.</b> It is proving that better evidence and a clear decision trail make investigations more effective.</div>')
    st.caption("No customer ROI, commercial traction or production security has been established. SevAnalysis is CC BY-NC 4.0.")

    def return_to_journey() -> None:
        # Callbacks run before Streamlit creates the radio widget.
        st.session_state["scout_pitch_section"] = "Intro to Scout"
        st.session_state["scout_pitch_chapter"] = 0

    st.button("← Back to Intro to Scout", key="pitch_return_journey", on_click=return_to_journey)

# I retain the original measured charts as supporting evaluation evidence.
with st.expander("Measured evidence · evaluation results", expanded=False):
    l, r = st.columns(2, gap="large")
    with l:
        st.image(str(ROOT / "reports/retrieval_hit_at_5.svg"), width="stretch")
        st.caption("Keyword 9/12; TF-IDF 8/12. Retrospective test.")
    with r:
        st.image(str(ROOT / "reports/llm_provisional_findings.svg"), width="stretch")
        st.caption("Raw Llama: 4/12 factual, 3/12 expected citations, 2/3 refusals. Provisional.")
