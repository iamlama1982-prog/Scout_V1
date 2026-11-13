"""Scout — evidence-led incident investigator.

This is a standalone RAG application; historical incidents and technical
references retain distinct evidence IDs.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
from urllib.request import urlopen

import streamlit as st

from src.scout_case_store import (
    add_message, add_note, add_verification_review, create_case, delete_case,
    export_case, get_case, get_messages, get_notes, get_verification_reviews,
    initialise_database, list_cases, set_case_status, title_case_from_first_message,
    update_assistant_evidence,
)
from src.scout_conversation import (
    case_context_for_model, retrieval_query, source_snapshot,
)
from src.scout_response_flow import first_useful_reply
from src.scout_case_log import format_case_log
from src.scout_workflow import completed_checks, save_investigation_turn
from src.scout_demo import (
    DEMO_CASE_TITLE, DEMO_OPENING, DEMO_STEPS, DEMO_RECOVERY,
    DEMO_REVIEW, next_demo_step, is_demo_case,
)
from src.scout_verification import ai_verification_notice, initial_verification_notice

from src.incident_assistant import (
    DATASET_PAGE, LOCAL_CSV, answer_with_llm, build_index,
    evidence_only_answer, historical_evidence_for_answer, keyword_search,
    load_incidents, prepare_incidents, retrieve,
)
from src.technical_knowledge import (
    CATALOGUE_PATH, build_knowledge_index, load_knowledge, retrieve_knowledge,
)
# Streamlit keeps imported modules in the server process between script reruns.
# A git pull updates the file on disk without replacing that cached module.
# The regular Python import can succeed while an existing Streamlit session
# still holds an older playbook module. Reload only when this attribute is missing.
from src import scout_playbooks as _scout_playbooks

if not hasattr(_scout_playbooks, "checked_plan_response"):
    importlib.invalidate_caches()
    _scout_playbooks = importlib.reload(_scout_playbooks)

checked_plan_response = _scout_playbooks.checked_plan_response
load_playbooks = _scout_playbooks.load_playbooks
reported_case_text = _scout_playbooks.reported_case_text
select_playbooks = _scout_playbooks.select_playbooks

st.set_page_config(
    page_title="Scout — Incident Investigator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 83% 5%, rgba(91,154,144,.11), transparent 42%), #101719;
        color: #ecf0ec;
    }
    [data-testid="stSidebar"] {
        background: #152022;
        border-right: 1px solid #304143;
    }
    .block-container {max-width: 1150px; padding-top: 2.15rem; padding-bottom: 3.6rem;}
    .scout-hero {
        display: flex; align-items: center; gap: 1.4rem;
        border: 1px solid #36534e;
        background: linear-gradient(125deg, #1d3230 0%, #172526 56%, #192122 100%);
        border-radius: 24px; padding: 1.65rem 2rem;
        margin: 0 0 1.4rem 0;
        box-shadow: 0 18px 50px rgba(0,0,0,.13);
    }
    .scout-mark {
        width: 78px; height: 78px; flex: 0 0 78px;
        border-radius: 22px; display: flex;
        justify-content: center; align-items: center;
        background: linear-gradient(150deg, #4c7b72, #284642);
        color: #e8f6ed; font-size: 40px;
        border: 1px solid rgba(212,236,223,.18);
        box-shadow: 0 8px 24px rgba(0,0,0,.14);
    }
    .scout-eyebrow {
        color: #a1c2b6; text-transform: uppercase;
        letter-spacing: .13em; font-size: .74rem; font-weight: 680;
        margin-bottom: .35rem;
    }
    .scout-heading {
        font-size: clamp(2.1rem, 4vw, 3.0rem); letter-spacing: -.045em;
        line-height: 1.12; font-weight: 720; color: #f6f8f3;
    }
    .scout-intro {
        color: #c9d7d0; font-size: 1.04rem;
        line-height: 1.62; margin-top: .5rem; max-width: 680px;
    }
    .scout-sidebar-brand {
        display: flex; align-items: center; gap: .6rem;
        font-size: 1.23rem; font-weight: 720; letter-spacing: -.025em; color: #f0f4ef;
    }
    .scout-sidebar-mark {
        display:inline-flex; align-items:center; justify-content:center;
        border-radius: 11px; width: 35px; height: 35px;
        background: #2a4a43; color: #c6e4d5; font-size: 1.25rem;
        border: 1px solid #4b7469;
    }
    .scout-stats {
        display:flex; gap: .7rem; flex-wrap:wrap; margin:.25rem 0 1.45rem 0;
    }
    .scout-stat {
        border: 1px solid #314447; border-radius: 999px;
        background: #1a292b; color: #c8d8d2;
        padding: .46rem .8rem; font-size: .85rem;
    }
    .scout-stat strong {color: #f1f4f0; font-weight: 670; font-variant-numeric: tabular-nums;}
    .scout-section {
        color: #eef3ee; font-size: 1.13rem; font-weight: 660; margin-bottom: .45rem;
    }
    .scout-help {color:#a9bbb6; font-size: .9rem; margin: .3rem 0 .8rem 0;}
    .scout-result-header {
        font-size:.75rem; text-transform:uppercase; letter-spacing:.12em;
        color:#9ec6b6; font-weight:750; margin:.6rem 0 1rem;
    }
    .scout-footnote {
        border-left: 3px solid #55786f; padding:.58rem .85rem;
        background: #192527; border-radius: 0 10px 10px 0;
        color:#b3c6bd; font-size:.84rem; line-height:1.55;
        margin-top: 1rem;
    }
    div[data-testid="stTextArea"] textarea {
        border: 1px solid #47615b; border-radius: 15px;
        background: #172124; color: #f2f5ef;
        font-size: 1.03rem; line-height: 1.65;
        padding: 1rem 1.05rem;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #91bdae; box-shadow: 0 0 0 2px rgba(145,189,174,.13);
    }
    div[data-testid="stForm"] {
        border: 1px solid #2b4140; border-radius: 18px;
        padding: 1rem 1.25rem 1.1rem;
        background: rgba(23,33,35,.84);
    }
    button[kind="primary"], button[data-testid="stBaseButton-primary"] {
        background: #abd4c4 !important; color: #16332d !important;
        border: 1px solid #abd4c4 !important; border-radius: 12px !important;
        font-weight: 700 !important; padding: .55rem 1.6rem;
    }
    button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
        background: #c5e6d9 !important; border-color: #c5e6d9 !important;
    }
    button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
        border-color: #394d4c; border-radius: 11px;
        color: #c9d9d0;
    }
    [data-testid="stTabs"] button {
        font-size: .94rem; font-weight: 570;
    }
    [data-testid="stExpander"] {
        border: 1px solid #304142; border-radius: 12px;
        background: #172124;
    }
    div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li {
        line-height: 1.72;
    }
    [data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h2,
    [data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h3 {
        color: #e8f2e9; letter-spacing: -.01em; margin-top: 1.2rem;
    }
    /* Conversation: Scout and the investigator must be easy to tell apart.
       We use our own speaker labels for styling, not Streamlit's generated class names. */
    [data-testid="stChatMessage"] {
        border-radius: 18px;
        padding: 1.05rem 1.3rem;
        margin-bottom: .85rem;
        box-shadow: 0 5px 20px rgba(0, 0, 0, .08);
    }
    [data-testid="stChatMessage"]:has(.scout-speaker-user) {
        background: #212b3a;
        border: 1px solid #465b78;
        border-left: 3px solid #8fa9db;
    }
    [data-testid="stChatMessage"]:has(.scout-speaker-assistant) {
        background: #1b302c;
        border: 1px solid #41685b;
        border-left: 3px solid #8ac2a8;
    }
    .scout-speaker {
        font-size: .79rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: .095em;
        margin-bottom: .65rem;
    }
    .scout-speaker-user {color: #b7c9f3;}
    .scout-speaker-assistant {color: #abe2ca;}
    [data-testid="stChatMessage"]:has(.scout-speaker-user) p,
    [data-testid="stChatMessage"]:has(.scout-speaker-user) li {
        color: #e8edf9;
    }
    [data-testid="stChatMessage"]:has(.scout-speaker-assistant) p,
    [data-testid="stChatMessage"]:has(.scout-speaker-assistant) li {
        color: #edf7ef;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        font-size: 1rem;
        line-height: 1.65;
    }
    [data-testid="stBottomBlockContainer"]:has([data-testid="stChatInput"])::before {
        content: "💬  REPLY TO SCOUT";
        display: block;
        color: #b6e4d2;
        font-size: .8rem;
        letter-spacing: .09em;
        font-weight: 750;
        margin: .1rem 0 .55rem .3rem;
    }
    [data-testid="stChatInput"] {
        border: 2px solid #699f8c;
        border-radius: 16px;
        background: #1d2e2d;
        box-shadow: 0 0 0 3px rgba(105,159,140,.08), 0 12px 28px rgba(0,0,0,.18);
    }
    [data-testid="stChatInput"] textarea {
        font-size: 1rem;
        color: #f1f9f4;
    }
    @media (max-width:720px) {
        .block-container {padding-top: 1.05rem;}
        .scout-hero {padding:1.15rem; gap:.9rem;}
        .scout-mark {width:55px; height:55px; flex-basis:55px; font-size:29px; border-radius:16px;}
        .scout-intro {font-size:.93rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Finding and preparing the incident history…")
def load_index(cache_tag: str, raw_bytes: bytes | None, local_path: str | None = None):
    source = raw_bytes if raw_bytes is not None else Path(local_path or LOCAL_CSV)
    return build_index(prepare_incidents(load_incidents(source)))


@st.cache_resource(show_spinner="Preparing the technical guides…")
def load_technical_knowledge(version: int):
    return build_knowledge_index(load_knowledge())


def local_ollama_status(model_name: str) -> tuple[bool, str]:
    """Verify a running local Ollama server and an installed model."""
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            data = json.load(response)
        installed = [item.get("name", "") for item in data.get("models", [])]
    except (OSError, ValueError, KeyError, TimeoutError):
        return False, (
            "I can't reach Ollama just now. Open the Ollama app on this "
            "computer and check that it's running."
        )
    name = model_name.strip()
    if name in installed or f"{name}:latest" in installed:
        return True, f"{name} is installed and Ollama is responding."
    return False, (
        f"Ollama is running, but {name} isn't installed yet. "
        f"Run 'ollama pull {name}' in PowerShell."
    )


def source_card(record: dict):
    with st.expander(f"{record['vendor']}  ·  {record['title']}"):
        st.caption(
            f"Reported: {record['started_at'] or 'date unavailable'}"
            f"  ·  Impact: {record['impact'] or 'not recorded'}"
            f"  ·  Status: {record['status'] or 'not recorded'}"
        )
        if record["components"]:
            st.write(f"**Affected services/components:** {record['components']}")
        st.caption(f"Source reference: {record['doc_id']}")
        if record["source_url"]:
            st.link_button("Read the original incident", record["source_url"])
        else:
            st.caption("No original incident link was provided for this record.")


def knowledge_card(record: dict):
    with st.expander(f"{record['publisher']}  ·  {record['title']}"):
        st.write(record["summary"])
        st.markdown("**Checks worth considering**")
        for check in record["diagnostic_checks"]:
            st.markdown(f"- {check}")
        st.caption(
            f"Reviewed: {record['reviewed_on']}  ·  Reference: {record['kb_id']}. "
            "These checks are relevant only if you're using the named technology."
        )
        st.link_button("Read the official guide", record["url"])


def investigation_step_cards(playbooks: list[dict], demo_numbering: bool = False) -> None:
    """Show the source-checked procedures, not free-form commands from an LLM."""
    if not playbooks:
        return

    st.markdown("**🧭 Your investigation steps**")
    st.caption(
        "Choose a check to see how to carry it out, what the results might mean "
        "and where the guidance came from. These are suggestions, not completed checks."
    )
    # In the pitch, keep each guide's original step number even after earlier
    # checks are completed. Ordinary cases still number their current list.
    demo_numbers = {step['id']: i for i, step in enumerate(DEMO_STEPS, start=1)}
    for number, item in enumerate(playbooks, start=1):
        if demo_numbering:
            number = demo_numbers.get(item['id'], number)
        with st.expander(f"{number}. {item['title']}  ·  View steps"):
            st.write(item["summary"])
            st.markdown(f"**When it applies:** {item['applies_when']}")
            st.markdown("**How to check**")
            for position, step in enumerate(item["steps"], start=1):
                st.markdown(f"**{position}.** {step['instruction']}")
                command = step.get("command")
                if command:
                    st.code(
                        command,
                        language="sql" if command.lstrip().startswith("SELECT") else "bash",
                    )
            findings = item["interpretation"]
            st.markdown("**What the result could tell you**")
            st.markdown(f"- **Supports the hypothesis:** {findings['supports']}")
            st.markdown(f"- **Weakens the hypothesis:** {findings['weakens']}")
            st.markdown(f"- **Still uncertain:** {findings['unknown']}")
            st.markdown(f"**What to tell Scout afterwards:** {item['share_back']}")
            if item.get("source_url"):
                st.caption(
                    f"Source: {item['source_publisher']} "
                    f"({item['reference_id']}) · checked {item['reviewed_on']}"
                )
                st.markdown(f"[Read the official documentation]({item['source_url']})")
            else:
                st.caption(
                    "Source: original general investigation method, "
                    "not a vendor-verified procedure."
                )


def show_human_check(
    case_id: str, message_id: int, evidence: dict, target: str,
    latest_review: dict | None, can_review: bool,
) -> None:
    """One contextual, human-controlled verification prompt per reply part."""
    if target == "initial_reply":
        notice = evidence.get("initial_verification")
        if not isinstance(notice, dict):
            # Existing cases from before this feature remain readable.
            notice = initial_verification_notice(evidence)
        label = "Investigation reply"
    else:
        notice = ai_verification_notice(evidence)
        label = "AI interpretation"

    st.caption(f"{label} · {notice['source_state']}")
    if latest_review is None:
        st.info(
            f"**Human check needed — {notice['title']}**\n\n"
            f"**Why:** {notice['reason']}\n\n"
            f"**What to check:** {notice['human_check']}"
        )
    else:
        outcome_labels = {
            "supported": "Human-reviewed: specified finding supported",
            "not_supported": "Human-reviewed: specified finding not supported",
            "uncertain": "Human-reviewed: still uncertain",
        }
        st.caption(
            f"{outcome_labels[latest_review['outcome']]} · "
            f"{latest_review['created_at'][:16].replace('T', ' ')} UTC"
        )
        st.write(f"**What was checked:** {latest_review['detail']}")
        if latest_review["outcome"] != "supported":
            st.info(
                f"**Still needs attention:** {notice['human_check']}"
            )
        else:
            st.caption(
                "Only the finding described in this review was checked. "
                "This does not certify the whole reply or a root cause."
            )
        st.caption(
            "This review is an audit record for this reply. To change the next "
            "investigation step, share what you discovered using Reply to Scout. "
            "Saving a review alone does not rewrite an answer or resolve the case."
        )

    if not can_review:
        return
    with st.expander(f"Record human check · {label}", expanded=False):
        st.caption(
            "Record one specific claim or next step, the evidence you "
            "checked and the result. This is your judgement, not the AI's."
        )
        with st.form(f"scout_review_{message_id}_{target}"):
            outcome = st.selectbox(
                "What did your check establish?",
                ["uncertain", "supported", "not_supported"],
                format_func=lambda key: {
                    "uncertain": "Still uncertain / more evidence needed",
                    "supported": "This specific finding is supported",
                    "not_supported": "This specific finding is not supported",
                }[key],
            )
            detail = st.text_area(
                "What exactly did you check and find?",
                placeholder="For example: I compared the 504 timestamps to our deployment log; they do not overlap.",
                max_chars=3000,
            )
            submitted = st.form_submit_button("Save review to case history")
        if submitted:
            try:
                add_verification_review(
                    case_id, message_id, target, outcome, detail,
                )
            except ValueError as exc:
                st.warning(str(exc))
            else:
                st.rerun()


def show_referenced_sources(answer: dict, incidents: list[dict], guides: list[dict]):
    """Only render source links for the exact verified IDs used by the model."""
    cited = answer.get("cited_ids", [])
    if not cited:
        st.caption("Scout hasn't cited a matching source in this answer. Review the evidence tabs.")
        return
    by_id = {
        **{item["doc_id"]: ("Incident report", item["title"], item["source_url"]) for item in incidents},
        **{item["kb_id"]: ("Technical guide", item["title"], item["url"]) for item in guides},
    }
    with st.expander(f"Sources Scout referred to ({len(cited)})"):
        for identifier in cited:
            if identifier not in by_id:
                continue
            kind, title, url = by_id[identifier]
            st.markdown(f"**{kind}** · {title}")
            st.caption(identifier)
            if url:
                st.link_button(f"Open {kind.lower()}", url)


st.markdown(
    """
    <div class="scout-hero">
      <div class="scout-mark" aria-hidden="true">🧭</div>
      <div>
        <div class="scout-eyebrow">Ops Sentinel · Incident intelligence</div>
        <div class="scout-heading">Scout.</div>
        <div class="scout-intro">Tell me what is happening. We'll work through
        the investigation together, one useful question at a time.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# This database is local to the machine running Streamlit. We never commit it.
