"""My five audience-facing story chapters. The full script stays in docs."""

JOURNEY = [
    {
        "label": "The problem",
        "kicker": "01 · WHY SCOUT EXISTS",
        "heading": "Where on earth do I start?",
        "example": "Customers cannot pay. We know the symptom, not the cause. Someone still has to decide what to do next.",
        "decision": "Help an investigator choose the next useful check, rather than guess a diagnosis."
    },
    {
        "label": "The information",
        "kicker": "02 · FIND SOMETHING USEFUL",
        "heading": "What has happened before? What can I check?",
        "example": "I started with real published incidents, then added reliable technical references. They answer different questions.",
        "decision": "Keep each source visible and use it for what it can actually establish."
    },
    {
        "label": "The turning point",
        "kicker": "03 · WHAT CHANGED MY THINKING",
        "heading": "The right evidence. The wrong answer.",
        "example": "Llama sometimes missed the correct incident even when it had been retrieved first, and offered unsupported technical advice.",
        "decision": "Separate the AI's interpretation from the checked procedure. Don't let a plausible answer choose the first action."
    },
    {
        "label": "The build",
        "kicker": "04 · FROM INFORMATION TO ACTION",
        "heading": "An investigation, not a one-off answer.",
        "example": "A person completes a check, records the result and Scout helps choose what to investigate next.",
        "decision": "Make the steps source-linked, keep case history in SQLite, and leave verification with the person."
    },
    {
        "label": "The product",
        "kicker": "05 · WHAT I BUILT TODAY",
        "heading": "A useful next decision, backed by a record.",
        "example": "Scout brings historical knowledge, technical guidance, optional AI and human judgement into one investigation.",
        "decision": "Prove the usefulness of an investigation assistant before connecting to live systems or automating action."
    }
]

TOTAL_CHAPTERS = len(JOURNEY)
