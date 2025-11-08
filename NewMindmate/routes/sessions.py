from fastapi import APIRouter, HTTPException
from uuid import UUID
from datetime import datetime
from typing import List

from schemas import SessionCreate, SessionResponse
from db.supabase_client import get_supabase

from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import UUID
from datetime import datetime

from db.supabase_client import get_supabase
from db.vector_utils import store_memory_embedding

router = APIRouter(prefix="/sessions", tags=["sessions"])
supabase = get_supabase()

# ------------------------------
# Create a new session
# ------------------------------
@router.post("/", response_model=SessionResponse)
def create_session(session: SessionCreate):
    # Default session date
    session_date = session.session_date or datetime.utcnow()

    # Compute overall score if test scores provided
    overall_score = None
    if session.cognitive_test_scores:
        scores = [(t.score / t.max_score) * 100 for t in session.cognitive_test_scores]
        overall_score = sum(scores) / len(scores)

    session_data = session.dict()
    session_data.update({
        "session_date": session_date.isoformat(),
        "overall_score": overall_score,
        "created_at": datetime.utcnow().isoformat()
    })

    result = supabase.table("sessions").insert(session_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {result}")

    return SessionResponse(**result.data[0])

# ------------------------------
# Get sessions for a patient
# ------------------------------
@router.get("/patient/{patient_id}", response_model=List[SessionResponse])
def get_sessions(patient_id: UUID):
    result = (
        supabase.table("sessions")
        .select("*")
        .eq("patient_id", str(patient_id))
        .order("session_date", desc=True)
        .execute()
    )
    if not result.data:
        return []

    return [SessionResponse(**row) for row in result.data]

# ------------------------------
# Analyze session (AI placeholder)
# ------------------------------

router = APIRouter()
supabase = get_supabase()

# ------------------------------
# Analyze session (Dedalus + vector embeddings)
# ------------------------------
@router.post("/analyze/{session_id}", response_model=SessionResponse)
def analyze_session(session_id: UUID, background_tasks: BackgroundTasks):
    """
    Trigger AI analysis on a session:
    1. Lookup patient history
    2. Transcribe audio (if available)
    3. Generate memory embeddings
    4. Update cognitive test scores and overall_score
    """
    # Fetch session from Supabase
    result = supabase.table("sessions").select("*").eq("session_id", str(session_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result.data[0]
    patient_id = session["patient_id"]
    audio_url = session.get("audio_url")  # optional field


    # Return immediately
    return {"status": "Analysis started in background.", "session_id": str(session_id)}