try:
    initialise_database()
    saved_cases = list_cases()
except OSError as exc:
    st.error(f"Scout couldn't open its local case records: {exc}")
    st.stop()

NEW_CASE = "__new_case__"
# Keep the sidebar option order stable when a case gets new messages or reviews.
# list_cases() is sorted by updated_at, which changes on every save.
# Reordering the widget choices could make Streamlit revert to New investigation.
case_ids = [NEW_CASE] + [
    item["id"] for item in sorted(
        saved_cases, key=lambda item: (item["created_at"], item["id"]),
        reverse=True,
    )
]
by_case_id = {item["id"]: item for item in saved_cases}

# A new case is created further down the page, after the case selector exists.
# Save its ID in a separate key and apply it at the START of the next rerun.
# Streamlit does not allow changing a widget's key after it is instantiated.
pending_case = st.session_state.pop("scout_pending_case", None)
if pending_case in case_ids:
    st.session_state["scout_current_case"] = pending_case

# A fresh browser session restores the most recently updated saved case.
# The old default (always New investigation) made a refresh look like data loss.
# A first-time installation still opens the guided start screen.
if st.session_state.pop("scout_reset_opening_message", False):
    st.session_state["scout_opening_message"] = ""

if "scout_current_case" not in st.session_state:
    st.session_state["scout_current_case"] = (
        saved_cases[0]["id"] if saved_cases else NEW_CASE
    )
