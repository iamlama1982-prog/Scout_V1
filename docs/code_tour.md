# Scout — code and implementation guide

This guide explains the main components of Scout, my design decisions and the boundaries of the prototype. I used AI-assisted development to implement and debug parts of the application.

## Project structure

| Part | Where | Purpose |
|---|---|---|
| Framing and baseline | notebooks/01, 06 | Why the real records need cleaning; missing components; keyword baseline |
| Build | notebooks/02, 04, 05 | TF-IDF, evidence in a prompt, checked steps, case memory |
| Evaluate | notebooks/03; reports | Hit@5, missed cases, raw Llama errors, timing and limitations |
| Demo | app.py, pages/Scout.py, pages/Pitch.py | How an interaction calls reusable functions and saves the result |

## The main route through the code

`app.py` chooses the Streamlit page. `pages/Scout.py` handles buttons, inputs and what appears on screen. Both the normal chat and demonstration buttons call `src/scout_workflow.py: save_investigation_turn()`.

That function saves the user's message, reads previous messages and notes, builds a search question, retrieves incident and technical evidence, selects checked playbooks, makes the first source-led reply and saves it. It does not call Llama. The optional model call comes afterwards.

**Completing a check:** the investigator explicitly records a finding against the current guide. `completed_checks()` reads the guide IDs and results from saved confirmed-fact notes. Scout filters completed guides out of the next plan and acknowledges the finding. When no applicable checks remain, it summarises the findings and asks for evidence of recovery. The existing verified-resolution note and human review support closure. Scout doesn't infer completion from a chat message or independently verify a fix.

## 1. Data and retrieval — src/incident_assistant.py

- `prepare_incidents()`: loop through rows, clean text, skip missing titles/vendors and remove repeated source records using a set. A set stores unique values.
- `hashlib.sha256()`: make a repeatable fingerprint from vendor, source ID, time and title. The first 12 hex characters form the INC reference. It is a practical stable identifier, not an absolute collision guarantee. A case UUID is a different identifier.
- `IncidentIndex`: a dataclass is a convenient container holding the records, fitted vectorizer and matrix. No extra ML happens inside the dataclass.
- `build_index()`: scikit-learn's TfidfVectorizer learns weights for individual words and word pairs. The sparse matrix avoids storing a massive table of zeros. I use L2 normalisation (the library default).
- `keyword_search()`: turn the question into a set of words; compare it with each report. Score = matched question words divided by question-word count. The sort lambda means higher score first, then original row order. It is just a sort key.
- `retrieve()`: turn the question into a vector using the same fitted vectorizer. The dot product of the normalised vectors gives cosine similarity. Sort the scores, return the top k, and drop very weak matches. The 0.05 threshold is a prototype choice, not a calibrated confidence score.
- `historical_evidence_for_answer()`: simple pattern checks prevent a single-symptom match being used to connect several symptoms. This filters candidate evidence; it does not infer causal relationships.
- `build_messages()`: build instructions and supply source IDs, source text and case context. `answer_with_llm()` uses the OpenAI-compatible client with local Ollama or the chosen hosted endpoint, then filters citation IDs that weren't supplied. A valid ID still doesn't mean the claim is correct. I redact common email and phone patterns before preparing source text or sending a question/context to a model. This is not a complete personal-data detector; I keep confidential tickets out of the prototype.

## 2. Why the checked guides are separate

`src/technical_knowledge.py` loads a small catalogue of official reference cards, checks required fields and builds a second TF-IDF index. `src/scout_playbooks.py` loads the six authored playbooks and uses rule-based selection.

The selector checks words and patterns in what the user reported. It does not learn a classifier. A database mentioned in a retrieved public report doesn't mean the user's own system uses that database. The guide's applicability and priority are explicit rules.

`src/scout_response_flow.py` builds the first useful response without an LLM. The catalogue owns the checked instructions; a later model draft may interpret them but does not replace them. I haven't proved the selected steps are always the best next step.

## 3. SQLite — src/scout_case_store.py

SQLite is a local file database, so I don't need a separate server for the prototype. Four tables hold cases, messages, notes and verification reviews. Evidence is saved as JSON alongside the message.

A UUID identifies each case. Message and review IDs identify individual rows. Foreign keys link them together. SQL uses ? placeholders to pass values safely rather than joining a person's text into a SQL string. The context manager opens a connection for an action, commits or rolls back and then closes it. CREATE TABLE IF NOT EXISTS makes startup safe for existing records.

Human verification adds a new review row referencing the case and exact reply. It doesn't delete or edit previous reviews. A user-marked verified-resolution note is required before closing a case; it is not independent system verification.

## 4. Case memory and Streamlit state

`src/scout_conversation.py` combines the first user message, current update and recent confirmed notes for retrieval. It keeps model suggestions labelled as suggestions. It does not retrain Llama.

`source_snapshot()` saves the specific sources and playbooks displayed at the time of the answer. A later search or guide change doesn't overwrite previous evidence.

Streamlit reruns the page when a widget changes. Session state remembers which case and presenter controls are selected. SQLite saves the investigation across restarts. Cached index functions avoid refitting the TF-IDF index on every click. A pending-case key lets a new case be selected at the beginning of the next rerun, before the selectbox exists.

**My final demo bug:** identical demo titles could cause the case selector to return to a previously completed investigation. SQLite preserved the right records, but the UI could select the wrong case. I made the displayed label include the case ID and tied the presenter button key to the case ID and guide ID. I test preparing a new demo alongside an older demo with three completed checks. The new case must advance only to one completed check while the old case stays unchanged.

HTML/CSS is presentation styling, not ML code. The five introduction screens use a chapter number and ordinary if/elif branches. I kept the EDA and quantitative comparisons in Evidence & charts so the opening tells the product story. The presenter buttons submit fictional observations through the same save_investigation_turn function.

## 5. Tests and evaluation

Pytest checks functions and example workflows. Streamlit AppTest clicks controls without opening a real browser. Temporary files and small fictional fixtures isolate tests from actual data. CI runs these after GitHub changes.

The 15 recorded model answers are a different experiment: 12 known-source questions and three unanswerable ones. The question set is retrospective and scores are provisional. Tests do not prove the current app's accuracy, and the checked guidance has not inherited the raw Llama scores.

**Implementation boundaries:** the core combines data preparation, retrieval, RAG, evidence separation, SQLite and Streamlit. Advanced numerical optimisation, concurrent database access and production security are outside the scope of this local prototype.
