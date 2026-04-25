# Bugs & Fixes Log

## Bug 4 — No guardrails on out-of-scope questions

**Symptom 1:** Asking "who is the CEO of Ferrari" returned a factual answer — completely outside the app's purpose.
**Symptom 2:** Asking about Ferrari (not in catalog) gave a normal response with no indication it's unavailable on CarDekho.

**Root cause:** `get_followup_response` prompt had no scope constraints — it behaved as a general-purpose assistant.

**Fix:** Added explicit scope rules to the `get_followup_response` prompt:
- **Off-topic questions** (non-automotive) → fixed decline message, no answer given
- **Cars not in CarDekho catalog** (Ferrari, Lamborghini, etc.) → brief general info allowed, but always appended with "This car isn't currently available in CarDekho's catalog"
- Also tightened temperature from 0.5 → 0.3 to reduce creative deviation from the rules

Also added a one-line scope reminder to the `SYSTEM_PROMPT` used during initial recommendations.

**Files changed:** `backend/recommender.py`, `fixes_made.md`

**Follow-up fix 1:** The guardrail only applied post-shortlist. During the intake stage, off-topic messages were silently ignored and the app just asked for car params. Added a `check_scope()` function that runs before param extraction on every message at every stage. If off-topic, returns the decline message immediately without proceeding to extraction or param-asking.

**Follow-up fix 2:** Off-topic messages showed no loading spinner because `check_scope()` was called before any `st.spinner` context. Fixed by merging the scope check and param extraction under a single `st.spinner("Thinking...")` block so there is always visual feedback regardless of what the user typed.

**Files changed:** `backend/recommender.py`, `app.py`

---


## Bug 1 — "No preference" not recognized during guided Q&A

**Symptom:** User replied "5 seats is fine, no preference, Safety" to a 3-question follow-up. The app re-asked the transmission question instead of mapping "no preference" to `Any`.

**Root cause:** `extract_params_from_message` had no context about what the assistant had just asked. OpenAI couldn't map "no preference" to the correct param (transmission) because it didn't know what was being asked.

**Fix:** Added a `pending_params` argument to `extract_params_from_message`. The prompt now tells OpenAI which params were pending, so "no preference" is correctly interpreted in context. Also added explicit instruction to map "no preference / doesn't matter / any" → `"Any"` for whichever param was being asked.

**Files changed:** `backend/recommender.py`, `app.py`

---

## Bug 2 — Welcome example message missing 2 of 6 params

**Symptom:** The example prompt shown on the welcome screen only demonstrated 4 of the 6 required params (missing seats and fuel preference), potentially confusing users about what to include.

**Fix:** Updated example to: *'Budget 12 lakhs, need 5 seats, automatic, mostly city driving, open to petrol or diesel, safety is my top priority'*

**Files changed:** `app.py`

---

## Bug 3 — Param refinement ("show diesel instead") triggered plain-text response instead of card UI

**Symptom:** After receiving the initial top-3 shortlist, saying "instead of petrol give me diesel" returned a plain-text response like "Unfortunately, none of the cars on your shortlist offer a diesel option" — only looking at the 3 shortlisted cars, not the full catalog.

**Root cause (double):**
1. `params_before` was captured *after* `extract_params_from_message` had already merged the new fuel value in. So `params_before` and `updated_params` were identical, `param_changed` was always `False`, and the code always fell into the plain-text follow-up path.
2. `get_followup_response` only has access to the 3 shortlisted cars, not the full 80-car catalog — so even if it had reached the right path, it would search the wrong dataset.

**Fix:** Moved `params_before = dict(params)` to before the extraction call so the snapshot is taken before any merging. When a param change is detected, the code now falls through to the full filter+recommend pipeline (searching all 80 cars), and renders the card UI with a "Got it! Let me update your shortlist" prefix message. Removed the redundant second `extract_params_from_message` call.

**Design decision:** When a user changes a param (fuel, budget, etc.), always re-search the full catalog — never just the current shortlist. The shortlist-only path only makes sense for factual questions ("does the Nexon come in diesel?"), not param changes.

**Files changed:** `app.py`