if st.session_state["scout_current_case"] not in case_ids:
    st.session_state["scout_current_case"] = (
        saved_cases[0]["id"] if saved_cases else NEW_CASE
    )

# The saved-case list is sorted by update time, so it can be reordered after
# every message. Streamlit may recreate a selectbox when its options change,
# dropping it back to the first ("New investigation") option. Keep the active
# case in a separate, durable session key and re-seed the WIDGET key before
# it is instantiated. The widget may update the active case ONLY after an
# actual user selection via on_change.
st.session_state["scout_case_picker"] = st.session_state["scout_current_case"]


def select_investigation() -> None:
    """An intentional sidebar selection changes the active case."""
    st.session_state["scout_current_case"] = st.session_state["scout_case_picker"]


def start_new_investigation() -> None:
    """Create and select a real case before the selectbox appears on rerun.

    The previous implementation only reselected the empty 'New investigation'
    placeholder, so clicking the button appeared to do nothing.
    """
    new_case = create_case("New investigation")
    st.session_state["scout_current_case"] = new_case["id"]
    st.session_state["scout_opening_message"] = ""


def case_label(identifier: str) -> str:
    if identifier == NEW_CASE:
        return "New investigation"
    case = by_case_id.get(identifier)
    if not case:
        return "Investigation unavailable"
    # Streamlit serialises the displayed option label, so identical titles
    # must not produce identical labels. Show the ID before the title so
    # the correct case is obvious even in the narrow sidebar.
    short_id = identifier[:8]
    if sum(other.startswith(short_id) for other in by_case_id) > 1:
        short_id = identifier
    prefix = "✓ " if case["status"] == "resolved" else "○ "
    return f"{short_id} · {prefix}{case['title'][:50]}"


