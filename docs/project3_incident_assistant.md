# Project 3 — Incident Investigator (LLM track)

> **Development notes:** I kept this record of how the feature evolved. Some descriptions refer to earlier versions. The [final README](../README.md), [code tour](code_tour.md) and [presentation runbook](project3_presentation_runbook.md) describe the submitted Scout app.

## Purpose

**User:** IT support specialist or engineer investigating a newly reported service incident.

**Question:** Can retrieval plus a source-grounded LLM help find and understand relevant historical incidents, compared with simple keyword search?

**Product:** The standalone Scout Streamlit application. The original four-dataset analytical project remains intact, but the AI assessment focuses on one main dataset and one RAG assistant.

## Primary data source

**[SevAnalysis — official downloadable incidents.csv](https://sevanalysis.com/data/)** · CC BY-NC 4.0, educational and non-commercial use with attribution.

Each row is a vendor-reported public service-status incident, **not** an internal support ticket. The publisher updates the file regularly, so use the actual downloaded snapshot count. Our original exploration used 40,188 rows.

Download incidents.csv from the original publisher page and either upload it in Incident Investigator or save it locally at data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv.

Do not commit the raw dataset. Keep private tickets and identifying details out of hosted LLM calls.

## System design

1. Read and profile incident titles, vendor, published times, status, impact, components, source IDs and URLs.
2. Exclude empty titles/vendors, deduplicate source records and generate stable citation IDs. Mask common contact details before external API use.
3. Build a TF-IDF word and bigram index over published titles and operational context.
4. Use basic word-overlap search as the **baseline**.
5. Retrieve the most relevant published records for a question.
6. With a configured model, send **only retrieved evidence** to an OpenAI-compatible LLM (hosted or local Ollama). The prompt requires source IDs and warns against guessing diagnoses or fixes.
7. Present the answer and clickable original vendor-source evidence. Without a model, the page works as retrieval-only mode; that is **not** a full RAG demonstration.

A connected LLM now produces **separate sections for historical evidence, unverified explanations to test, safe next diagnostic checks, and unknowns**. Troubleshooting suggestions may use the model's general technical knowledge, but must never be presented as solutions confirmed by SevAnalysis. Without an installed model or valid API key, this is **retrieval only**.

**Local Ollama setup (Windows):** Install from https://ollama.com/download/windows, run 'ollama pull llama3.2' in PowerShell, ensure the Ollama app is running, then use the 'Ollama running locally' mode in Streamlit. The page now checks whether the local server is reachable and whether the selected model exists. On Streamlit Cloud, localhost refers to the cloud server, not your own PC.

The source root-cause and failure-mode labels may be model-enriched and are **not verified ground truth**. Similar titles do not prove a shared root cause. The publisher often lacks resolution procedures or internal logs.

## Run

From the root of this standalone Scout repository:

    python -m pip install -r requirements.txt
    streamlit run app.py

This Streamlit entry point opens the standalone Scout application. The earlier operations dashboards are preserved in the separate Ops Sentinel repository. Download incidents.csv from SevAnalysis and upload it or place it in the documented local path.

To generate an LLM answer, choose a hosted API and enter a key privately, or start Ollama locally and choose its OpenAI-compatible endpoint. Ollama on your own machine does not automatically work from Streamlit Cloud.

## Evaluation protocol

For my evaluation protocol I set up **15 questions**, including **3 that the public dataset cannot answer**, with linked expected sources for the remaining 12. The course brief requires at least 15 evaluation questions written before building. I developed Scout before freezing this set, so the initial run is retrospective and does not meet that timing requirement.

1. Run 'python -m scripts.build_incident_eval_set' to create a **draft** 15-question, source-linked file from the real CSV.
2. Review every row with the original vendor source, paraphrase several overly literal title-based questions, check the expected ID, and set reviewed_by_human=True for approved rows. Freeze the questions. The generator will not overwrite an existing set.
3. Run 'python -m scripts.evaluate_incident_assistant'. This saves a side-by-side keyword/TF-IDF hit@5 result with retrieval latency.
4. When an LLM is configured, run 'python -m scripts.evaluate_incident_llm --model gpt-4.1-mini --input-price PRICE --output-price PRICE'. Prices are USD per **million** input/output tokens; verify current rates. For local Ollama, pass --base-url http://localhost:11434/v1 and an installed model.
5. Manually mark answer correctness, citation support, proper refusals and whether errors came from retrieval or generation. Report hit@5, time/question, token usage, actual/estimated total cost, errors and examples.

**Measured local retrieval result (November 2026):** I tested against the downloaded full incident snapshot using 12 known-incident questions plus three out-of-scope questions. Keyword overlap found 9/12 expected sources within the first five results (75.0%, 0.551 seconds mean query time), and TF-IDF found 8/12 (66.7%, 0.007 seconds). These are retrospective, provisional retrieval results pending independent publisher-page review, and the times exclude index construction. The [checked-in evaluation report](../reports/retrieval_findings.md) and [evaluation notebook](../notebooks/03_evaluation.ipynb) contain the individual hits and errors. **Human-scored LLM correctness, refusals and generation cost are still outstanding.** The public CSV is present locally, not included in GitHub.

## Conversations and local case memory

Scout now stores each investigation in a local SQLite file at data/scout_cases.db. A case contains the conversation, source references and human-labelled notes; the user can reopen it after a refresh or restart. Follow-up questions reuse the original problem and recent conversation. An earlier LLM suggestion is **not** automatically a verified fact. A person must enter a verified resolution before marking the case resolved.

There is no cross-case learning, authentication, cloud database or automatic repair in this prototype. The saved case database is ignored by GitHub and is only for a single-user local demonstration. This is still the same incident RAG project, not an additional machine learning task.

The full design, explanation, example workflow and tests are in [Scout case memory](scout_case_memory.md) and [notebook 04](../notebooks/04_case_memory.ipynb).

## Scout — product experience

The Project 3 Streamlit page presents the assistant as **Scout**, part of Ops Sentinel. Scout is the interface persona and evidence-grounded prompt; **Llama 3.2 running in Ollama is still the underlying local model**. This is not a separately trained model.

The page now gives users a short introduction, example questions, a more readable investigation report and source links collected beneath each answer. Settings such as the model endpoint, raw CSV upload and keyword-search baseline remain accessible without dominating the user experience.

The assistant is prompted to answer in direct, natural British English: what it found, where it would start, what might explain the symptoms and the few details that would help narrow things down. It must not use vaguely similar incidents as explanations or present a vendor documentation card as a confirmed fix. Invalid citation IDs are removed from the text, flagged to the user and retained as a testable warning rather than shown as an awkward placeholder.

**Try locally:** Run app.py, choose **Ask Scout · Local AI** and confirm Ollama is ready. Start a case with an incident description, add a short follow-up such as a confirmed database technology, then reopen the case after refreshing. Switch off technical guidance for a source comparison. **Search only · No AI** remains available for retrieval without generation.

**Evaluation note:** A friendlier tone is a UX adjustment, not evidence of greater factual accuracy. Human grading of correctness, usefulness, source support and unsupported conclusions remains necessary.

## Curated technical guidance (implemented)

A second, **separate** knowledge collection now contains **18 short, original reference cards** in [knowledge/official_guides.json](../knowledge/official_guides.json). Each card links directly to an official AWS, Kubernetes, Google Cloud, Microsoft, PostgreSQL, MDN or Cloudflare reference checked on **9 November 2026**. We do **not** scrape or mirror whole manuals. The JSON records the publisher, link, review date, topic, applicability and two read-only investigation checks. An official source is not proof of a root cause for an individual incident.

The app now shows two independent retrieval tabs:
- **Historical incidents:** SevAnalysis vendor status reports and original incident URLs (INC citation IDs).
- **Technical guidance:** Curated reference cards, official links and specific checks conditional on the technology involved (KB citation IDs).

With Ollama or a hosted model connected, the answer is prompted to distinguish reported history, possible explanations, source-backed diagnostic checks and missing evidence. A supplied reference does **not** mean the current system uses that technology or that the referenced check is a confirmed fix. The app never executes troubleshooting actions. If no suitable reference is found, the LLM must identify its suggestions as general reasoning.

### Run and compare

1. From your existing project directory run 'git pull' and reopen the Streamlit **Incident Investigator** page. Your existing SevAnalysis CSV is reused from data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv.
2. Leave **Use curated technical guidance** enabled in the sidebar. Select **Ollama running locally** and the installed 'llama3.2' model. No new dependency is needed beyond requirements.txt.
3. Try: **"Our API keeps returning 504 gateway timeouts. What checks should we make first?"**
4. Inspect both source tabs. Check for historical [INC-...] citations and technical [KB-...] citations in the answer. If the relevant stack is unknown, recommendations must remain conditional.
5. Repeat the **same question** with **Use curated technical guidance** off. This isolates what the source-backed troubleshooting collection adds.

### Evaluation

The historical-retrieval comparison is based on the recorded 15-question protocol, of which 12 are answerable from the published incident data. We have added a separate [15-question technical-guidance evaluation draft](../evals/technical_guidance_review_draft.csv): 12 realistic technical questions with expected reference IDs and three questions that should not be answered as facts. **Review and approve these manually before using them as a fixed assessment set**; it is not a measured accuracy report.

After freezing the main question set, run *two separate LLM evaluations* over exactly the same questions and model:

    python -m scripts.evaluate_incident_llm --model llama3.2 --base-url http://localhost:11434/v1 --out outputs/project3/llm_incidents_only.csv
    python -m scripts.evaluate_incident_llm --model llama3.2 --base-url http://localhost:11434/v1 --with-knowledge --out outputs/project3/llm_with_technical_guidance.csv

The two outputs capture retrieved IDs, knowledge IDs, citations, generation time and manual review fields. Do not report any accuracy, effect or improvement until the paired runs have been evaluated. The reference question draft can be used for additional manual scenario reviews. For an external paid model, separately supply and verify its actual per-million-token prices.

**Boundaries:** Relevance is still TF-IDF, not semantic embeddings. The cards are reviewed source summaries, not a comprehensive or live technical knowledge base. Model outputs are untrusted until manually checked, and documentation may change after the recorded review date.

## Scope control

The wider Ops Sentinel model experiments, predictive risk work, reusable company onboarding, automated ticket refresh, Supabase, regression and MLOps are not mandatory for this Project 3 sign-off. The deliverable is **one evaluated incident investigation assistant** with its source evidence and a clear baseline.
