# Project 3 rubric check — Scout

I compared Scout with the [Project 3 template](https://github.com/iamlama1982-prog/project-3-ai-product) and [full rubric](https://github.com/iamlama1982-prog/project-3-ai-product/blob/main/RUBRIC.md). This is an **evidence map, not my own grade**. I have not filled gaps by claiming work that did not happen.

| Rubric criterion | Where I show it | Honest status |
|---|---|---|
| 1. Problem framing | README §1; notebook 01; notebook 03 conclusion | Defined IT investigator, inputs, next-step decision and the cost of an unsupported answer |
| 2. Data preparation | Notebooks 01 and 06; `src/incident_assistant.py` | 41,314 rows, 143 duplicates removed, missingness measured; common email and phone patterns masked, not a comprehensive PII detector; raw CSV kept out of Git |
| 3. EDA | Notebook 01 overview; executed notebook 06; five source-EDA charts | Measured component missingness, short titles, vendor concentration, dates and impact labels; each interpreted |
| 4. LLM pipeline | Notebook 02; `src/incident_assistant.py`, `src/scout_playbooks.py` | Keyword baseline versus TF-IDF, grounded Llama prompt, citations, checked guides and optional staged interpretation |
| 5. Evaluation | Notebook 03; `evals/`; `reports/` | 15 recorded questions, retrieval hit@5, provisional answer/citation/refusal review, failure categories and timings. **Limitation:** questions were not prospectively frozen; human source approval is outstanding. This is a gap against the course's stated minimum pre-build evaluation requirement, not just an advanced criterion. |
| 6. App | `app.py`, `pages/Scout.py` | Working local Streamlit investigator, cached search index, source links, case record, explicit completed-check results, human review and case closure. The corrected multi-case demo was confirmed working in the browser; final intro visual check remains |
| 7. Visuals | Source EDA charts in 01/06; baseline and LLM charts in 03; in-app presentation | Actual labelled plots and a written decision from each, not decorative figures |
| 8. Code structure | `src/`, `scripts/`, `tests/` | Reusable Python modules; six notebooks include three core notebooks and three supporting investigations. Core notebooks execute in CI with committed summaries; actual downloaded-data execution is a separate local check |
| 9. Git | Commit history; `.gitignore` | Frequent descriptive commits and CI; main-branch work does **not** meet an optional advanced branch-workflow example. No raw dataset or keys included |
| 10. Documentation | README; code comments; data README; focused support docs | Reproduction, source attribution, scope, limitations, model cost and [code tour](code_tour.md) |
| 11. Presentation | Product pitch, Live Scout, Evidence & charts | Ten-minute product pitch: Intro to Scout, full investigation and close. Final timed rehearsal remains |

## Three distinctions I want to keep clear

1. **Observed data quality and query timings** are not the same as approved model correctness.
2. The **15 raw Llama answers** were graded provisionally. The checked-guide system was added later and has not inherited those accuracy scores.
3. **GitHub CI passing** means the tested code behaved as expected. It does not verify the original reports, the live system, or AI advice.

## Repository structure and course template

The template explicitly says it is a **place to start, not a layout to copy exactly**. Scout uses `app.py` and `pages/` for its three Streamlit pages, and keeps reusable code in smaller, named `src/` modules rather than a large `src/functions.py`. This serves the same purpose without creating dummy files or maintaining duplicate implementations.

The three main notebooks map to the template's 01/02/03 sequence. Notebooks 04–06 are supporting evidence; they are not additional modelling tracks.

## Remaining validation

- Check the 12 original published status pages, question ambiguity and provisional scores.
- Rerun the three core notebooks in a fresh local kernel with the downloaded CSV.
- Check the presentation on the local machine and confirm the ten-minute running order.

No claims of a newly trained model, verified root cause, live remediation or production-ready data security.
