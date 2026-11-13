# Scout — final presentation runbook

**10 minutes, mostly in the live product.** My [speaking notes](presenter_speaking_notes.md) are separate from the app.

## Before class

1. Pull the latest repository and restart `python -m streamlit run app.py`.
2. Check the real SevAnalysis CSV loaded. The CSV and case database stay local.
3. Open **Product pitch → Intro to Scout**. Five short chapters tell the story of the problem, sources, turning point, build and product.
4. Prepare a **fresh** DEMO case in Live Scout before the talk. Older demo cases used the previous clue-only workflow; leave those saved and use the new case. Check the first recommendation is the timeline and the progress is 0/5. Note the active case ID; it must stay the same throughout the demo.
5. Optional: generate one genuine Llama interpretation of the initial response before class; identify it as previously generated. No new slow generation during the pitch.
6. Return to Product pitch, chapter 1. Check that the fresh case stays selected.

## Running order

| Time | On screen |
|---|---|
| 0:00–2:30 | Intro to Scout: problem, sources, AI turning point, investigation workflow, prototype scope |
| 2:30–3:15 | Open demo: customers can't pay. Scout asks for a timeline |
| 3:15–4:00 | 1. Complete timeline: release 09:00, database waits 09:12, checkout errors 09:15 UTC |
| 4:00–4:45 | 2. Shared systems: compare failed and successful orders |
| 4:45–5:30 | 3. Follow a failed order: 29s database wait, 30s gateway timeout |
| 5:30–6:10 | 4. Compare the timeout: the gateway is waiting for the API |
| 6:10–7:00 | 5. Database check: read-only evidence supports release-related locking |
| 7:00–8:00 | Verify recovery: simulated rollback, successful test orders, monitoring; case resolved |
| 8:00–9:00 | Full case log, unique ID, saved checks, human review and conclusion |
| 9:00–10:00 | Finish pitch → Beyond the prototype |

The audience is responsible for an online shop, not required to be IT engineers. Every question is about observations, timing, evidence and uncertainty. The fictional results are supplied by the team, while Scout genuinely selects the next guide, records results, retrieves sources and saves the case. Scout does not run checks or execute a rollback.

## What the demo establishes

- A new clue is not a completed check. Each button explicitly records the result of the current guide; the next reply excludes completed guides.
- The final fictional evidence supports release-related database locking and verifies **service recovery within the scenario**. It does not establish the precise code-level root cause.
- The supported human review concerns the recovery evidence. The existing case closure rule requires an investigator-recorded verified-resolution note.
- The normal app also has **Record the result of the next investigation check** for human-entered findings.

## Limits

The 15-question model evaluation is retrospective and provisionally graded. No live system is inspected, no real company incident is resolved, and no production security or commercial ROI is claimed. SevAnalysis is CC BY-NC 4.0. The [code tour](code_tour.md) and three core notebooks contain the coursework explanation.