with st.sidebar:
    st.markdown(
        '<div class="scout-sidebar-brand"><span class="scout-sidebar-mark">✦</span>Scout</div>',
        unsafe_allow_html=True,
    )
    st.caption("Your incident investigation assistant")
    st.divider()
    st.selectbox(
        "Your investigations",
        case_ids,
        # The picker is seeded from the active case above. Supplying both
        # index and session_state value confuses Streamlit on reruns.
        format_func=case_label,
        key="scout_case_picker",
        on_change=select_investigation,
        help="Each case has its own ID. Select by the ID shown before its title.",
    )
    st.button(
        "＋ Start a new investigation",
        use_container_width=True,
        on_click=start_new_investigation,
    )

    st.divider()
    st.checkbox(
        "Show presenter controls",
        key="scout_pitch_mode",
        value=False,
        help="One-click fictional scenario in real Scout; normal cases are untouched.",
    )
    mode_labels = {
        "Ollama running locally": "Ask Scout · Local AI",
        "Evidence only (no LLM)": "Search + checked guides · No AI",
        "Hosted OpenAI-compatible API": "Ask Scout · Hosted model",
    }
    mode = st.selectbox(
        "How would you like Scout to help?",
        list(mode_labels),
        format_func=lambda value: mode_labels[value],
        # Presenter mode avoids an Ollama connection warning or slow call.
        index=1 if st.session_state.get("scout_pitch_mode", False) else 0,
    )
    if mode == "Ollama running locally":
        with st.expander("Local model settings"):
            model = st.text_input("Ollama model", value="llama3.2")
            base_url = st.text_input("Local API", value="http://localhost:11434/v1")
        api_key = "ollama"
        model_ready, connection_message = local_ollama_status(model)
        if model_ready:
            st.success("Scout is ready")
            st.caption(connection_message)
        else:
            st.warning("Scout isn't connected yet")
            st.caption(connection_message)
    elif mode == "Hosted OpenAI-compatible API":
        with st.expander("Hosted model settings", expanded=True):
            try:
                saved_key = st.secrets.get("OPENAI_API_KEY", "")
            except Exception:
                saved_key = ""
            api_key = st.text_input("API key", type="password", value=saved_key)
            model = st.text_input("Model", value="gpt-4.1-mini")
        base_url = None
        model_ready = bool(api_key.strip())
        if not model_ready:
            st.info("Enter a valid API key to ask Scout.")
    else:
        model, api_key, base_url = "", "", None
        model_ready = False
        st.caption("Search the records and show applicable reviewed guides without AI generation.")

    use_knowledge = st.checkbox(
        "Include technical guidance",
        value=True,
        help="Use the reviewed library of official troubleshooting references.",
    )
    with st.expander("Data and search settings"):
        st.markdown(f"[SevAnalysis incident data]({DATASET_PAGE}) · CC BY-NC 4.0")
        uploaded = st.file_uploader("Replace or upload incidents.csv", type="csv")
        st.caption("You can also save incidents.csv in the existing data/raw/incident_taxonomy folder.")
        k = st.slider("Similar incidents to show", 3, 10, 5)

