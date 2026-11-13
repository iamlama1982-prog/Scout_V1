"""Scout final-project presentation, told from the evidence.

Use the actual charts committed from real source data and recorded evaluations.
The same Streamlit app contains the real live investigator. The PowerPoint is a
separate backup, not a source of fabricated performance figures.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
FIGURES = {
    "missingness": "reports/source_eda_missingness.png",
    "title_lengths": "reports/source_eda_title_lengths.png",
    "vendor_coverage": "reports/source_eda_vendor_coverage.png",
    "monthly_coverage": "reports/source_eda_monthly_coverage.png",
    "impact_labels": "reports/source_eda_impact_labels.png",
    "retrieval_hit": "reports/retrieval_hit_at_5.svg",
    "retrieval_time": "reports/retrieval_query_latency.svg",
    "llm_review": "reports/llm_provisional_findings.svg",
}

st.set_page_config(
    page_title="SCOUT · Project story",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.stApp {background: #101719;color: #eef5f0;}
[data-testid="stHeader"] {background: #101719;}
.block-container {max-width: 1320px;padding-top:1.05rem;padding-bottom:2rem;}
[data-testid="stTabs"] button {font-weight:670;}
.story-banner {border:1px solid #355a50;background:linear-gradient(125deg,#1a3330,#152124);
 border-radius:18px;padding:23px 28px;margin:4px 0 15px;}
.story-banner h1 {font-size:2rem;margin:0;color:#eff9f1;letter-spacing:-.035em;}
.story-banner p {margin:.4rem 0 0;color:#b9d7c8;font-size:1rem;}
.story-step {color:#a7d5c1;text-transform:uppercase;letter-spacing:.16em;
 font-size:.78rem;font-weight:750;margin-bottom:10px;}
.story-slide-title {color:#f5f8f3;font-size:clamp(1.6rem,3vw,2.75rem);
 line-height:1.16;font-weight:750;letter-spacing:-.038em;margin:0 0 8px;}
.story-lead {color:#d3e2d8;font-size:clamp(1.02rem,1.45vw,1.22rem);
 line-height:1.53;max-width:1050px;margin-bottom:12px;}
.story-metrics {display:flex;flex-wrap:wrap;gap:10px;margin:12px 0;}
.story-metric {flex:1;min-width:140px;background:#1b2f30;border:1px solid #3a5550;
 border-radius:13px;padding:13px 16px;}
.story-metric strong {display:block;color:#eff8f3;font-size:clamp(1.25rem,2.35vw,2.25rem);
 line-height:1.08;font-variant-numeric:tabular-nums;}
.story-metric span {display:block;color:#b5d0c4;font-size:.86rem;margin-top:8px;line-height:1.4;}
.story-insight {background:#1b282a;border:1px solid #35504b;border-radius:12px;
 padding:16px 18px;margin-bottom:11px;}
.story-insight .story-label {color:#a3d8c0;letter-spacing:.04em;font-weight:760;
 font-size:.9rem;margin-bottom:6px;}
.story-insight p {color:#d6e6dd;font-size:.98rem;line-height:1.55;margin:0;}
.story-takeaway {border-left:4px solid #8fc5ae;background:#1a302c;
 border-radius:0 11px 11px 0;padding:14px 17px;margin:14px 0 8px;
 font-size:1.03rem;color:#e5f5e8;line-height:1.55;}
.story-source {color:#9bb6ac;font-size:.78rem;line-height:1.45;margin:5px 0 10px;}
.story-failure {display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;}
.story-failure .cell {background:#1b2b2e;border:1px solid #3b5552;
 border-radius:12px;padding:15px 17px;}
.story-failure b {color:#b8e2cc;display:block;margin-bottom:7px;}
.story-failure span {color:#d6e3db;line-height:1.52;font-size:.98rem;}
.story-example {border:1px solid #46645b;padding:18px;background:#17282a;
 border-radius:12px;color:#e8f2e8;line-height:1.58;}
.story-example strong {color:#b8e2cb;}
.story-section-help {font-size:.86rem;color:#9fbaad;margin-bottom:10px;}
[data-testid="stImage"] {background:#f8faf9;border-radius:13px;padding:7px;
 border:1px solid #415b54;}
[data-testid="stImage"] img {border-radius:7px;}
[data-testid="stExpander"] {border:1px solid #304844;border-radius:11px;}
</style>
    """,
    unsafe_allow_html=True,
)


