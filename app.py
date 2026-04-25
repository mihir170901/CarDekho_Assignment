import json
import streamlit as st
from backend.filter import load_cars, filter_cars
from backend.recommender import check_scope, extract_params_from_message, get_recommendations, get_followup_response

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CarDekho AI Advisor",
    page_icon="🚗",
    layout="centered",
)

# ── Theme & custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
/* CarDekho orange + white theme */
:root {
    --cd-orange: #FF6B00;
    --cd-orange-light: #FFF3E8;
    --cd-dark: #1A1A1A;
    --cd-grey: #6B7280;
    --cd-border: #E5E7EB;
}

/* Header */
h1 { color: var(--cd-dark) !important; }

/* Car card */
.car-card {
    border: 1.5px solid var(--cd-border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.car-card:hover {
    border-color: var(--cd-orange);
    box-shadow: 0 2px 12px rgba(255,107,0,0.10);
    transition: all 0.2s ease;
}

/* Rank badge */
.rank-badge {
    display: inline-block;
    background: var(--cd-orange);
    color: white;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 8px;
    text-transform: uppercase;
}

/* Car title */
.car-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--cd-dark);
    margin: 4px 0 2px 0;
}
.car-price {
    font-size: 15px;
    font-weight: 600;
    color: var(--cd-orange);
    margin-bottom: 10px;
}

/* Why text */
.car-why {
    font-size: 14px;
    color: #374151;
    line-height: 1.6;
    background: var(--cd-orange-light);
    border-left: 3px solid var(--cd-orange);
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 16px;
}

/* Spec pills */
.specs-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
}
.spec-pill {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    background: #F9FAFB;
    border: 1px solid var(--cd-border);
    border-radius: 8px;
    padding: 8px 14px;
    min-width: 90px;
}
.spec-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--cd-grey);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 3px;
}
.spec-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--cd-dark);
}

/* Summary text */
.summary-text {
    font-size: 13px;
    color: var(--cd-grey);
    font-style: italic;
    margin-bottom: 16px;
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid var(--cd-border);
    margin: 8px 0 20px 0;
}

