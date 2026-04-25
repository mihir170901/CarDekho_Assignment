# CarDekho AI Advisor

An AI-powered conversational car buying assistant that helps users go from "I don't know what to buy" to a confident shortlist of top 3 cars.

**Live URL:** https://cardekhoai.streamlit.app/

---

## Quick Start

**Requirements:** Python 3.11, an OpenAI API key

```bash
# 1. Clone the repo
git clone https://github.com/mihir170901/CarDekho_Assignment.git
cd CarDekho_Assignment

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenAI key
# Create a .env file in the root with:
# OPENAI_API_KEY=your_key_here

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## What did you build and why? What did you deliberately cut?

The core idea is a conversational car finder. Users type in their requirements — budget, use case, seating, fuel preference, transmission, and top priority — and the app returns a ranked shortlist of the top 3 cars with a personalised explanation for each. They can then ask follow-up questions, compare cars side by side, or refine their preferences — all within a controlled, guardrailed chat environment.

What makes this different from just asking ChatGPT is that the recommendations are grounded in CarDekho's own dataset. CarDekho's data is domain-specific, up to date, and in the future can be connected to their ERP and internal systems for even richer context. The hallucination risk that comes with a general-purpose model goes down significantly when the AI is working off structured, curated data rather than training memory.

The UI decision was a deliberate call. I initially considered a dropdown/radio-button form for collecting the 6 parameters — it would be cleaner for input — but the chat interface wins because it gives the user the ability to ask ad-hoc questions, compare options, and refine on the fly. A form can't do that.

**What was cut:**
- Car images — adds visual polish but not core to the decision
- Real-time pricing API — static dataset is sufficient for an MVP
- User accounts and saved sessions — not needed to validate the core flow
- EMI calculator, dealer locator — useful features but out of scope for this build
- Database — a JSON file of 80 cars fits in memory and needs no infra

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend + App | Streamlit |
| Backend logic | Pure Python |
| AI | OpenAI GPT-4o-mini |
| Dataset | Static JSON (80 cars) |
| Deployment | Streamlit Community Cloud |

**Why this stack:** Python was the natural choice given my familiarity with it. Streamlit is genuinely useful for building quick prototype products — it saved a lot of time compared to setting up a separate frontend framework. GPT-4o-mini is cost-effective, reliable with structured JSON output, and fast enough for a chat interface.

---

## What did you delegate to AI vs. do manually?

Honestly, the entire coding was delegated to Claude Code. But I kept a close watch on everything that was being built and stayed in control throughout. Whenever it started going in the wrong direction I course-corrected immediately.

My role was closer to a senior engineer or product manager — clearly defining requirements, deciding the architecture upfront, reviewing every piece of code, and catching bugs before they compounded. I understand Python well and was always on top of what the code was actually doing, not just accepting output blindly.

**Where it helped most:** Translating requirements to working code quickly. Building this much functionality in a 2-3 hour window would have been difficult without it. It was especially useful for boilerplate — file structure, Streamlit session state wiring, OpenAI API calls.

**Where it got in the way:** The UI styling needed multiple iterations. The initial CSS pass made all bold text orange which looked bad. This was partly my fault — I wasn't specific enough in the prompt about where orange should and shouldn't appear. Once I gave clearer direction it corrected quickly. Since the codebase was small, the tool didn't go off the rails in any significant way.

---

## If you had another 4 hours, what would you add?

**Live CarDekho product links** on each car card — a direct "View on CarDekho" button that takes the user to the actual listing. This closes the loop between recommendation and action.

**A more intelligent conversational flow.** Right now the bot collects 6 params and recommends. There's a lot more that can be added — remembering what the user rejected, detecting implicit signals ("I drive 80km a day" → infer mileage priority), smarter follow-up questions that narrow the shortlist rather than just collecting missing fields, and multi-turn memory so the user doesn't have to repeat themselves.

**Tool access for the agent.** Currently the agent has no tools — it works purely off the static JSON. Giving it access to CarDekho-specific data stores, internal APIs, or live inventory would make the responses significantly richer and more accurate.

**Auth and session persistence** — basic stuff but useful. Right now every page refresh resets the conversation. Saving sessions and user preferences would make this a proper product rather than a prototype.