# Every main slide moves the story forward: question -> evidence -> decision.
# source references point to actual committed notebooks, charts and reports.
SLIDES = [
    {
        "n": 1, "group": "Problem", "tag": "01 / INTRODUCTION",
        "title": "SCOUT. Better questions. Safer investigations.",
        "lead": "An evidence-led IT incident investigator, built to support the next sensible check — not to invent a confident diagnosis.",
        "metrics": [("41,171", "Searchable public incident reports"), ("15", "Recorded raw Llama evaluations"),
                    ("86", "Automated tests passed in latest GitHub CI run")],
        "insights": [
            ("The question", "Can historical incidents, retrieved evidence and checked guidance help a person investigate without mistaking an AI guess for a fact?"),
            ("The practical output", "A working Streamlit conversation, linked public incidents, context-specific checked guides, optional local AI and a persistent case record."),
        ],
        "takeaway": "My goal was not to build an autonomous outage fixer. It was to help an investigator make a better-informed next decision.",
        "source": "README; notebooks 01–05; measured test results in GitHub CI.",
    },
    {
        "n": 2, "group": "Problem", "tag": "02 / THE REAL PROBLEM",
        "title": "A plausible answer can be the most dangerous one.",
        "lead": "Imagine a checkout service timing out after a deployment. A model may sound certain that the database is to blame before anyone has compared the evidence.",
        "comparison": [
            ("What the investigator actually knows", "504 timeouts, slow connections, a reported deployment and partial customer impact."),
            ("What is not known", "Which component is responsible, whether the deployment caused it, or which intervention is safe."),
            ("A useful first action", "Put the failure and change timestamps on one timeline, then check what changed and where requests fail."),
        ],
        "takeaway": "Scout should support the investigation process, not jump from similar words to an asserted root cause.",
        "source": "Problem framing in Notebook 01; checked timeline and tracing playbooks.",
    },
    {
        "n": 3, "group": "Data", "tag": "03 / COLLECTION & CLEANING",
        "title": "First I checked what kind of evidence I actually had.",
        "lead": "SevAnalysis aggregates published vendor status-page reports. These are real source-linked incidents, but they are not internal IT service tickets.",
        "metrics": [("41,314", "Original rows · 21 source columns"),
                    ("143", "Duplicate records removed"),
                    ("41,171", "Prepared searchable reports · 99.65% retained"),
                    ("364", "Different vendors represented")],
        "insights": [
            ("Preparation", "Parsed timestamps, selected searchable fields and removed duplicate usable rows. No rows were lost because title or vendor was missing."),
            ("Reproducibility", "Notebook 06 records the real-data counts, five output charts and a SHA-256 fingerprint for the analysed CSV."),
            ("Crucial limitation", "A status report can say a service was degraded without providing the cause, internal logs or the exact fix."),
        ],
        "takeaway": "I could search published incident descriptions. I could not train Scout to know an organisation's private fault history from them.",
        "source": "Notebook 06; reports/source_eda_metrics.json; CC BY-NC 4.0 source licence.",
    },
    {
        "n": 4, "group": "Data", "tag": "04 / EDA · MISSING VALUES",
        "title": "Nearly three quarters of the reports omit the affected component.",
        "lead": "The missingness chart from Notebook 06 changed what I could reasonably expect from retrieval.",
        "figure": "missingness",
        "insights": [
            ("What I measured", "72.94% of prepared records have no affected-component information; missing does not mean no component was affected."),
            ("Why it matters", "I cannot depend on neatly classified components to tell me which historical incidents are relevant."),
            ("Design response", "Search the title and available incident text, retain the source link and keep any diagnosis explicitly unconfirmed."),
        ],
        "takeaway": "The dataset contains plenty of records, but many lack the details needed for a precise technical match.",
        "source": "Actual plot: reports/source_eda_missingness.png · Notebook 06.",
    },
    {
        "n": 5, "group": "Data", "tag": "05 / EDA · TEXT QUALITY",
        "title": "The typical incident title contains just six words.",
        "lead": "Short titles explain why an apparently straightforward search can miss a matching incident.",
        "figure": "title_lengths",
        "insights": [
            ("What I measured", "Median six words; 10th percentile three words; 90th percentile eleven."),
            ("Example problem", "A query says 'Asia-Pacific', while the source title says 'APAC'. Both can describe the same region without sharing a term."),
            ("Design response", "Use word-and-bigram TF-IDF as a fast, transparent starting method, compare it with a keyword baseline and record the misses."),
        ],
        "takeaway": "A search miss may reflect sparse source language, not proof that a relevant incident does not exist.",
        "source": "Actual plot: reports/source_eda_title_lengths.png; retrieval miss Q07.",
    },
    {
        "n": 6, "group": "Data", "tag": "06 / EDA · COVERAGE",
        "title": "The source covers 364 vendors — unevenly.",
        "lead": "Vendor representation is descriptive coverage, not a ranking of which services are reliable.",
        "figure": "vendor_coverage",
        "insights": [
            ("What I measured", "The 12 most represented vendors account for 36.23% of the prepared reports."),
            ("Why it matters", "Two suppliers with similar incident wording can compete in a ranking, and frequently represented suppliers may dominate results."),
            ("What I decided", "Keep supplier names and original source URLs visible. Inspect wrong-supplier results in the retrieval error analysis."),
        ],
        "takeaway": "The chart describes the dataset's coverage — not outage risk, severity or supplier performance.",
        "source": "Actual plot: reports/source_eda_vendor_coverage.png · Notebook 06.",
    },
    {
        "n": 7, "group": "Method", "tag": "07 / METHOD & ARCHITECTURE",
        "title": "The evidence has three different jobs.",
        "lead": "The system separates 'what happened elsewhere', 'what the documentation says to check' and 'what an AI thinks might explain it'.",
        "comparison": [
            ("1 · Public incident retrieval", "Clean SevAnalysis CSV → word/bigram TF-IDF → ranked incident IDs and original source links."),
            ("2 · Checked technical guidance", "18 reviewed reference cards and six source-reviewed playbooks. Deterministic action order uses the investigator's reported information."),
            ("3 · Optional Llama + memory", "Ollama Llama 3.2 provides separately labelled hypotheses; SQLite stores messages, source snapshots and human review outcomes."),
        ],
        "insights": [
            ("Why not Llama alone?", "The model can cite the wrong thing, overlook a correct retrieved source or invent technical commands."),
            ("Why source-first?", "The useful checked response can appear and be saved before slow local model generation."),
        ],
        "takeaway": "Source retrieval, reviewed procedures and AI interpretation are deliberately not treated as equivalent evidence.",
        "source": "Notebooks 02, 04, 05 · src/incident_assistant.py, scout_playbooks.py, scout_case_store.py.",
    },
    {
        "n": 8, "group": "Evaluation", "tag": "08 / RETRIEVAL EXPERIMENT",
        "title": "The keyword baseline actually retrieved one more target.",
        "lead": "I compared both search methods on the same 12 answerable historical incident questions.",
        "figure": "retrieval_hit",
        "insights": [
            ("Metric", "Hit@5: did the expected incident ID appear among the first five returned records?"),
            ("Measured result", "Keyword overlap: 9/12 (75.0%). TF-IDF: 8/12 (66.7%)."),
            ("Interpretation", "TF-IDF is not proven more accurate. Twelve retrospectively written questions are too few to claim a general winner."),
        ],
        "takeaway": "I kept the less flattering result instead of tuning the model against the same 12 questions and calling it an independent improvement.",
        "source": "Actual figure: reports/retrieval_hit_at_5.svg · Notebook 03; reports/retrieval_baseline_2026-11.csv.",
    },
    {
        "n": 9, "group": "Evaluation", "tag": "09 / RETRIEVAL SPEED",
        "title": "TF-IDF's advantage was query speed, not accuracy.",
        "lead": "This is the second retrieval chart from the actual evaluation, measuring each search after the index was built.",
        "figure": "retrieval_time",
        "insights": [
            ("Measured result", "Mean keyword query: 0.551 seconds. Mean TF-IDF query: 0.007 seconds."),
            ("Fair comparison", "These figures exclude loading the data and constructing the TF-IDF index; no end-to-end response time is implied."),
            ("Product decision", "TF-IDF remained a reasonable fast prototype retriever, with its limitations documented and visible."),
        ],
        "takeaway": "Model selection involved a trade-off: substantially faster search on this run, but one fewer target retrieved.",
        "source": "Actual figure: reports/retrieval_query_latency.svg · Notebook 03.",
    },
    {
        "n": 10, "group": "Evaluation", "tag": "10 / ERROR ANALYSIS",
        "title": "The misses were not random: the wording and supplier mattered.",
        "lead": "I inspected specific wrong-ranked results instead of reporting only two percentages.",
        "comparison": [
            ("Q05 · Gamma in Brazil", "Keyword retrieved the DNS record first; TF-IDF missed it and preferred other vendors' DNS incidents."),
            ("Q07 · LangSmith in APAC", "Both methods missed it. The question said 'Asia-Pacific', but the published title said 'APAC'."),
            ("Q11 · Vanta support button", "Both methods missed it. The question used 'in-app support contact'; the report said 'Chat with us'."),
            ("Q02 · Azure", "TF-IDF found Azure Communication Services; keyword overlap preferred incidents about Azure published by other suppliers."),
        ],
        "takeaway": "The next retrieval experiment should test vendor-aware matching or semantic search on new, unseen questions.",
        "source": "reports/retrieval_findings.md · five documented error investigations.",
    },
    {
        "n": 11, "group": "Evaluation", "tag": "11 / RAW LLAMA 3.2",
        "title": "Having the right source did not mean Llama used it.",
        "lead": "15 raw responses were saved: 12 factual lookups plus three questions the public data could not answer.",
        "figure": "llm_review",
        "insights": [
            ("What I compared", "Source available in retrieved evidence, correctness of the direct answer, exact target source ID cited, and suitable refusals."),
            ("Provisional results", "Target present 8/12; factual pass 4/12; target cited 3/12; both correct and cited 2/12. Clear refusals: 2/3."),
            ("Evidence limit", "These are assistant-assisted provisional judgements, not independent human-approved answer accuracy."),
        ],
        "takeaway": "A retrieval hit, a correct factual statement and a well-supported answer are three different achievements.",
        "source": "Actual figure: reports/llm_provisional_findings.svg; detailed raw-answer review.",
    },
    {
        "n": 12, "group": "Evaluation", "tag": "12 / FAILURE THAT CHANGED THE DESIGN",
        "title": "Two of the clearest mistakes happened after successful retrieval.",
        "lead": "The correct Azure and HeyGen incidents were ranked first, but Llama still said no direct match existed.",
        "comparison": [
            ("Q02 · Azure", "Retrieval: correct Azure incident at rank 1. Generation: denied a close match and cited other vendors."),
            ("Q06 · HeyGen", "Retrieval: correct Generate Result button incident at rank 1. Generation: again claimed no direct match."),
            ("Live technical risk", "An earlier draft proposed checking database capacity first and named an invalid PostgreSQL view."),
        ],
        "takeaway": "I stopped allowing generated technical advice to dictate the investigation order; the original model output remains saved for audit.",
        "source": "reports/llm_evaluation_findings.md; Notebook 05; verified PostgreSQL example.",
    },
    {
        "n": 13, "group": "Evaluation", "tag": "13 / PERFORMANCE & PRODUCT DECISION",
        "title": "The local model also made the first response too slow.",
        "lead": "On a CPU-bound 16 GB laptop, the original raw-answer run was not suitable for instant interactive guidance.",
        "metrics": [
            ("81.0 s", "Median raw Llama answer among 15 recorded replies"),
            ("7.1/s", "Output tokens in a separate direct Ollama diagnostic"),
            ("22.49 s", "That separate short direct test"),
        ],
        "insights": [
            ("Anomaly kept", "Q15 alone recorded 52,047.6 seconds. Its cause is unknown; it is not representative generation time."),
            ("Design change", "Scout now shows and saves retrieved evidence and checked steps first. An AI interpretation runs only on request."),
            ("What is still unmeasured", "The revised complete UI's time-to-first-useful-answer has not been formally benchmarked."),
        ],
        "takeaway": "I changed the interaction design to remove the model as a blocker, not to claim I had made Llama faster.",
        "source": "reports/ollama_cpu_single_run_2026-11-10.csv; original 15-response timings; Notebook 03.",
    },
    {
        "n": 14, "group": "Safety", "tag": "14 / SAFEGUARDS ADDED AFTER TESTING",
        "title": "A human-check notice explains the uncertainty, not just 'AI can be wrong'.",
        "lead": "This is the latest safeguard: a user-friendly reason, a specific suggested check and an auditable human outcome.",
        "comparison": [
            ("Source-supported lead", "An original status-page link may support that a published incident occurred, not that it caused this outage."),
            ("Checked procedure", "A reviewed playbook gives a suggested read-only investigation step, but Scout cannot verify live applicability."),
            ("Optional AI interpretation", "Always unverified until checked. The model cannot grant itself an approved status."),
            ("Person's recorded result", "Supported / not supported / still uncertain, with what was checked. Scope: one described finding, not an entire reply."),
        ],
        "takeaway": "A recorded human check changes the audit status. It does not retrain the model, automatically resolve a case or prove the entire reply.",
        "source": "src/scout_verification.py; src/scout_case_store.py; Notebook 05; GitHub CI.",
    },
    {
        "n": 15, "group": "Demo", "tag": "15 / REAL LIVE DEMONSTRATION",
        "title": "One incident. New evidence. A different next check.",
        "lead": "Switch to Live Scout using the button below. This is the actual investigator and local case database, not a second mock app.",
        "comparison": [
            ("1 · Start", "Use the prepared 504 API timeout case. Show evidence and the first expandable checked step."),
            ("2 · Add information", "Add a deployment detail in Reply to Scout. Show the timeline guide moving up the investigation."),
            ("3 · Review", "Open Human check needed. Record a supported, unsupported or uncertain finding and inspect the saved status."),
            ("4 · Audit", "Open Case record or export JSON. Show the original reply and saved review. A previously generated AI draft is optional."),
        ],
        "takeaway": "Do not run a fresh CPU-bound Llama request during the demonstration. Use a saved AI draft if one is available.",
        "source": "pages/Scout.py · SQLite case records · saved checked guides.",
    },
    {
        "n": 16, "group": "Conclusion", "tag": "16 / CONCLUSION",
        "title": "Scout works as a cautious investigator — not an autonomous incident manager.",
        "lead": "The most valuable result was learning where the data, retriever and Llama each stop being trustworthy.",
        "comparison": [
            ("What is working", "Real data preparation and EDA; source-linked retrieval; checked guides; case continuity; separately labelled AI; persistent human reviews."),
            ("What is not established", "A verified root-cause engine, universally safe instructions, generalisable answer accuracy, or secure multi-user case storage."),
            ("What I would test next", "Independently approve the 15-answer evaluation; use a larger unseen test set; evaluate final checked-plan relevance separately."),
        ],
        "takeaway": "The design got better because the evaluation exposed weaknesses, not because the model produced a polished-looking answer.",
        "source": "README; submission evidence map; final evaluation limitations.",
    },
    {
        "n": 17, "group": "Appendix", "tag": "APPENDIX A1 / MORE REAL EDA",
        "title": "Coverage over time is not the same as continuous monitoring.",
        "lead": "Additional Notebook 06 plots show historical coverage and data interpretation.",
        "figure": "monthly_coverage",
        "insights": [
            ("What this shows", "The distribution of published incidents over time in the captured dataset."),
            ("What it does not show", "Continuous monitoring, true outage frequency or comparable reporting effort across all vendors."),
        ],
        "takeaway": "The dataset is useful for retrieval, but it is not a universal measure of service reliability.",
        "source": "Actual plot: reports/source_eda_monthly_coverage.png · Notebook 06.",
    },
    {
        "n": 18, "group": "Appendix", "tag": "APPENDIX A2 / IMPACT LABELS",
        "title": "A severity label is only as comparable as the publisher's definition.",
        "lead": "The impact-label chart is useful for describing the source, not for assigning universal risks.",
        "figure": "impact_labels",
        "insights": [
            ("What I measured", "21,844 minor, 7,890 major, 7,543 none, 3,497 critical and 397 unknown labels in the prepared dataset."),
            ("Why it matters", "Vendors use different publishing standards; 'major' in one system is not necessarily the same as 'major' in another."),
        ],
        "takeaway": "I did not turn the status labels into a cross-vendor risk score.",
        "source": "Actual plot: reports/source_eda_impact_labels.png · reports/source_eda_metrics.json.",
    },
    {
        "n": 19, "group": "Appendix", "tag": "APPENDIX A3 / EVIDENCE LIMITS",
        "title": "What a test, a source link and a human check each prove.",
        "lead": "These are separate claims and I have kept them separate in the notebooks and presentation.",
        "comparison": [
            ("Software checks", "The current suite tests programmed behaviours. It does not certify AI correctness."),
            ("Source validation", "The expected incidents appear in the publisher's records. Only two original vendor pages were directly accessed in the documented external check."),
            ("Raw answer scoring", "4/12 factual passes and 2/3 clear refusals remain provisional assistant-assisted scoring."),
            ("Human checks inside Scout", "An operator's recorded outcome can support one specific observation. It does not independently validate the whole answer."),
        ],
        "takeaway": "The correct language is 'observed and documented', not 'independently proved' where a review is still pending.",
        "source": "reports/source_link_checks_2026-11-10.md; reports/llm_evaluation_findings.md.",
    },
]