# Tests can use a disposable copy of the public CSV, never the user's data.
# Ordinary local use still takes its path from LOCAL_CSV.
incident_csv = Path(os.environ.get("SCOUT_INCIDENT_CSV", str(LOCAL_CSV)))

# Saved cases should still be readable if the publisher CSV isn't present.
# A new investigation needs that dataset, but simply reopening a case doesn't.
index = None
if not uploaded and not incident_csv.exists():
    st.info(
        "You can read your saved cases below. To start or continue an investigation, "
        "upload the SevAnalysis incidents.csv using the sidebar."
    )
else:
    try:
        if uploaded:
            raw = uploaded.getvalue()
            signature = f"upload:{uploaded.name}:{hashlib.sha256(raw).hexdigest()[:16]}"
            index = load_index(signature, raw)
        else:
            stat = incident_csv.stat()
            signature = f"local:{incident_csv}:{stat.st_size}:{stat.st_mtime_ns}"
            index = load_index(signature, None, str(incident_csv))
    except (ValueError, OSError, UnicodeError) as exc:
        st.warning(f"Scout couldn't read the incident file: {exc}")

try:
    knowledge_index = load_technical_knowledge(CATALOGUE_PATH.stat().st_mtime_ns)
except (ValueError, OSError) as exc:
    knowledge_index = None
    if use_knowledge:
        st.warning(f"The technical guide library couldn't be loaded: {exc}")

try:
    playbook_catalogue = load_playbooks()
except (ValueError, OSError) as exc:
    playbook_catalogue = []
    if use_knowledge:
        st.warning(f"The detailed investigation guides couldn't be loaded: {exc}")

guide_count = len(knowledge_index.records) if knowledge_index is not None else 0
st.markdown(
    f'<div class="scout-stats">'
    f'<span class="scout-stat"><strong>{len(index.records) if index is not None else 0:,}</strong> past incidents</span>'
    f'<span class="scout-stat"><strong>{guide_count}</strong> technical guides</span>'
    f'<span class="scout-stat">Case history saved locally</span>'
    f'</div>',
    unsafe_allow_html=True,
)

current_id = st.session_state["scout_current_case"]
current_case = get_case(current_id) if current_id != NEW_CASE else None
messages = get_messages(current_id) if current_case else []
notes = get_notes(current_id) if current_case else []
review_history = get_verification_reviews(current_id) if current_case else []
latest_reviews = {
    (item["message_id"], item["target"]): item for item in review_history
}

if st.session_state.get("scout_pitch_mode", False):
    st.markdown("### ✦ You're running an online shop. Checkout is failing.")
    st.caption(
        "No IT expertise needed. You're responsible for customers: what happened, "
        "what changed, and what do we actually know? The incident is fictional; "
        "the search, checked guidance and saved case are real."
    )
    col_main, col_support = st.columns([2, 1], gap="medium")
    with col_main:
        if st.button(
            "▶ Prepare a fresh demo case",
            key="pitch_prepare_case",
            type="primary",
            use_container_width=True,
            disabled=index is None,
        ):
            demo_case = create_case(DEMO_CASE_TITLE)
            with st.spinner("Retrieving real incident leads and checked steps…"):
                save_investigation_turn(
                    demo_case["id"], DEMO_OPENING, index, knowledge_index,
                    playbook_catalogue, use_knowledge=use_knowledge, k=k,
                )
            st.session_state["scout_pending_case"] = demo_case["id"]
            st.rerun()
    with col_support:
        st.caption(
            "Open this case before presenting. Each preparation creates a "
            "separate DEMO-labelled local case; no existing case is overwritten."
        )
    if index is None:
        st.warning("The real incident CSV must be loaded to prepare a pitch case.")
    if is_demo_case(current_case) and messages:
        done = completed_checks(notes)
        step = next_demo_step(notes)
        count = sum(step["id"] in done for step in DEMO_STEPS)
        st.caption(f"Active demo case: {current_id[:8]} · This case's saved progress")
        st.progress(count / len(DEMO_STEPS), text=f"{count} of {len(DEMO_STEPS)} investigation checks recorded")
        # Show the saved result before the next action, so the presenter and
        # audience can see that the previous check actually happened.
        if count:
            completed = [item for item in DEMO_STEPS if item["id"] in done]
            last = completed[-1]
            st.success("Completed: " + last["label"])
            st.caption(done[last["id"]])
            with st.expander("Completed checks · saved findings", expanded=False):
                for item in completed:
                    st.markdown("**" + item["label"] + "**")
                    st.write(done[item["id"]])
        if current_case["status"] == "resolved":
            st.success("Fictional service recovery verified. The case is resolved; the precise root cause still needs review.")
            if st.button("Finish pitch · Beyond the prototype", key="pitch_finish_demo", use_container_width=True):
                st.session_state["scout_pitch_section"] = "Beyond the prototype"
                st.switch_page("pages/Pitch.py")
        elif step:
            st.markdown(f"**Next check: {count + 1} of {len(DEMO_STEPS)}**")
            st.info("Audience question: " + step["question"])
            if st.button(step["label"], key=f"pitch_next_clue_{current_id}_{step['id']}", use_container_width=True, disabled=index is None):
                with st.spinner("Recording the finding and choosing the next check…"):
                    save_investigation_turn(
                        current_id, step["finding"], index, knowledge_index,
                        playbook_catalogue, use_knowledge=use_knowledge, k=k,
                        completed_check_id=step["id"],
                    )
                st.rerun()
        else:
            st.info("Audience question: the evidence points towards the new release. How would we know customers can actually pay again?")
            if st.button("Verify recovery and close the fictional case", key=f"pitch_verify_recovery_{current_id}", use_container_width=True, disabled=index is None):
                # Only the fictional team supplies recovery evidence. Scout
                # records it and requires the existing verified-resolution rule.
                add_note(current_id, "verified_resolution", DEMO_RECOVERY)
                saved = save_investigation_turn(
                    current_id, DEMO_RECOVERY, index, knowledge_index,
                    playbook_catalogue, use_knowledge=use_knowledge, k=k,
                )
                add_verification_review(current_id, saved["message_id"], "initial_reply", "supported", DEMO_REVIEW)
                set_case_status(current_id, "resolved")
                st.rerun()

