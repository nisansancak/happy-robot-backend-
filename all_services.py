"""
cognee_service.py — Long-term memory via Cognee Knowledge Graph
Phone number → unique CallerID → conversation history
"""
import hashlib, httpx, os

COGNEE_URL = os.getenv("COGNEE_URL", "http://localhost:8765")

def _phone_to_id(phone: str) -> str:
    """Stable ID — never store raw phone numbers in graph nodes."""
    return "caller_" + hashlib.sha256(phone.encode()).hexdigest()[:12]

async def get_caller_context(phone: str) -> dict:
    caller_id = _phone_to_id(phone)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{COGNEE_URL}/node/{caller_id}", timeout=3)
            data = r.json() if r.status_code == 200 else {}
        except Exception:
            data = {}  # Cognee down? Graceful degradation — still take the call
    return {"caller_id": caller_id, **data}

async def save_caller_context(phone: str, payload: dict):
    caller_id = _phone_to_id(phone)
    async with httpx.AsyncClient() as client:
        await client.post(f"{COGNEE_URL}/node/{caller_id}", json=payload, timeout=5)

# ---------------------------------------------------------------------------

"""
dify_service.py — Trigger Dify workflows for orchestration logic
"""
DIFY_URL  = os.getenv("DIFY_URL", "http://localhost:3001")
DIFY_KEY  = os.getenv("DIFY_API_KEY", "mock-key")

async def trigger_dify_workflow(workflow_name: str, inputs: dict) -> dict:
    """Fire and get Dify's response. Dify handles the big brain stuff."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{DIFY_URL}/v1/workflows/{workflow_name}/run",
                headers={"Authorization": f"Bearer {DIFY_KEY}"},
                json={"inputs": inputs},
                timeout=10,
            )
            return r.json()
        except Exception:
            return {"greeting": "Hello, how can I help you today?"}  # safe fallback

# ---------------------------------------------------------------------------

"""
scoring_service.py — 1-5 lead score via Gemini
Criteria: buying intent, budget signals, timeline, B2B qualifier
"""
import google.generativeai as genai
from models import ScoreResult, Mode

genai.configure(api_key=os.getenv("GOOGLE_API_KEY", "mock"))
_model = genai.GenerativeModel("gemini-1.5-flash")

SCORE_PROMPT = """
You are a sales qualification expert. Given this call transcript, score the lead from 1-5.

Scoring rubric:
5 = Ready to buy, has budget, has authority, clear timeline
4 = Strong interest, most signals present, minor friction
3 = Interested but unclear timeline or budget
2 = Weak interest, just browsing
1 = Wrong fit, no intent, or B2C caller in B2B mode

Mode: {mode}
Transcript: {transcript}

Respond ONLY as JSON: {{"score": <int>, "reasoning": "<one sentence>"}}
"""

async def score_lead(transcript: str, caller_id: str, mode: Mode) -> ScoreResult:
    prompt = SCORE_PROMPT.format(mode=mode.value, transcript=transcript)
    try:
        response = _model.generate_content(prompt)
        import json, re
        # strip any markdown fences Gemini loves to add
        raw = re.sub(r"```json|```", "", response.text).strip()
        data = json.loads(raw)
        return ScoreResult(score=data["score"], reasoning=data["reasoning"], sms_triggered=False)
    except Exception:
        return ScoreResult(score=2, reasoning="Could not parse transcript.", sms_triggered=False)

# ---------------------------------------------------------------------------

"""
sms_service.py — Post-deal SMS so hallucinations don't haunt us
"""
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "mock")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "mock")
TWILIO_FROM  = os.getenv("TWILIO_FROM_NUMBER", "+15005550006")

async def send_verification_sms(phone: str, result: ScoreResult):
    """
    Human-readable SMS confirmation — AI said we booked a meeting,
    let's make sure that's actually true before blocking a calendar slot.
    """
    message = (
        f"Hi! Your AI sales assistant just scheduled a meeting. "
        f"Details: {result.reasoning}. "
        f"Reply YES to confirm or NO to cancel. Powered by Happy Robot Club Mate."
    )
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                auth=(TWILIO_SID, TWILIO_TOKEN),
                data={"From": TWILIO_FROM, "To": phone, "Body": message},
            )
        except Exception:
            pass  # SMS failure is non-fatal — log it, don't crash