GROUPS = [
    ("Problem", "01 · Why Scout"),
    ("Data", "02 · Real data"),
    ("Method", "03 · How it works"),
    ("Evaluation", "04 · Experiments"),
    ("Safety", "05 · Safeguards"),
    ("Demo", "06 · Live demo"),
    ("Conclusion", "07 · Conclusion"),
    ("Appendix", "Appendix · Evidence"),
]

DEMO_REVIEWS = [
    ("Still uncertain", "uncertain",
     "I have the 504 error timestamps, but I have not yet checked them against the deployment timeline.",
     "Scout records that the finding is still uncertain and suggests what to check next."),
    ("Not supported", "not_supported",
     "I compared the reported deployment times and timeout logs. The failures began much later; this check does not support a direct deployment link.",
     "Scout records a not-supported human judgement. The original reply remains visible."),
    ("Supported", "supported",
     "I checked the gateway and upstream timestamps and confirmed that our 504 errors coincide with upstream response delays.",
     "Scout marks that specific reviewed finding supported, not the whole diagnosis."),
]


def markup(text: str, cls: str) -> None:
    st.markdown(f'<div class="{cls}">{escape(text)}</div>', unsafe_allow_html=True)


def show_metrics(metrics: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="story-metric"><strong>{escape(value)}</strong>'
        f'<span>{escape(label)}</span></div>'
        for value, label in metrics
    )
    st.markdown(f'<div class="story-metrics">{cells}</div>', unsafe_allow_html=True)