if current_case and messages:
    st.markdown(f"### {current_case['title']}")
    st.caption(
        f"Case {current_case['id'][:8]} · "
        + ("Resolved" if current_case["status"] == "resolved" else "In progress")
        + f" · Last updated {current_case['updated_at'][:16].replace('T', ' ')} UTC"
    )
    st.caption("💬 Continue the conversation using **Reply to Scout** at the bottom of the screen.")
    with st.expander(
        f"📋 Full case log · {len(messages)} messages · {len(review_history)} human checks",
        expanded=False,
    ):
        st.caption(
            "This is the complete readable history for this investigation, "
            "including previous messages, source references, notes and human checks. "
            "The complete case ID is shown below; the first eight characters are "
            "only a shortcut."
        )
        st.markdown("**Unique case ID (full UUID)**")
        st.code(current_case["id"], language=None)
        readable_log = format_case_log(
            current_case, messages, notes, review_history,
        )
        st.text_area(
            "Full investigation transcript · scroll to read or copy",
            value=readable_log,
            height=460,
            disabled=True,
            key=f"scout_full_log_{current_case['id']}",
        )
        st.download_button(
            "Download full readable log (.txt)",
            data=readable_log,
            file_name=f"scout_case_{current_case['id'][:8]}_full_log.txt",
            mime="text/plain",
        )
        st.caption(
            "For the complete machine-readable evidence, use "
            "**Case record → Export this investigation (JSON)** below."
        )

# A first-time user should start in the middle of the page, not by managing
# cases in the sidebar or finding the small chat box at the very bottom.
opening_question = None
if not messages and (not current_case or current_case["status"] == "open"):
    st.markdown("### Start here — tell Scout what’s going wrong")
    st.write(
        "You don't need to select or set up anything first. Describe the problem "
        "in your own words and Scout will start an investigation. "
        "You'll be able to add more information as you go."
    )
    st.markdown(
        "**Helpful details, if you have them:** Which system is affected? "
        "When did it start? What errors are you seeing? Did anything change recently?"
    )
    st.caption("Don't have all the answers? That's fine. Scout can ask follow-up questions.")

    examples = [
        (
            "API timeouts",
            "Our API has been returning 504 Gateway Timeout errors since this "
            "morning. Some customers can't complete requests. Where should we start?",
        ),
        (
            "Checkout failures",
            "Our checkout service has been failing intermittently since Tuesday. "
            "We're seeing slow database connections and API timeouts. Could they be linked?",
        ),
        (
            "App keeps restarting",
            "One of our Kubernetes pods keeps restarting after a deployment. "
            "What should we investigate first?",
        ),
    ]

    def use_opening_example(example: str) -> None:
        # Called before the text input is instantiated on the next rerun.
        st.session_state["scout_opening_message"] = example

    st.caption("Or try an example:")
    example_columns = st.columns(3)
    for column, (label, sample) in zip(example_columns, examples):
        with column:
            st.button(
                label, key=f"scout_start_example_{label.replace(' ', '_')}",
                use_container_width=True,
                on_click=use_opening_example,
                args=(sample,),
            )

    with st.form("scout_opening_form"):
        draft = st.text_area(
            "Describe your incident",
            key="scout_opening_message",
            placeholder=(
                "For example: Our checkout is timing out. It started yesterday, "
                "and we deployed a change the night before…"
            ),
            height=155,
            max_chars=5000,
        )
        # Source retrieval and checked plans work even when Ollama is offline.
        can_answer = index is not None
        submitted = st.form_submit_button(
            "Start investigation",
            type="primary",
            use_container_width=True,
            disabled=not can_answer,
        )
    if not can_answer:
        if index is None:
            st.info(
                "To start, Scout needs the SevAnalysis incident file. "
                "Open Data and search settings in the sidebar to upload it."
            )
        else:
            st.info("Local evidence and checked guidance are available without an AI model.")
    if submitted:
        if draft.strip():
            opening_question = draft.strip()
        else:
            st.warning("Tell Scout a little about the problem first.")

# During the pitch, show the latest exchange so the audience doesn't have
# to scroll past every technical reply. Nothing is removed from SQLite:
# the Full case log above still contains every message and its evidence.
visible_messages = messages
if st.session_state.get("scout_pitch_mode", False) and is_demo_case(current_case):
    if len(messages) > 2:
        st.caption("Earlier exchanges are saved in Full case log. Showing the latest clue and Scout's response.")
        visible_messages = messages[-2:]

