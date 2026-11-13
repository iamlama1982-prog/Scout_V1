# Scout — AI-assisted incident investigator 🧭


**Submission version:** Scout_V1 contains the final project snapshot. The original [Scout development repository] retains the full development and testing history for the Git assessment criterion. 

**Ironhack Data Science & Machine Learning · Project 3 · LLM track (RAG)**

Scout helps an IT support engineer investigate a reported problem. It finds similar **published incidents**, offers **checked next steps**, and saves the conversation. It does **not** diagnose a live system or make repairs.

**My question:** Can I help someone choose a sensible next investigation step, with evidence they can check, instead of trusting an AI answer simply because it sounds convincing?

## 1. The user and the decision

The user starts with incomplete information — for example, "Our checkout API is returning 504 errors". They want to know **where to look next**, not receive an invented root cause.

- **Input:** the incident description, then new observations as the investigation develops.
- **Output:** linked historical reports, an ordered set of checked investigation steps, optional AI interpretation, and a saved case with human review notes.
- **The mistake I most want to avoid:** presenting an unsupported explanation or technical action as a verified fact.
- **How I assess it:** retrieval **Hit@5**, correctness and citations of the raw Llama answers, refusals when the data has no answer, and response time. The checked procedure and case workflow are tested separately.

## 2. Data and what I found

