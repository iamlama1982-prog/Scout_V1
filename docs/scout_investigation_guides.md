# Scout — expandable investigation steps

> **Development notes:** I kept this record of how the feature evolved. Some descriptions refer to earlier versions. The [final README](../README.md), [code tour](code_tour.md) and [presentation runbook](project3_presentation_runbook.md) describe the submitted Scout app.

## Why I built this

Scout could remember an investigation and suggest what to look at, but its technical instructions weren't always dependable. In one test it gave a PostgreSQL object a plausible-sounding name that didn't match the official documentation. I don't want an assistant that sounds confident while giving an engineer the wrong command.

I decided to separate **Scout's explanation** from **the instructions someone might actually follow**.

The language model can still discuss possible causes and explain what evidence would help. The detailed **View steps** panels, however, come from a small, reviewed set of instructions. Scout does not write a fresh command every time somebody asks.

## How the feature works

1. I wrote six concise investigation guides in `knowledge/investigation_playbooks.json`. There are general methods for comparing incident timelines, mapping dependencies and following a failed request. There are also technology-specific guides for HTTP 504 timeouts, PostgreSQL session activity and Kubernetes Pod restarts.
2. Each guide says **when it applies**, then gives a short sequence of checks and explains what would support, weaken or leave a hypothesis unresolved.
3. The app chooses guides using information **the user actually supplied** in this case. It doesn't take a database name from one of Scout's own guesses or from an unrelated vendor incident.
4. When Scout responds, the chosen guides appear under its answer as **clickable, expandable investigation steps**. A user can open one and see the full procedure, any reviewed read-only command, a source link and what to tell Scout afterwards.
5. The selected instructions are saved alongside Scout's response in the local case database. Reopening the case gives the same instructions, even if the reference catalogue later changes.

These guides are not instructions Scout has already carried out. The application does **not** connect to a live system or run any of the commands.

## What the next user test showed

The first version displayed the four useful guides in the right order, but the
LLM's own written answer still started with generic database-capacity checks.
It also repeated the question and gave a second checklist that did not match
the clickable plan.

**My decision:** the reviewed, ordered playbooks should own the action list.
When there are playbooks, Scout's generated response now has a smaller job:
give a direct, short interpretation, explain why the **first** checked guide
comes first and ask for one useful observation afterwards. The model should
not repeat the user's question or invent its own detailed instructions.

This is an important design choice. Changing the tone of the prompt might
make Scout sound nicer, but it doesn't make an improvised procedure reliable.
I am using a clear separation between generated interpretation and checked
action steps, and I still need to test the revised answer with the local model.

## A further change after testing the real conversation

I ran the checkout/PostgreSQL example again after strengthening the prompt. Scout
still wrote a database-first checklist, even though its checked guides correctly
started with comparing the failure and deployment timelines. This showed me that
**prompt instructions alone aren't a reliable way to enforce an action order**.

I changed the design rather than adding more instructions:

- **The visible first priority** is now built directly from the first reviewed
  playbook selected for this case. The summary explains what to check and asks
  for one useful observation before we move on.
- **The expandable steps** contain the actual investigation procedures in the
  reviewed order, including conditions and what different results would mean.
- **The original LLM output** is saved in the case evidence under **Original AI
  draft**. It is clearly marked unverified and may conflict with the checked
  plan; it is retained for transparency and course evaluation, not for
  operational instructions.
- When no guide applies, Scout's ordinary generated answer is still shown. The
  model is still called and the public RAG sources are retrieved, but the
  reviewed playbooks control any actionable checklist.

For this example, comparing the timeline is now first. That is not a claim
that the deployment caused the incident. It is the starting check needed to
test whether the change and failures are actually related.

The trade-off is deliberate: the first-priority explanation is less free-form,
but it cannot silently move an unverified database-capacity check ahead of
the source-checked investigation steps. The model's original response remains
available to assess whether it is learning to follow the same sequence.

## Why there are two kinds of guide

| Type | Example | How I label it |
| --- | --- | --- |
| General investigation method | Compare when the database slowed down and when checkout failures began | An original general method, **not** supplier-verified |
| Source-linked technical procedure | Inspect active PostgreSQL sessions and waits | Linked to the actual PostgreSQL documentation, with an explicit condition that the organisation uses PostgreSQL |

This distinction matters. A good investigation method can be sensible without appearing word for word in a vendor manual. I don't want to pretend every general method has an official certification.

The technical examples are linked to the existing approved source library:
- [PostgreSQL monitoring statistics](https://www.postgresql.org/docs/current/monitoring-stats.html) — `pg_stat_activity` and the documented activity/wait columns
- [MDN HTTP 504](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/504) — what a gateway timeout actually means
- [Kubernetes debugging running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) — Pod events and previous container logs

**Review date:** 9 November 2026. These are checked references, not a live documentation feed. The real commands and operating conditions may differ by environment and version, so an engineer still needs to verify applicability before running them.

## The specific PostgreSQL correction

I replaced the vague or invented commands from the model's earlier answer with a **read-only SELECT from `pg_stat_activity`**, based on the official PostgreSQL reference.

It examines database session state and waiting events. It does **not** measure available RAM or disk space; those need separate monitoring. Results are only a snapshot, so a normal result now doesn't disprove a short-lived problem earlier.

## The limits I am keeping

- **No automatic execution.** A click opens instructions; it doesn't touch the infrastructure.
- **No automatic diagnosis.** Similar symptoms and a useful check do not prove a cause.
- **No permission assumptions.** Commands are intended for someone with appropriate access, after confirming the technology.
- **No invented procedures in the checked panels.** The panels use reviewed JSON records, not newly generated LLM instructions.
- **No claim of perfect generation.** A small language model can still make unsupported statements in the surrounding text; those still need human evaluation.
- **No automatic case-learning yet.** Saved cases remain separate; the guide catalogue is curated manually.

## Example investigation and verification

1. Start a case about checkout, database delays and API timeouts. Scout should offer **timeline, dependency and request-tracing guides** without assuming a database vendor.
2. Open **View steps** under one action. Check that it says why to do the check and what the result means.
3. Add the follow-up: **"We're using PostgreSQL, and we deployed an update on Monday."**
4. Scout should now also make the PostgreSQL-specific guide available, with an official source link. It should **not** have shown that guide before the user mentioned PostgreSQL.
5. Refresh the browser and reopen the case. The same step-by-step guides should still be visible under the saved replies.
6. Turn off **Include technical guidance** to compare how the assistant behaves without the guided procedures.

The documented tests cover source IDs, read-only command restrictions, conditions, saved playbooks and the Streamlit first-message/follow-up flow. Run them with:

```powershell
python -m pytest -q tests/test_scout_playbooks.py tests/test_scout_ui_smoke.py tests/test_scout_case_memory.py
```

**What this example demonstrates:** source-linked guidance changes when new information is supplied and remains visible in the saved case. It does not establish an independently confirmed root cause or guarantee that every suggestion is correct.