for message in visible_messages:
    is_assistant = message["role"] == "assistant"
    with st.chat_message(
        "assistant" if is_assistant else "user",
        avatar="🧭" if is_assistant else "👤",
    ):
        # The speaker labels make the distinction clear even when emoji avatars
        # aren't rendered. Colours are visual aids; the role is also written out.
        if is_assistant:
            st.markdown(
                '<div class="scout-speaker scout-speaker-assistant">Scout</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="scout-speaker scout-speaker-user">You</div>',
                unsafe_allow_html=True,
            )
        st.markdown(message["content"])
        evidence = message.get("evidence", {})
        if is_assistant:
            show_human_check(
                current_id, message["id"], evidence, "initial_reply",
                latest_reviews.get((message["id"], "initial_reply")),
                bool(current_case and current_case["status"] == "open"),
            )
            investigation_step_cards(
                evidence.get("playbooks", []),
                demo_numbering=bool(st.session_state.get("scout_pitch_mode", False) and is_demo_case(current_case)),
            )
            if evidence.get("model_draft"):
                with st.expander("AI interpretation · generated separately (unverified)"):
                    st.caption(
                        "This is LLM-generated commentary, not a checked "
                        "investigation procedure or a confirmed diagnosis. "
                        "Use the reviewed guides above for any suggested actions."
                    )
                    st.markdown(evidence["model_draft"])
                show_human_check(
                    current_id, message["id"], evidence, "ai_interpretation",
                    latest_reviews.get((message["id"], "ai_interpretation")),
                    bool(current_case and current_case["status"] == "open"),
                )
        cited = set(evidence.get("cited_ids", []))
        if is_assistant and cited:
            with st.expander(f"Sources used ({len(cited)})"):
                for incident in evidence.get("incidents", []):
                    if incident["doc_id"] in cited:
                        st.write(f"**Historical report:** {incident['vendor']} · {incident['title']}")
                        if incident["source_url"]:
                            st.link_button("Open incident", incident["source_url"])
                for guide in evidence.get("guides", []):
                    if guide["kb_id"] in cited:
                        st.write(f"**Technical guide:** {guide['publisher']} · {guide['title']}")
                        st.link_button("Open guide", guide["url"])


# The normal investigator can record a completed check and move forward too.
# A review of Scout's advice is separate from completing the actual procedure.
if current_case and current_case["status"] == "open" and messages:
    latest = messages[-1]
    remaining = latest.get("evidence", {}).get("playbooks", []) if latest["role"] == "assistant" else []
    if remaining and not (st.session_state.get("scout_pitch_mode", False) and is_demo_case(current_case)):
        first = remaining[0]
        with st.expander("Record the result of the next investigation check", expanded=False):
            st.write("**" + first["title"] + "**")
            st.caption("Enter what you actually checked and found. This records a human-reported result, not independent verification by Scout.")
            with st.form("scout_check_result", clear_on_submit=True):
                finding = st.text_area("What did this check establish?", max_chars=3000)
                if st.form_submit_button("Save result and continue", disabled=index is None):
                    if finding.strip():
                        save_investigation_turn(
                            current_id, finding, index, knowledge_index,
                            playbook_catalogue, use_knowledge=use_knowledge, k=k,
                            completed_check_id=first["id"],
                        )
                        st.rerun()
                    else:
                        st.warning("Record a finding before completing the check.")

# Stage B is explicitly requested. Stage A (retrieval + checked plan) was saved
# by the submit handler below and is already usable even with Ollama switched off.
# Attach generated commentary to that same saved assistant message, rather than
# inserting a second instruction plan or losing the source snapshot.
if (
    current_case and current_case["status"] == "open"
    and messages and messages[-1]["role"] == "assistant"
    and mode != "Evidence only (no LLM)"
):
    latest_reply = messages[-1]
    latest_evidence = latest_reply.get("evidence", {})
    if not latest_evidence.get("model_draft"):
        if model_ready:
            st.caption(
                "The evidence and checked steps above are ready now. "
                "AI interpretation is optional and may take over a minute "
                "on a CPU-only local model."
            )
            if st.button(
                "Ask AI to interpret this case",
                key=f"scout_generate_interpretation_{latest_reply['id']}",
            ):
                fresh_messages = get_messages(current_id)
                fresh_notes = get_notes(current_id)
                latest_question = next(
                    (entry["content"] for entry in reversed(fresh_messages)
                     if entry["role"] == "user"),
                    "",
                )
                incident_cards = latest_evidence.get("incidents", [])
                permitted_incidents = set(
                    latest_evidence.get("supporting_incident_ids", [])
                )
                llm_incidents = [
                    record for record in incident_cards
                    if record.get("doc_id") in permitted_incidents
                ]
                checked_guides = latest_evidence.get("playbooks", [])
                with st.spinner(
                    "Llama is generating an optional interpretation. "
                    "The checked plan above is already saved."
                ):
                    try:
                        ai_result = answer_with_llm(
                            latest_question,
                            llm_incidents,
                            api_key=api_key,
                            model=model,
                            base_url=base_url,
                            knowledge_results=latest_evidence.get("guides", []),
                            case_context=case_context_for_model(
                                fresh_messages, fresh_notes,
                            ),
                            playbooks=checked_guides,
                            max_tokens=200 if checked_guides else 250,
                        )
                        update_assistant_evidence(
                            current_id, latest_reply["id"], {
                                "model_draft": ai_result["answer"],
                                "model_draft_cited_ids": ai_result["cited_ids"],
                                "model": ai_result.get("model", model),
                                "seconds": ai_result.get("seconds", 0),
                                "tokens": ai_result.get("tokens", 0),
                            },
                        )
                    except Exception as exc:
                        st.error(
                            "The AI interpretation couldn't be generated. "
                            "Your checked plan and case history are saved."
                        )
                        with st.expander("Connection details"):
                            st.code(str(exc))
                    else:
                        st.rerun()
        else:
            st.caption(
                "The checked investigation is available now. "
                "Start Ollama or configure a hosted provider to add optional AI commentary."
            )

