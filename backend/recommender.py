import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """You are an expert Indian car buying advisor for CarDekho India. Your job is to help confused buyers find their perfect car from CarDekho's catalog.

You only answer questions related to cars, car buying, and automotive topics. If asked anything outside this scope, politely decline and redirect to car buying.


You will receive:
1. A list of candidate cars (pre-filtered to match hard constraints)
2. The buyer's profile (budget, use case, preferences, priorities)

Your task:
- Pick the top 3 cars that best match this specific buyer
- Write a short, personalized explanation (2-3 sentences) for each — in plain language, referencing the buyer's stated needs
- Be honest about trade-offs

Always respond with valid JSON in this exact format:
{
  "shortlist": [
    {
      "rank": 1,
      "car_id": "...",
      "make": "...",
      "model": "...",
      "variant": "...",
      "price_lakhs": ...,
      "why": "...",
      "key_specs": {
        "mileage": "...",
        "fuel": "...",
        "transmission": "...",
        "seating": ...,
        "safety_stars": ...,
        "range_km": null
      }
    }
  ],
  "summary": "One sentence summary of the recommendation logic"
}

For EVs, set mileage to null and populate range_km instead."""


def get_recommendations(candidates: list, user_params: dict, user_message: str) -> dict:
    """Call OpenAI to rank candidates and generate explanations."""

    buyer_profile = _format_profile(user_params, user_message)

    user_content = f"""Buyer profile:
{buyer_profile}

Candidate cars:
{json.dumps(candidates, indent=2, ensure_ascii=False)}

Pick the best 3 cars for this buyer and explain why in their own terms."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )

    return json.loads(response.choices[0].message.content)


def get_followup_response(shortlist: list, user_message: str, chat_history: list) -> str:
    """Handle follow-up questions about the shortlist."""

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in chat_history[-6:]
    )

    prompt = f"""You are an expert Indian car buying advisor for CarDekho India. You help buyers choose from cars available in the Indian market.

## Scope rules — follow strictly:
1. If the question is NOT related to cars, automotive topics, or car buying decisions (e.g. sports, politics, celebrity info, general knowledge, coding, etc.) — respond only with:
   "I'm here to help you find and compare cars. I can't help with that, but feel free to ask me anything about car buying, specs, or comparisons!"
   Do not answer the off-topic question at all.

2. If the question is about a car or brand NOT present in CarDekho's catalog (e.g. Ferrari, Lamborghini, Rolls Royce, rare imports) — you may share brief general knowledge about that car, but always end with:
   "Note: This car isn't currently available in CarDekho's catalog. I can help you find the best options from our available range."

3. For everything else — car comparisons, specs, advice, shortlist questions — answer helpfully and concisely.

## Context:
Current shortlist shown to buyer:
{json.dumps(shortlist, indent=2)}

Recent conversation:
{history_text}

Buyer's question: {user_message}

Formatting rules:
- Use **bold** for car names, spec values, and key terms
- For comparisons: use a small markdown table or two clearly headed sections (e.g. ### Honda City vs Hyundai Verna)
- For detailed info on one car: use short bullet points grouped under a bold heading (e.g. **Performance**, **Comfort**, **Value**)
- For simple questions: 2-3 sentences is fine, still use **bold** for key terms
- Never write a wall of plain text — always add structure
- Keep it concise, under 200 words total"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def check_scope(message: str) -> str | None:
    """
    Returns a decline message if the input is off-topic, else None.
    Called before param extraction so guardrails apply from the very first message.
    """
    prompt = f"""You are a scope checker for a car buying assistant.

Classify this user message into one of two categories:
- "on_topic": anything related to cars, car buying, specs, brands, automotive topics, or providing car preferences (budget, fuel, seats, etc.)
- "off_topic": anything unrelated to cars or automotive topics (politics, sports, celebrities, general knowledge, coding, etc.)

Message: "{message}"

Respond with JSON only: {{"category": "on_topic"}} or {{"category": "off_topic"}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)
    if result.get("category") == "off_topic":
        return "I'm here to help you find and compare cars. I can't help with that, but feel free to ask me anything about car buying, specs, or comparisons!"
    return None


def extract_params_from_message(message: str, existing_params: dict, pending_params: list = None) -> dict:
    """Use OpenAI to extract car buying params from a free-text message."""

    pending_context = ""
    if pending_params:
        labels = {
            "budget": "budget",
            "use_case": "primary use (City/Highway/Mixed)",
            "seats": "number of seats needed",
            "fuel": "fuel preference",
            "transmission": "transmission preference (Manual/Automatic/Any)",
            "priority": "top priority (Mileage/Safety/Low Maintenance/Resale Value/Boot Space)",
        }
        asked = [labels[p] for p in pending_params if p in labels]
        pending_context = f"\nThe assistant had just asked the user about: {', '.join(asked)}. Interpret the user's reply in this context."

    prompt = f"""Extract car buying parameters from this message. Return only a JSON object.

Message: "{message}"
{pending_context}
Extract these fields (use null if not mentioned or not answerable from context):
- budget: number in lakhs (e.g. "10 lakhs" -> 10, "under 15L" -> 15, "10-15 lakhs" -> 12.5)
- use_case: one of "City", "Highway", "Mixed" (or null)
- seats: minimum seats needed as integer (e.g. "family of 4" -> 5, "7-seater" -> 7)
- fuel: one of "Petrol", "Diesel", "CNG", "Electric", "Hybrid", "Any" (or null)
- transmission: one of "Manual", "Automatic", "Any" (or null). "no preference" or "doesn't matter" -> "Any"
- priority: one of "Mileage", "Safety", "Low Maintenance", "Resale Value", "Boot Space" (or null)

Important:
- "no preference", "doesn't matter", "any", "open to all", "fine with anything" -> map to "Any" for whichever param was being asked
- If the user answers multiple params in one reply (e.g. "5 seats is fine, no preference, Safety"), map each answer to the pending params in order
- Do not override existing params unless the user explicitly changes them

Existing known params: {json.dumps(existing_params)}
Return JSON only."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    extracted = json.loads(response.choices[0].message.content)

    # Merge: existing params take precedence unless new value is not null
    merged = dict(existing_params)
    for key, val in extracted.items():
        if val is not None and val != "null":
            merged[key] = val
    return merged


def _format_profile(params: dict, message: str) -> str:
    lines = []
    if params.get("budget"):
        lines.append(f"- Budget: ₹{params['budget']} lakhs")
    if params.get("use_case"):
        lines.append(f"- Primary use: {params['use_case']}")
    if params.get("seats"):
        lines.append(f"- Minimum seats needed: {params['seats']}")
    if params.get("fuel"):
        lines.append(f"- Fuel preference: {params['fuel']}")
    if params.get("transmission"):
        lines.append(f"- Transmission preference: {params['transmission']}")
    if params.get("priority"):
        lines.append(f"- Top priority: {params['priority']}")
    if message:
        lines.append(f"- Original message: \"{message}\"")
    return "\n".join(lines) if lines else "No specific preferences provided."
