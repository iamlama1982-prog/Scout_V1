# Scout — conversations and case memory

> **Development notes:** I kept this record of how the feature evolved. Some descriptions refer to earlier versions. The [final README](../README.md), [code tour](code_tour.md) and [presentation runbook](project3_presentation_runbook.md) describe the submitted Scout app.

## Why I added this

My original Incident Investigator could answer a single question, but every follow-up started from scratch. That is not how people investigate a real problem. Someone might report an API timeout, then tell us later what database they use or what changed just before the fault began. Those details need to build on one another.

I wanted Scout to **keep the investigation together**: the questions, earlier answers, checked facts, ideas we're still testing, and finally what we actually confirmed.

This extends the Project 3 assistant. It is not another prediction model or another external dataset.

## The practical design

I chose **SQLite** because Python already includes it, and I only need a small local database for this version. I don't need to configure a server or pay for a hosted service.

- **Cases** have an ID, a short title, dates and a status (open or resolved).
- **Messages** contain the user input, Scout's replies and any source links used in the answer.
- **Case notes** are stored separately so we can distinguish facts from ideas.

The three tables live in data/scout_cases.db, created **locally on the computer running Streamlit**. This file is excluded from GitHub. It is not automatically uploaded or shared.

| Note label | Meaning |
| --- | --- |
| Confirmed fact | The person investigating says they checked this. |
| Observation | Something reported or seen, not necessarily verified yet. |
| Hypothesis | A possible cause still being tested. |
| Verified resolution | The investigator says they checked what resolved the case. |

I chose separate labels deliberately. If Scout suggests a likely cause, that does **not** become an established fact by repetition. Only the user can record a verified resolution and close the case.

## Making the conversation easier to follow

I also made the user and Scout messages look different. The user has a person icon, a blue-toned message and a clear **You** label. Scout uses the compass and a green-toned message with its own name. The colour helps, but the written labels make the conversation understandable even without relying on colour. The reply field is also labelled more clearly, especially after longer answers.

These are interface changes only. They do not affect the stored messages, the retrieved evidence or the LLM's reasoning.

## What happens when I add a follow-up?

1. Scout saves the new message under the selected case.
2. It searches using the **original problem plus the latest detail**. A follow-up such as "We're using PostgreSQL" isn't searched without the earlier API timeout context.
3. It includes a short portion of the existing conversation and labelled notes in the LLM prompt. Previous Scout answers are explicitly described as **unverified suggestions**.
4. The model generates the next response, citing any useful incident reports or technical guides retrieved.
5. The answer and its source links are saved to the case, which can be reopened later.

The full conversation stays in SQLite. Only the recent history and selected notes go into the prompt to keep it manageable. This is **retrieval-based memory, not retraining the model**.

## What I deliberately didn't add

- No automatic changes to live IT systems.
- No automatic promotion of AI guesses to verified organisational knowledge.
- No cross-case retrieval yet. Old cases can be reopened, but aren't used to answer a different case.
- No logins, customer separation or encryption. It is a single-user local learning prototype, **not a secure place for confidential production tickets**.
- No claim that a convincing LLM answer is a verified diagnosis.

If this develops into a product, it will need user permissions, company separation, security controls, backup and a suitable hosted database. Streamlit Community Cloud doesn't guarantee that local database files will survive restarts.

## Run Scout locally

In the project root in VS Code PowerShell:

    python -m pip install -r requirements.txt
    ollama pull llama3.2
    streamlit run app.py

Ollama needs to be running on the same computer only for optional AI interpretation. The retrieval and checked guides work without it. Download incidents.csv from https://sevanalysis.com/data/ and save it under data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv, or upload it using the sidebar.

**app.py launches only Scout.** The earlier analytical notebooks and control-room application are preserved in the [separate Ops Sentinel repository](https://github.com/iamlama1982-prog/ops_sentinal_final_project). Scout's repository contains only the files relevant to the RAG product.

### A simple demonstration

1. Scout opens on **Start here — tell Scout what's going wrong**. No need to choose a case in the sidebar. I can type an incident description, or tap one of the three examples to fill it in.
2. Click **Start investigation**. Scout creates a case automatically from that first message and gives an initial answer.
3. Reply: "We're using PostgreSQL, and we deployed a change on Monday." Scout should use this information alongside the original problem.
4. When the conversation has started, open **Case record** to save "We use PostgreSQL" as a **Confirmed fact**, or a possible shared dependency as a **Hypothesis**.
5. Refresh the browser and reopen the saved case from the left sidebar. The conversation and notes should still be available.
6. If a genuinely checked outcome is available, record it as a **Verified resolution** and close the case. Otherwise, leave it open.

**Why the interface is arranged this way:** the first job is explaining the incident, not choosing record-management options. The case record becomes relevant once the investigation has begun.

A case remains **open** until the investigator records evidence of verified resolution.

### Repeatable tests

    python -m pytest -q tests/test_scout_case_memory.py tests/test_incident_assistant.py tests/test_technical_knowledge.py

These tests use small made-up examples to check the software; they aren't evidence of model accuracy or real incident outcomes. They cover persistence, case separation, note labels, source references and passing history into the prompt. The actual LLM responses still need to be evaluated by a person on a frozen question set.

## Files to inspect

- app.py — the Streamlit entry point.
- pages/Scout.py — Scout's user interface.
- src/scout_case_store.py — SQLite storage and case operations.
- src/scout_conversation.py — turns the case history into relevant search and prompt context.
- src/incident_assistant.py — historical evidence retrieval and LLM integration.
- src/technical_knowledge.py and knowledge/official_guides.json — independent technical guidance.
- tests/test_scout_case_memory.py — tests for records, conversations and human-verified outcomes.
- notebooks/04_case_memory.ipynb — the steps explained in my own words.

## What still needs verification

The code is implemented and deterministic tests have been written. The local Ollama model still needs to be tested with a real follow-up conversation to judge whether it makes use of the extra context correctly. Reliable storage is not the same thing as a good investigation. I won't claim accuracy or improvement until the evaluation has been run and reviewed.