/* Follow-up response typography inside chat messages */
[data-testid="stChatMessage"] p {
    font-size: 14px;
    line-height: 1.7;
    color: #374151;
}
[data-testid="stChatMessage"] strong {
    color: #1A1A1A;
    font-weight: 600;
}
[data-testid="stChatMessage"] h3 {
    font-size: 15px;
    font-weight: 700;
    color: #1A1A1A;
    margin: 14px 0 6px 0;
    padding-left: 10px;
    border-left: 3px solid #FF6B00;
}
[data-testid="stChatMessage"] ul {
    margin: 4px 0 10px 0;
    padding-left: 18px;
}
[data-testid="stChatMessage"] ul li {
    font-size: 14px;
    color: #374151;
    margin-bottom: 4px;
    line-height: 1.6;
}
[data-testid="stChatMessage"] ul li::marker {
    color: #FF6B00;
}
[data-testid="stChatMessage"] table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin: 10px 0;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    overflow: hidden;
}
[data-testid="stChatMessage"] th {
    background: #1A1A1A;
    color: #ffffff;
    padding: 8px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
[data-testid="stChatMessage"] td {
    padding: 7px 14px;
    border-bottom: 1px solid #E5E7EB;
    color: #374151;
}
[data-testid="stChatMessage"] td:first-child {
    font-weight: 600;
    color: #1A1A1A;
    background: #FFF3E8;
    border-left: 3px solid #FF6B00;
}
[data-testid="stChatMessage"] tr:last-child td {
    border-bottom: none;
}
[data-testid="stChatMessage"] tr:nth-child(even) td {
    background: #F9FAFB;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_params" not in st.session_state:
    st.session_state.user_params = {}
if "shortlist" not in st.session_state:
    st.session_state.shortlist = None
if "stage" not in st.session_state:
    st.session_state.stage = "intake"  # intake | shortlist | followup
if "cars" not in st.session_state:
    st.session_state.cars = load_cars()

REQUIRED_PARAMS = ["budget", "use_case", "seats", "fuel", "transmission", "priority"]
MISSING_QUESTIONS = {
    "budget": "💰 What's your budget? (e.g. '10 lakhs', '8-12 lakhs')",
    "use_case": "🛣️ How will you mainly use the car? (City / Highway / Mixed)",
    "seats": "👨‍👩‍👧‍👦 How many seats do you need? (5 for most families, 7 for larger ones)",
    "fuel": "⛽ Any fuel preference? (Petrol / Diesel / CNG / Electric / No preference)",
    "transmission": "🕹️ Manual or Automatic? (or no preference)",
    "priority": "⭐ What's your top priority? (Mileage / Safety / Low Maintenance / Resale Value / Boot Space)",
}


def missing_params(params: dict) -> list:
    return [k for k in REQUIRED_PARAMS if not params.get(k)]


def ask_missing(missing: list) -> str:
    questions = [MISSING_QUESTIONS[k] for k in missing]
    if len(questions) == 1:
        return questions[0]
    return "I need a few more details:\n\n" + "\n".join(f"- {q}" for q in questions)


def _spec_pill(label: str, value: str) -> str:
    return f"""
    <div class="spec-pill">
        <span class="spec-label">{label}</span>
        <span class="spec-value">{value}</span>
    </div>"""


def _safety_text(stars) -> str:
    try:
        n = int(stars)
        return f"{n}/5 stars"
    except (TypeError, ValueError):
        return "N/A"


def render_shortlist(shortlist: dict):
    cars = shortlist.get("shortlist", [])
    summary = shortlist.get("summary", "")

    if summary:
        st.markdown(f'<p class="summary-text">{summary}</p>', unsafe_allow_html=True)

    rank_labels = ["#1 Best Match", "#2 Runner Up", "#3 Also Consider"]

    for i, car in enumerate(cars):
        rank_label = rank_labels[i] if i < 3 else f"#{car['rank']}"
        price = car.get("price_lakhs", "N/A")
        why = car.get("why", "")
        specs = car.get("key_specs", {})

        fuel = specs.get("fuel") or "—"
        trans = specs.get("transmission") or "—"
        if isinstance(trans, list):
            trans = " / ".join(trans)
        seating = specs.get("seating") or "—"
        safety = _safety_text(specs.get("safety_stars"))
        range_km = specs.get("range_km")
        mileage = specs.get("mileage")

        if range_km:
            efficiency_label = f"{range_km} km"
            efficiency_heading = "Range"
        elif mileage:
            efficiency_label = str(mileage)
            efficiency_heading = "Mileage"
        else:
            efficiency_label = "—"
            efficiency_heading = "Efficiency"

        pills = (
            _spec_pill("Fuel", fuel)
            + _spec_pill("Gearbox", trans)
            + _spec_pill("Seats", str(seating))
            + _spec_pill("Safety", safety)
            + _spec_pill(efficiency_heading, efficiency_label)
        )

        card_html = f"""
        <div class="car-card">
            <div class="rank-badge">{rank_label}</div>
            <div class="car-title">{car['make']} {car['model']} {car['variant']}</div>
            <div class="car-price">₹{price} Lakhs</div>
            <div class="car-why">{why}</div>
            <div class="specs-row">{pills}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)


def process_user_message(user_input: str):
    params = st.session_state.user_params
    stage = st.session_state.stage
    params_before = dict(params)  # snapshot before any extraction

    # Scope check + param extraction under one spinner
    with st.spinner("Thinking..."):
        decline = check_scope(user_input)
        if decline:
            st.session_state.messages.append({"role": "assistant", "content": decline})
            return

        # Extract params — pass pending params so AI knows what was being asked
        pending = missing_params(params)
        updated_params = extract_params_from_message(user_input, params, pending_params=pending)
    st.session_state.user_params = updated_params

    # If we already have a shortlist, check if user is updating params or asking a question
    if stage == "followup" and st.session_state.shortlist:
        param_changed = any(updated_params.get(k) != params_before.get(k) for k in REQUIRED_PARAMS)

        if param_changed:
            # User is refining (e.g. "show diesel instead") — re-run full catalog search
            # Fall through to filter + recommend below
            pass
        else:
            # Pure follow-up question — return plain chat response
            with st.spinner("Looking that up..."):
                reply = get_followup_response(
                    st.session_state.shortlist.get("shortlist", []),
                    user_input,
                    st.session_state.messages,
                )
            st.session_state.messages.append({"role": "assistant", "content": reply})
            return

    # Check what's still missing
    missing = missing_params(updated_params)

    if missing:
        reply = ask_missing(missing)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        return

    # All params collected — run filter + AI recommendation
    if stage == "followup":
        st.session_state.messages.append({"role": "assistant", "content": "Got it! Let me update your shortlist with the new preferences."})

    with st.spinner("Finding your best matches..."):
        candidates = filter_cars(st.session_state.cars, updated_params)

        if not candidates:
            reply = "I couldn't find any cars matching all your criteria. Try relaxing your budget or fuel preference."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            return

        result = get_recommendations(candidates, updated_params, user_input)

    st.session_state.shortlist = result
    st.session_state.stage = "followup"
    st.session_state.messages.append({"role": "assistant", "content": "__SHORTLIST__"})


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
    <span style="font-size:32px;">🚗</span>
    <div>
        <h1 style="margin:0; font-size:26px; color:#1A1A1A;">CarDekho <span style="color:#FF6B00;">AI Advisor</span></h1>
        <p style="margin:0; font-size:13px; color:#6B7280;">Tell me what you need — I'll find your perfect car from 80+ options.</p>
    </div>
</div>
<hr style="border:none; border-top:2px solid #FF6B00; margin:12px 0 20px 0;">
""", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "assistant" and content == "__SHORTLIST__":
        with st.chat_message("assistant"):
            st.markdown("Here are your **Top 3 picks** based on your requirements:")
            if st.session_state.shortlist:
                render_shortlist(st.session_state.shortlist)
            st.markdown("💬 **Ask me anything** — compare cars, ask about a specific model, or refine your search.")
    else:
        with st.chat_message(role):
            st.markdown(content)

# ── Welcome message on first load ─────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 Hi! I'm your AI car buying advisor.\n\n"
            "Tell me what you're looking for — you can describe everything in one go, or I'll guide you step by step.\n\n"
            "**Example:** *'Budget 12 lakhs, need 5 seats, automatic, mostly city driving, open to petrol or diesel, safety is my top priority'*"
        )

# ── Input ─────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Tell me what you're looking for..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    process_user_message(prompt)
    st.rerun()