def show_insights(insights: list[tuple[str, str]]) -> None:
    for heading, body in insights:
        st.markdown(
            '<div class="story-insight">'
            f'<div class="story-label">{escape(heading)}</div>'
            f'<p>{escape(body)}</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def show_comparison(items: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="cell"><b>{escape(heading)}</b>'
        f'<span>{escape(body)}</span></div>'
        for heading, body in items
    )
    st.markdown(f'<div class="story-failure">{cells}</div>', unsafe_allow_html=True)


def show_figure(key: str) -> None:
    """Display the actual saved chart; never regenerate substitute numbers."""
    path = ROOT / FIGURES[key]
    if path.is_file():
        st.image(str(path), width="stretch")
    else:
        st.error(f"Expected report chart missing: {FIGURES[key]}")


def render_slide(slide: dict) -> None:
    markup(f"SLIDE {slide['n']:02d} OF {len(SLIDES)} · {slide['tag']}", "story-step")
    markup(slide["title"], "story-slide-title")
    markup(slide["lead"], "story-lead")

    if slide.get("metrics"):
        show_metrics(slide["metrics"])
    if slide.get("figure"):
        graph, interpretation = st.columns([1.55, 1], gap="large")
        with graph:
            show_figure(slide["figure"])
        with interpretation:
            show_insights(slide.get("insights", []))
    else:
        if slide.get("comparison"):
            show_comparison(slide["comparison"])
        if slide.get("insights"):
            st.write("")
            show_insights(slide["insights"])

    st.markdown(
        f'<div class="story-takeaway">{escape(slide["takeaway"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="story-source">Evidence: {escape(slide["source"])}</div>',
        unsafe_allow_html=True,
    )
    if slide["group"] == "Demo":
        st.button(
            "🧭 Open the real Live Scout investigation",
            key="scout_present_open_demo",
            width="stretch",
            type="primary",
            on_click=lambda: st.switch_page("pages/Scout.py"),
        )
        with st.expander("Example human-check findings", expanded=False):
            st.caption("These are example findings to enter manually in Scout, not pre-verified facts.")
            for label, outcome, sample, expected in DEMO_REVIEWS:
                st.markdown(f"**{label} · {outcome}**")
                st.code(sample, language=None)
                st.caption(expected)
            st.caption(
                "After saving: look for the updated status, check Case record / export, "
                "then use Reply to Scout if you want the new observation to affect "
                "a subsequent investigation. Saving a review alone does not retrain "
                "the model, change the original reply or close the case."
            )
    elif slide["group"] == "Conclusion":
        st.button(
            "🧭 Return to Live Scout",
            key="scout_present_return_demo",
            width="stretch",
            on_click=lambda: st.switch_page("pages/Scout.py"),
        )


