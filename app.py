import json
import streamlit as st
from backend.filter import load_cars, filter_cars
from backend.recommender import extract_params_from_message, get_recommendations, get_followup_response

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CarDekho AI Advisor",
    page_icon="🚗",
    layout="centered",
)

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


def render_shortlist(shortlist: dict):
    cars = shortlist.get("shortlist", [])
    summary = shortlist.get("summary", "")

    if summary:
        st.markdown(f"*{summary}*")
        st.markdown("---")

    medals = ["🥇", "🥈", "🥉"]
    for i, car in enumerate(cars):
        medal = medals[i] if i < 3 else f"#{car['rank']}"
        price = car.get("price_lakhs", "N/A")
        specs = car.get("key_specs", {})

        with st.container():
            st.markdown(f"### {medal} {car['make']} {car['model']} {car['variant']}")
            st.markdown(f"**₹{price} Lakhs**")
            st.markdown(f"> {car['why']}")

            # Specs strip
            col1, col2, col3, col4, col5 = st.columns(5)
            fuel = specs.get("fuel", "—")
            trans = specs.get("transmission", "—")
            seating = specs.get("seating", "—")
            safety = specs.get("safety_stars", "—")
            range_km = specs.get("range_km")
            mileage = specs.get("mileage")

            if range_km:
                efficiency_label = f"🔋 {range_km}km"
            elif mileage:
                efficiency_label = f"⛽ {mileage}"
            else:
                efficiency_label = "—"

            col1.metric("Fuel", fuel)
            col2.metric("Gearbox", trans if isinstance(trans, str) else "/".join(trans) if trans else "—")
            col3.metric("Seats", seating)
            col4.metric("Safety", f"{'★' * int(safety) if safety and safety != '—' else '—'}")
            col5.metric("Efficiency", efficiency_label)

            st.markdown("---")


def process_user_message(user_input: str):
    params = st.session_state.user_params
    stage = st.session_state.stage

    # Extract params from message — pass pending params so AI knows what was being asked
    pending = missing_params(params)
    with st.spinner("Understanding your requirements..."):
        updated_params = extract_params_from_message(user_input, params, pending_params=pending)
    st.session_state.user_params = updated_params

    # If we already have a shortlist, handle as follow-up
    if stage == "followup" and st.session_state.shortlist:
        with st.spinner("Thinking..."):
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
st.title("🚗 CarDekho AI Advisor")
st.caption("Tell me what you need — I'll find your perfect car from 80+ options.")

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
