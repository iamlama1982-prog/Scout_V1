# Scout — my speaking notes

These are separate from the app. Use them as prompts, not a script to race through.

## Act 1 — Intro to Scout (about 2½ minutes)

### 1. The problem

I started with a fairly simple operational problem. Imagine you run an online business and suddenly customers can't complete their orders. You know something is wrong, it's affecting the business and someone needs to make a decision about what happens next.

The information you have at that point is usually incomplete. There could be several things happening at once, different systems involved, and a huge amount of information to work through. The question isn't necessarily "What's the answer?" It's often "Where on earth do I start?"

That's the problem I wanted Scout to solve.

### 2. The information

My original idea was to use knowledge from previous incidents to help investigate a new one. I found a public dataset, SevAnalysis, containing over 41,000 published technology incidents. I built a search function to find relevant reports. If something similar happened elsewhere, it might give us a useful lead.

That raised a question: does a similar problem mean the same cause? Does knowing what happened elsewhere tell me what to do next? Not necessarily.

So I added technical documentation from sources such as Microsoft, PostgreSQL, Kubernetes and MDN. I used that to build checked investigation guides explaining what to check, how to check it and what different results might mean.

### 3. The turning point

Then I introduced Llama to interpret the evidence. One of the most interesting discoveries was that even with the right report in front of it, the model could give me the wrong answer or suggest something unsupported.

That changed the design. I didn't want another AI tool that gives you a convincing answer and leaves you to work out whether it's right. I separated checked guidance from optional AI interpretation. The user gets a useful next step without relying on the model's judgement.

### 4. The build

In a real incident you don't ask one question, get an answer and go home. You investigate, find something out, change your thinking and investigate again.

I introduced SQLite so each investigation has its own identity and keeps the conversation, evidence, completed checks and decisions. Scout moves through it with you. A person remains responsible for checking the findings and deciding when the incident is resolved.

### 5. The product today

Scout is a working local prototype. It brings historical knowledge, technical guidance, optional AI interpretation and a saved investigation into one place.

It isn't connected to live company systems and doesn't automatically fix problems. Those are deliberate boundaries. I wanted to demonstrate whether I could help someone move from an initial problem to a more informed decision and a conclusion they can explain.

**Transition:** "Rather than tell you any more about how it works, I'd like you to help me investigate something. You're responsible for an online shop. It's a normal working day. Customers are trying to place orders. And checkout has stopped working."

## Act 2 — Follow the investigation to a conclusion (6½ minutes)

### Start: the customer problem (2:30–3:15)

"Imagine you run an online shop. Some customers can't pay. A 504 means a system has waited too long for a response. We know what the customer experiences, not the cause. What's the first thing you'd want to know?"

Open the prepared demo case. Show Scout's first recommendation: build a timeline. Open **View steps** briefly. "We aren't going to just move on to the next clue. We're going to do the check and report what we found."

### 1. Complete the timeline (3:15–4:00)

Ask: "A new version went live at 9. Customers first saw failures at 9:15. Is that relevant? Does it prove the cause?"

Click **Complete the timeline check**. The fictional logs provide actual times in UTC: release 09:00, database waits 09:12, checkout failures 09:15, both continuing through 09:30.

"That gives us a sequence. Scout has saved the result and moved on. We don't need to ask for the same timeline again."

### 2. Check what the failed orders share (4:00–4:45)

"Are we looking at completely separate problems, or do the orders go through the same systems?"

Click **Check what the failed orders share**. Failed and successful orders share the gateway, checkout API and PostgreSQL database. Failed writes wait; successful ones don't. "A database is where the shop stores information. We have confirmed what the shop actually uses, not guessed it from a historical incident."

### 3. Follow one failed order (4:45–5:30)

"If a customer order is like a parcel moving through a series of stages, where does it get stuck?"

Click **Follow one failed order**. The failed request spends 29 seconds waiting for the database write and times out at 30; a successful one takes 0.4 seconds. Point to the real next checked guide.

### 4. Compare the timeout (5:30–6:10)

Click **Compare the timeout with a successful order**. The gateway times out while waiting for the checkout API. "We have found where the delay occurs. Increasing the time limit would hide the symptom, not explain the delay."

### 5. Check why the database waits (6:10–7:00)

Click **Check why the database is waiting**. The fictional read-only check shows checkout writes waiting on locks held by a long-running transaction from the new release.

"Think of a lock as someone temporarily holding a resource so another person has to wait. Now we have actual evidence supporting a release-related locking problem. That's our leading explanation, not a proven code-level cause."

### Verify recovery (7:00–8:00)

Ask: "What would convince you that customers can actually pay again?"

Click **Verify recovery and close the fictional case**. The fictional authorised team rolled back the release at 09:35; the blocking transaction ended at 09:36, waits returned to normal, errors stopped, 20 test orders succeeded and 30 minutes of monitoring showed no recurrence.

"Scout hasn't rolled anything back. The fictional team did that and supplied the results. We've verified recovery in this scenario and recorded a supported human review. The cause is still a leading explanation, and the precise code defect needs further review. That's a meaningful conclusion, not just 'we don't know'."

### Show the case log (8:00–9:00)

Open **Full case log**. Show the same unique ID, the original problem, completed check results, next recommendations, human review and verified-resolution note. Explain SQLite preserves the investigation and the current case status. Optional: briefly open historical evidence; do not wait for live Llama generation.

Click **Finish pitch · Beyond the prototype**.

## Act 3 — Beyond the prototype (1 minute)

"What we've just seen is a working local investigation aid. We haven't proved it saves a company money or that it's ready for confidential corporate data.

The first step is to test with real incident teams on genuinely unseen, independently reviewed cases. Do people find the right information and make better next-step decisions?

Then I'd need secure shared case management, integration with monitoring and ticketing, and licensing the data for commercial use. The current incident dataset has a non-commercial licence.

Finally, I'd run a pilot and measure whether this actually reduces wasted effort or improves investigation quality. That's the commercial question.

**The next step isn't more AI. It's proving that better evidence and a clear decision trail make investigations more effective.**"

## Reminders

- The shop and human review are fictional; retrieval, guidance and local saving are real.
- 4/12 refers to the old raw Llama test, not the final checked app. Grades are provisional and the question set retrospective.
- 0.007s is search-only after indexing, not end-to-end response time.
- If audience discussion runs long, shorten the source browsing. Keep the recovery verification and full log.
