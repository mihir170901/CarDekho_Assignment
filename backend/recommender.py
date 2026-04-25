import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert Indian car buying advisor. Your job is to help confused buyers find their perfect car.

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

    prompt = f"""You are an expert Indian car buying advisor.

The buyer has already received this shortlist:
{json.dumps(shortlist, indent=2)}

Recent conversation:
{history_text}

Buyer's follow-up question: {user_message}

Answer concisely and helpfully. Reference specific cars from the shortlist by name.
If asked to compare, give a direct recommendation. Keep it under 150 words."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content


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
