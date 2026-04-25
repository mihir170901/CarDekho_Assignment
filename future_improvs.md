# Future Improvements

## 1. Live CarDekho Product Links on Car Cards
Each car card in the top 3 shortlist could include a "View on CarDekho" CTA button linking to the actual product listing page.

**What this needs:**
- Map each car in the dataset to its canonical CarDekho URL (e.g. `https://www.cardekho.com/maruti-suzuki/swift`)
- Add a `cardekho_url` field to each entry in `cars.json`
- Render a styled orange button at the bottom of each card that opens the link in a new tab

**Value:** Closes the loop between recommendation and action — user goes from shortlist directly to the real listing without leaving the flow.

---

## 2. More Intelligent and Context-Aware Conversational Flow
The current flow collects 6 params and recommends. There is room to make the conversation feel smarter and more natural.

**Specific improvements:**
- **Memory across turns:** Track what the user has reacted to (e.g. "too expensive", "I like this one") and factor that into re-ranking without asking again
- **Implicit signal detection:** If a user says "I drive 80km a day", infer mileage priority automatically rather than asking
- **Smarter follow-up questions:** Instead of asking all missing params at once, prioritise the one that most narrows the shortlist given what's already known
- **Clarification on ambiguity:** If "mixed" use case + "safety" priority returns very different cars, ask a tiebreaker ("mostly families or solo driving?") rather than picking arbitrarily
- **Multi-turn refinement memory:** When user says "too expensive" on a shortlist, remember the rejected cars and never surface them again in that session
- **Richer prompt context:** Pass more of the conversation history to the recommendation call so the AI can reference earlier constraints the user mentioned casually