# A case record is useful after the conversation begins. Before then it is
# an empty administrative form, so keep it off the opening screen.
if current_case and messages:
    with st.expander(f"Case record · {len(notes)} notes", expanded=False):
        st.caption(
            "Scout keeps the conversation. Use these notes to distinguish things "
            "you've confirmed from things you're still testing. Scout cannot "
            "verify a finding just because it sounds plausible."
        )
        note_labels = {
            "confirmed_fact": "Confirmed fact (checked by me)",
            "observation": "Observation (reported, not yet verified)",
            "hypothesis": "Hypothesis to test",
            "verified_resolution": "Verified resolution (checked by me)",
        }
        for note in notes:
            st.markdown(f"**{note_labels.get(note['kind'], note['kind'])}**")
            st.write(note["content"])
        if review_history:
            st.markdown("**Human-check history**")
            st.caption(
                "Each review applies to one saved reply or AI interpretation. "
                "Earlier decisions remain in the record when a new review is added."
            )
            for review in review_history:
                subject = (
                    "Investigation reply" if review["target"] == "initial_reply"
                    else "AI interpretation"
                )
                status = {
                    "supported": "Supported finding",
                    "not_supported": "Finding not supported",
                    "uncertain": "Still uncertain",
                }[review["outcome"]]
                st.markdown(
                    f"**{subject} · {status}** "
                    f"(reply {review['message_id']}, {review['created_at'][:16]} UTC)"
                )
                st.write(review["detail"])
        if current_case["status"] == "open":
            with st.form("scout_note_form", clear_on_submit=True):
                note_kind = st.selectbox(
                    "What type of note is this?",
                    list(note_labels),
                    format_func=lambda value: note_labels[value],
                )
                note_content = st.text_area(
                    "Finding or detail",
                    placeholder="For example: Database connection usage peaked at 95% just before timeouts began.",
                    max_chars=3000,
                )
                if st.form_submit_button("Save to case record"):
                    if note_content.strip():
                        add_note(current_id, note_kind, note_content)
                        st.rerun()
                    else:
                        st.warning("Add the detail before saving.")

        st.divider()
        case_export = json.dumps(export_case(current_id), indent=2, ensure_ascii=False)
        st.download_button(
            "Export this investigation (JSON)",
            data=case_export,
            file_name=f"scout_case_{current_id[:8]}.json",
            mime="application/json",
        )

        if current_case["status"] == "open":
            has_verified_resolution = any(
                note["kind"] == "verified_resolution" for note in notes
            )
            if has_verified_resolution:
                if st.button("Mark case as resolved"):
                    set_case_status(current_id, "resolved")
                    st.rerun()
            else:
                st.caption(
                    "To close a case, first record a verified resolution above. "
                    "Scout's suggested fixes do not count as verified."
                )
        else:
            if st.button("Reopen this case"):
                set_case_status(current_id, "open")
                st.rerun()

    # Show source searches for the latest answer, even after an app restart.
    last_answer = next(
        (message for message in reversed(messages) if message["role"] == "assistant"),
        None,
    )
    if last_answer and last_answer.get("evidence"):
        last_sources = last_answer["evidence"]
        with st.expander("Explore the evidence behind the latest answer", expanded=False):
            tab_names = ["Historical incidents", "Technical guidance", "Keyword baseline"]
            if last_sources.get("model_draft"):
                tab_names.append("Original AI draft")
            tabs = st.tabs(tab_names)
            t_inc, t_kb, t_base = tabs[:3]
            with t_inc:
                historical = last_sources.get("incidents", [])
                if not historical:
                    st.caption("No closely related historical reports were retrieved.")
                if len(last_sources.get("supporting_incident_ids", [])) < len(historical):
                    st.info(
                        "Some results are useful search leads, but aren't evidence "
                        "that several symptoms share the same cause."
                    )
                for item in historical:
                    source_card(item)
            with t_kb:
                guides = last_sources.get("guides", [])
                if not guides:
                    st.caption("No technical guide was retrieved for this question.")
                for item in guides:
                    knowledge_card(item)
            with t_base:
                st.caption("A simple keyword search, retained for the course comparison.")
                for item in last_sources.get("baseline", []):
                    source_card(item)
            if last_sources.get("model_draft"):
                with tabs[3]:
                    st.warning(
                        "This is the unedited language-model output retained for "
                        "evaluation. It may contain unsupported technical suggestions "
                        "or a different action order. Use the checked guides in "
                        "the main conversation for procedures."
                    )
                    st.markdown(last_sources["model_draft"])
                    if last_sources.get("model_draft_cited_ids"):
                        st.caption(
                            "Citation IDs used in the original model draft: "
                            + ", ".join(last_sources["model_draft_cited_ids"])
                        )

if not current_case or current_case["status"] == "open":
    # The guided form is the first-message input. Once the user has described
    # the case, switch to the familiar chat input for conversational follow-ups.
    question = opening_question
    if messages:
        question = st.chat_input(
            "Reply to Scout — add details, results or a follow-up question…",
            disabled=(index is None),
        )
    if question:
        # A first message creates the case; later messages continue it.
        if not current_case:
            current_case = create_case(question)
            current_id = current_case["id"]
            # The real case is the durable selection. Streamlit may reset
            # the sidebar widget when the case list changes after this message.
            st.session_state["scout_current_case"] = current_id
            st.session_state["scout_pending_case"] = current_id
        else:
            # The Start button creates a real case before the first question.
            # Use that question to replace its placeholder name once only.
            title_case_from_first_message(current_id, question)
        st.session_state["scout_reset_opening_message"] = True
        with st.spinner("Scout is looking through the case and supporting references…"):
            save_investigation_turn(
                current_id, question, index, knowledge_index,
                playbook_catalogue, use_knowledge=use_knowledge, k=k,
            )
        st.rerun()
elif current_case:
    st.info("This investigation is resolved. Reopen it above if you need to add more information.")

st.markdown("---")
st.caption(
    "Scout stores case history on this computer using SQLite. "
    "This is a single-user learning prototype, not a secure company ticketing system. "
    "The case database stays out of GitHub. Never enter passwords, personal records "
    "or confidential tickets into a hosted model."
)