st.markdown(
    '<div class="story-banner"><h1>SCOUT. / The evidence behind the design</h1>'
    '<p>Symptoms → Real data → Retrieval experiment → Llama failure → '
    'Safeguards → Live investigation</p></div>',
    unsafe_allow_html=True,
)
st.caption(
    "Ironhack final project · supporting evidence for the 10-minute live pitch · "
    "real saved figures, not recreated sample charts."
)

tabs = st.tabs([label for _, label in GROUPS])
for tab, (group, label) in zip(tabs, GROUPS):
    with tab:
        available = [slide for slide in SLIDES if slide["group"] == group]
        choice = st.selectbox(
            "Choose slide in this section",
            options=[slide["n"] for slide in available],
            # Bind this tab's choices now. A late-bound loop closure could
            # point every tab's formatter at the Appendix choices on reruns.
            format_func=lambda n, choices=tuple(available): next(
                slide["title"] for slide in choices if slide["n"] == n
            ),
            key=f"scout_story_{group.lower()}",
        )
        current = next(slide for slide in available if slide["n"] == choice)
        render_slide(current)
        st.caption(
            f"{label} · {len(available)} slide(s) in section · "
            "Use the topic tabs above to move through the story."
        )

st.divider()
st.caption(
    "Source of truth: notebooks 03 and 06, the committed reports, and the "
    "Scout application. Provisional answer scores are not approved human grades. "
    "The 15-answer evaluation predates the later staged UI and human checks."
)
