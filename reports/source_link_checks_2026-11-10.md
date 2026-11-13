# Scout — source-link cross-check for the 12 known-incident questions

**Completed 10 November 2026 by assistant-assisted external lookup; NOT a human sign-off.** This adds corroboration for the **expected incident titles and dates** in the frozen provisional question set. It does **not** independently validate the 15 Llama-generated answers, certify all original vendor status pages or change any `reviewed_by_human` flag.

## What was checked

I looked for the expected incident in the public **SevAnalysis vendor listings** (the publisher whose CSV Scout uses), and I attempted to open the **specific official status link** from the question CSV. A link being inaccessible to a web retrieval tool is **not proof the incident is false or that the link is dead in a browser**.

| Question | Target source | Public corroboration checked | Original vendor incident page | Qualification |
| --- | --- | --- | --- | --- |
| Q01 | 1Password · extension code syntax | [SevAnalysis — 1Password](https://sevanalysis.com/vendors/1password/) | [Original link](https://status.1password.com/incidents/vkm6tvh2b568): not directly accessible in this check | Publisher shows incident 2026-01-23; [1Password community](https://www.1password.community/developers-69/1password-chrome-extension-is-incorrectly-manipulating-code-blocks-23713/index2.html) also describes the issue, but is not the incident page |
| Q02 | Azure Communication Services · multiple regions | [SevAnalysis — Azure](https://sevanalysis.com/vendors/azure/) | [Original link](https://azure.status.microsoft/en-us/status/history/?trackingId=YTYN-5T8): not directly accessible | Publisher lists 2022-08-12 incident; the official postmortem still needs direct inspection |
| Q03 | Circle · Aleo Testnet API temporarily unavailable | [SevAnalysis — Circle](https://sevanalysis.com/vendors/circle/) | [Original link](https://status.circle.com/incidents/5c5rbh5d23db): not directly accessible | Publisher lists start 2026-03-09 |
| Q04 | Dagster+ · brief hybrid agent disruption | [SevAnalysis — Dagster+](https://sevanalysis.com/vendors/dagster/) | [Original link](https://dagstercloud.statuspage.io/incidents/6c9vcl9j3164): not directly accessible | 2026-08-29 report exists; the question **may be ambiguous** if multiple hybrid-agent disruptions are available |
| Q05 | Gamma · DNS issues in Brazil | [SevAnalysis — Gamma](https://sevanalysis.com/vendors/gamma/) | [Original link](https://status.gamma.app/incident/cmv1jdeoz0cln1mnqzdh7fybe): not directly accessible | Publisher lists 2026-10-09 report |
| Q06 | HeyGen · Generate Result button | [SevAnalysis — HeyGen](https://sevanalysis.com/vendors/heygen/) | **[Original vendor incident opens](https://status.heygen.com/incidents/01KQD6CXDAV66217MB3JNAWG22)** | The official page shows the button title and 29 April 2026 date. It does not supply a verified cause |
| Q07 | LangSmith · APAC query issue | [SevAnalysis — LangSmith](https://sevanalysis.com/vendors/langsmith/) | [Original link](https://global.status.smith.langchain.com/incidents/01M4QDSKD45HC51TDCYF518XFP): not directly accessible | Publisher uses **APAC**, while question uses **Asia-Pacific** |
| Q08 | OneSignal · delayed analytics | [SevAnalysis — OneSignal](https://sevanalysis.com/vendors/onesignal/) | [Original link](https://status.onesignal.com/incidents/01KVYXAREPQRE2H7062JZAJH86): not directly accessible | Publisher lists 2026-06-25 processing delay |
| Q09 | Retell AI · 7% slow calls | [SevAnalysis — Retell AI](https://sevanalysis.com/vendors/retell/) | [Original link](https://status.retellai.com/incidents/cft9jts6dq1b): not directly accessible | Publisher lists 2025-10-02 report |
| Q10 | Squarespace · 3D Secure subscription purchases | [SevAnalysis — Squarespace](https://sevanalysis.com/vendors/squarespace/) | [Original link](https://status.squarespace.com/incidents/z23wzts5g535): not directly accessible | Publisher and [independent archive](https://rewindex.com/company/squarespace/incidents/z23wzts5g535) show 2025-12-08 17:02 UTC; the CSV contains seconds precision |
| Q11 | Vanta · in-app support button | [SevAnalysis — Vanta](https://sevanalysis.com/vendors/vanta/) | [Original link](https://status.vanta.com/incidents/w6q27jw497w1): not directly accessible | Publisher uses the label **Chat with us** |
| Q12 | v0 · code editor changes not saving | [SevAnalysis — v0](https://sevanalysis.com/vendors/v0/) | **[Original vendor incident opens](https://v0-status.com/incidents/01KN3JFEWY4GMXJWWRH6P6C2FG)** | Official page confirms the incident title and 1 April 2026 start (minute precision visible) |

**Outcome:** The target titles were located or corroborated through the dataset publisher's public listings for all 12 known incidents. **Only two original vendor incident pages (Q06 and Q12) were directly opened and checked in this attempt.** That is *not* 12 independently verified primary sources, and no question has been marked `reviewed_by_human=True`.

## What this changes in the evaluation interpretation

The source checks strengthen confidence that the expected incidents are real **entries in the published collection**. They do not resolve whether every question uniquely identifies one report; Q04 still needs an ambiguity check. They also do not determine whether the generated answer is correct just because a source was retrieved.

The saved 15-question score remains **provisional AI-assisted review**: factual core answers 4/12, expected source cited 3/12, clear refusals 2/3. The original raw answers were examined separately; only a human review of all 15 answers and the applicable original source text can authorise final human-approved scoring.

## Next review decisions (Q&A)

**Q. Why are there two kinds of source verification?**

**A.** The CSV comes from SevAnalysis, which aggregates incidents that vendors publish. Checking its live listings confirms my expected record exists within that compilation. Opening the original vendor status report is a stronger, independent check of what the vendor actually published. They are not interchangeable.

**Q. Why wasn't an inaccessible official link counted as a failed source?**

**A.** A retrieval tool may be blocked, require scripts or lack a cached copy. I only record what I could actually inspect; I cannot infer that the incident was removed.

**Q. Why are the LLM results still provisional?**

**A.** Source existence and generated-answer correctness are separate questions. The full raw answers, the expected record, citation relevance and the ambiguous cases must be reviewed together before I approve final scores.

**Q. How does Q04 affect the score?**

**A.** Its answer cites the target incident, but the question may also fit a different hybrid-agent report and the response adds irrelevant discussion. I keep the originally recorded provisional pass and flag it for strict human adjudication rather than silently changing the result after seeing the outputs.
