from fastapi import APIRouter, BackgroundTasks
from models import CallEvent, ScoreResult
from services.cognee_service import get_caller_context, save_caller_context
from services.dify_service import trigger_dify_workflow
from services.scoring_service import score_lead
from services.sms_service import send_verification_sms

router = APIRouter()


@router.post("/call-started")
async def call_started(event: CallEvent, bg: BackgroundTasks):
    """HappyRobot fires this the moment a call connects."""
    # Pull memory — if they called before, we greet them by name
    context = await get_caller_context(event.phone_number)

    # Tell Dify: here's who's calling + their history
    workflow_input = {
        "caller_id":    context["caller_id"],
        "phone":        event.phone_number,
        "past_summary": context.get("summary", ""),
        "is_returning": bool(context.get("summary")),
        "mode":         event.mode.value,
        "language":     event.language,
    }
    dify_response = await trigger_dify_workflow("call_started", workflow_input)

    return {"status": "live", "greeting": dify_response.get("greeting"), "caller_id": context["caller_id"]}


@router.post("/call-ended")
async def call_ended(event: CallEvent, bg: BackgroundTasks):
    """HappyRobot fires this post-hang-up with the full transcript."""
    context = await get_caller_context(event.phone_number)

    # Score the lead — AI does the math, we verify with SMS
    result: ScoreResult = await score_lead(
        transcript=event.transcript,
        caller_id=context["caller_id"],
        mode=event.mode,
    )

    # Persist to Cognee so next call gets context
    bg.add_task(save_caller_context, event.phone_number, {
        "summary":     result.reasoning,
        "last_score":  result.score,
        "language":    event.language,
        "voice_gender": event.voice_gender,
    })

    # SMS fires for score >= 4 (hot leads need confirmation ASAP)
    if result.score >= 4:
        bg.add_task(send_verification_sms, event.phone_number, result)

    return {"lead_score": result.score, "sms_triggered": result.score >= 4}


@router.post("/transfer-human")
async def transfer_human(call_id: str, reason: str):
    """Triggered by Dify when caller anger detected — escalate NOW."""
    # In prod: hit HappyRobot's transfer API here
    return {"status": "transferring", "call_id": call_id, "reason": reason}


@router.post("/scam-drop")
async def scam_drop(call_id: str):
    """Politely nuke the call and save our GPU budget."""
    # In prod: HappyRobot end-call API
    return {"status": "terminated", "call_id": call_id}