I used the public [SevAnalysis incident dataset](https://sevanalysis.com/data/) (**CC BY-NC 4.0**). Each row describes a vendor's published status-page incident. These are **not private support tickets or confirmed root-cause reports**. The downloaded CSV stays local.

| My real-data checks | Result | What it changed |
|---|---:|---|
| Original rows | 41,314 | I measured the actual file, not an estimated sample |
| Searchable rows | 41,171 | I removed 143 duplicates |
| Vendors | 364 | I kept vendor names and source links visible |
| Missing affected components | 72.94% | I couldn't rely on component categories alone |
| Median incident title | 6 words | I expected wording and abbreviation mismatches |
| Top 12 vendors' share | 36.23% | I treated vendor coverage as uneven, not as reliability scores |

The **actual charts and what I concluded** are in [Notebook 01](notebooks/01_framing_and_baseline.ipynb), with the full executed EDA in [Notebook 06](notebooks/06_source_eda.ipynb). Measurements and five plots are preserved in [reports](reports/).

## 3. Baseline, design choice and results

I compared two ways of finding a known published incident, using the **same 12 answerable questions**. Hit@5 means the expected incident ID appeared in the first five results.

| Retriever | Hit@5 | Average search time* |
|---|---:|---:|
| Keyword overlap — my baseline | **9/12 · 75.0%** | 0.551 s |
| TF-IDF, words and word pairs | **8/12 · 66.7%** | 0.007 s |

*Times are from the recorded local run, after the index was built.*

TF-IDF was much faster, but found **one fewer** expected incident. I kept it as a fast, straightforward prototype retriever and documented the misses rather than claiming it was more accurate. The failures included confusing suppliers, **APAC vs Asia-Pacific**, and different descriptions of the same support button.

### What happened when I tested Llama 3.2

I recorded **15 raw responses**: 12 historical questions plus **three deliberately unanswerable** questions.

| Strict provisional review | Result |
|---|---:|
| Correct historical answers | **4/12** |
| Expected incident ID cited | **3/12** |
| Both correct and cited | **2/12** |
| Clear refusals on unavailable information | **2/3** |
| Median recorded raw model time | **81.0 s** |

The correct incident was sometimes retrieved first **but Llama still said it could not find a match** (Azure and HeyGen). An earlier technical answer also proposed an unsupported PostgreSQL check. That is why I stopped letting the model decide the first investigation action.

**Evidence warning:** the 15 questions were prepared **after development**, not frozen before the build as the course rubric requests. The source records were cross-checked within the downloaded CSV, but not all original vendor pages were independently verified. Answer grades are **assistant-assisted and provisional** until human review. These results measure the **original raw Llama run**, not the newer checked-plan interface. [Read the complete evaluation](notebooks/03_evaluation.ipynb) and [failure report](reports/llm_evaluation_findings.md).

### Cost

The original evaluation logged **19,141 input tokens** and **4,314 output tokens**. Running Llama locally through Ollama produced **€0 of measured external API charges**, not zero computing cost. Electricity and device wear were not estimated. Time per question is in the committed [provisional evaluation record](reports/llm_provisional_review.csv); one extreme recorded delay of 52,047.6 seconds has an unknown cause. Optional hosted inference would have its own provider charges.

## 4. How the working product uses that evidence

1. **Retrieve:** clean the public records, build a TF-IDF index and show source-linked incident leads.
2. **Guide:** select from six checked investigation playbooks, backed by 18 technical reference cards. The selection uses the user's reported symptoms and technology; it is **not proof the steps apply to a live system**.
3. **Explain (optional):** ask local Ollama Llama 3.2 for a separate interpretation. The useful checked plan is shown **before** generation, so the user does not wait for Llama.
4. **Remember:** save the case, messages, source snapshots and notes in local SQLite. The full case log and unique case ID are visible in the app.
5. **Human check:** explain why a suggestion needs review, record a specific finding as supported, unsupported or uncertain, and keep the original response. The model cannot approve itself.

**This is a retrieval-augmented application, not a model I trained from scratch.** I used AI-assisted coding to help implement and debug parts of Scout; my [code tour](docs/code_tour.md) explains how the main components work. There is no access to live company infrastructure and no automatic fix execution.

## Live product pitch (10 minutes)

Choose **Product pitch → Intro to Scout** for a short visual story of
the problem, sources and build decisions behind Scout, then **Live Scout** for an online-shop investigation that needs no IT knowledge.
Return to **Product pitch → Beyond the prototype** for the close. Presenter
controls offer a clearly labelled fictional checkout case, five completed
check results, and a simulated recovery review that closes the case.
All replies use the same retrieval, guide and SQLite workflow as ordinary
Scout, without a fresh slow Ollama call. Completed guides are removed from the
next-action list only after the investigator records a finding. The fictional
case records verified service recovery, not an independently proven root cause. The full charts stay in
**Evidence & charts**. [Presenter runbook](docs/project3_presentation_runbook.md) · [Separate speaking notes](docs/presenter_speaking_notes.md).

This is a **product concept pitch**, not a claim of measured customer ROI or
commercial traction. The current SevAnalysis data is CC BY-NC 4.0, so a
commercial version would need appropriately licensed data and further security
and user testing.

## 5. Run Scout from a fresh clone

Use **Python 3.12**. In PowerShell:

```powershell
git clone https://github.com/iamlama1982-prog/Scout_V1.git
cd Scout_V1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**Data:** Download `incidents.csv` from [SevAnalysis](https://sevanalysis.com/data/) and upload it in Scout's sidebar. Alternatively put it here:

```text
data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv
```

The snapshot name is a folder label, **not proof of download date**. The app can open without Ollama, using **Search + checked guides · No AI**.

**Optional local model:** install [Ollama](https://ollama.com/), run `ollama pull llama3.2` and start Ollama; then select the local-AI option in Scout. No hosted API key is needed for this route. If you choose a hosted provider, put its key in local environment variables, never in Git.

To check the code:

```powershell
python -m pytest -q
```

The real incident CSV and local case database (`data/scout_cases.db`) are ignored by Git. Never upload customer credentials or confidential incidents.

## 6. Repository structure and project documentation

I kept the template's three-part notebook sequence. My descriptive filenames for 02 and 03, and the root Streamlit entry point plus separate modules, serve the same roles as the course's `02_build.ipynb`, `03_evaluate.ipynb`, `app/streamlit_app.py` and `src/functions.py`. I use the same sequence without duplicating the implementation.

| In the template's order | My work | What to look for |
|---|---|---|
| **01 · Frame, explore and baseline** | [Notebook 01](notebooks/01_framing_and_baseline.ipynb) | User, question, real-data EDA, 15-question design and keyword baseline |
| **02 · Build the LLM pipeline** | [Notebook 02](notebooks/02_rag_build.ipynb) | TF-IDF retrieval, cited sources, grounded prompt, checked steps and the staged app |
| **03 · Evaluation report** | [Notebook 03](notebooks/03_evaluation.ipynb) | Hit@5, raw answers, individual failures, model speed, cost and limitations |
| **App and demonstration** | [Run Scout](app.py) · [Product pitch](pages/Pitch.py) · [Evidence & charts](pages/Presentation.py) | Real conversation, retrieved sources, checked guide, human review, complete case log |
| **Supporting work, not extra core notebooks** | [04 · Case memory](notebooks/04_case_memory.ipynb) · [05 · Checked guides](notebooks/05_checked_guides.ipynb) · [06 · Full data EDA](notebooks/06_source_eda.ipynb) | How I tested decisions and saved the full EDA charts |
| **Measurements** | [Reports](reports/) · [15 questions](evals/incident_eval_questions_provisional.csv) | Source counts, per-question retrieval outcomes, provisional Llama review |
| **Project code** | [src](src/) · [tests](tests/) | Reusable functions and checks; the UI is in `pages/Scout.py`. [Plain-English code tour](docs/code_tour.md) |

The [**full 11-part project rubric**](https://github.com/iamlama1982-prog/project-3-ai-product/blob/main/RUBRIC.md) is my assessment reference. [This short rubric check](docs/rubric_alignment.md) shows where the evidence is, including gaps I have **not** claimed to close.

**Presentation:** the ten-minute product pitch opens with **Product pitch → Intro to Scout**, followed by **Live Scout**. **Evidence & charts** contains the detailed measurements and limitations. The complete methodology remains in the notebooks.

## 7. What I would and wouldn't trust

**I would use Scout** as a local prototype to structure a discussion, find published parallels and decide what to investigate. **I would not ship it** as a verified diagnosis engine or for shared confidential case storage. Sources may lack technical detail, retrieval can miss relevant documents, Llama can ignore or misrepresent good evidence, and human-check records rely on what the reviewer says they checked.

My next evaluation would use **independently written unseen questions**, confirmed original source pages, and a separate test of the checked plan's usefulness and real UI timing. Passing software tests is not an AI accuracy score.

*Data credit: SevAnalysis, public vendor status-page incidents, CC BY-NC 4.0. Scout is an educational, single-user prototype.*
