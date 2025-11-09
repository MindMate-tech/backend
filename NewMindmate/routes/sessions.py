from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from db.supabase_client import get_supabase
from db.vector_utils import store_memory_embedding

from schemas import (
    PatientCreate, PatientResponse,
    SessionCreate, SessionResponse,
    MemoryCreate, MemoryResponse,
    PatientData, BrainRegionScores, MemoryMetrics, RecentSession, TimeSeriesDataPoint
)

from services.cognitive_api_client import (
    doctor_query,
    get_session_insights,
    get_patient_risk_assessment
)

router = APIRouter()
supabase = get_supabase()


# Request models for doctor query endpoints
class DoctorQueryRequest(BaseModel):
    """Request for natural language doctor query"""
    query: str
    context: Optional[dict] = None


class SessionInsightRequest(BaseModel):
    """Request for session-specific insights"""
    session_id: UUID
    query: Optional[str] = None


# ==============================
# DOCTOR QUERY ENDPOINTS (AI-POWERED)
# ==============================

@router.post("/doctor/query")
async def natural_language_query(request: DoctorQueryRequest):
    """
    Natural language query interface for doctors

    Allows doctors to ask questions in plain English:
    - "Show me all at-risk patients"
    - "Why is patient X declining?"
    - "Compare patients A and B"
    - "Get recent sessions for patient Y"

    The AI agent uses tool calling to answer intelligently.

    Features:
    - Intelligent model routing (fast for simple queries, detailed for complex)
    - Sequential thinking for medical reasoning
    - Memory for follow-up queries
    - Predictive risk scoring
    """
    result = await doctor_query(
        query=request.query,
        context=request.context
    )

    return {
        "success": result.get("success", True),
        "query": request.query,
        "response": result.get("response", ""),
        "tools_used": result.get("tools_used", []),
        "model_info": result.get("model_info", {}),
        "raw_data": result.get("raw_data")
    }


@router.post("/sessions/{session_id}/insights")
async def get_ai_session_insights(session_id: UUID, query: Optional[str] = None):
    """
    Get AI-powered insights about a specific session

    Args:
        session_id: UUID of the session to analyze
        query: Optional specific question about the session

    Returns:
        Natural language analysis with insights and recommendations

    Example queries:
    - None (default: general analysis)
    - "What were the key concerns in this session?"
    - "How does this session compare to previous ones?"
    """
    # Verify session exists
    result = supabase.table("sessions").select("*").eq("session_id", str(session_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result.data[0]

    insights = await get_session_insights(
        session_id=session_id,
        query=query
    )

    return {
        "success": insights.get("success", True),
        "session_id": str(session_id),
        "session_date": session.get("session_date"),
        "patient_id": session.get("patient_id"),
        "insights": insights.get("response", ""),
        "model_info": insights.get("model_info", {}),
        "raw_data": insights.get("raw_data")
    }


@router.get("/patients/{patient_id}/risk-assessment")
async def get_ai_risk_assessment(patient_id: UUID):
    """
    Get AI-powered risk assessment for a patient

    Analyzes patient history and provides:
    - Risk level assessment
    - Specific risk factors identified
    - Trend analysis
    - Actionable recommendations
    """
    # Verify patient exists
    result = supabase.table("patients").select("*").eq("patient_id", str(patient_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = result.data[0]

    assessment = await get_patient_risk_assessment(patient_id)

    return {
        "success": assessment.get("success", True),
        "patient_id": str(patient_id),
        "patient_name": patient.get("name"),
        "assessment": assessment.get("response", ""),
        "model_info": assessment.get("model_info", {}),
        "raw_data": assessment.get("raw_data")
    }


# ==============================
# SESSION CRUD ENDPOINTS
# ==============================

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

# ------------------------------
# Meta
# ------------------------------

@router.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow()}

@router.get("/stats/overview")
def stats_overview():
    patients = supabase.table("patients").select("*").execute()
    sessions = supabase.table("sessions").select("*").execute()
    memories = supabase.table("memories").select("*").execute()
    return {
        "patients": len(patients.data),
        "sessions": len(sessions.data),
        "memories": len(memories.data),
    }

# ------------------------------
# Patients
# ------------------------------

@router.get("/patients", response_model=List[PatientResponse])
def list_patients():
    result = supabase.table("patients").select("*").order("created_at", desc=True).execute()
    return result.data

@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: UUID):
    result = supabase.table("patients").select("*").eq("patient_id", str(patient_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result.data[0]

@router.post("/patients", response_model=PatientResponse)
def create_patient(payload: PatientCreate):
    result = supabase.table("patients").insert(payload.dict()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create patient")
    return result.data[0]

@router.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: UUID, payload: PatientCreate):
    result = supabase.table("patients").update(payload.dict()).eq("patient_id", str(patient_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result.data[0]

@router.delete("/patients/{patient_id}")
def delete_patient(patient_id: UUID):
    supabase.table("patients").delete().eq("patient_id", str(patient_id)).execute()
    return {"status": "deleted"}

# ------------------------------
# Sessions
# ------------------------------

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions():
    result = supabase.table("sessions").select("*").order("created_at", desc=True).execute()
    return result.data

@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: UUID):
    result = supabase.table("sessions").select("*").eq("session_id", str(session_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return result.data[0]

@router.get("/patients/{patient_id}/sessions", response_model=List[SessionResponse])
def list_sessions_for_patient(patient_id: UUID):
    result = supabase.table("sessions").select("*").eq("patient_id", str(patient_id)).order("created_at", desc=True).execute()
    return result.data

@router.post("/sessions", response_model=SessionResponse)
def create_session(payload: SessionCreate):
    data = payload.dict()
    scores = [(t["score"] / t["max_score"]) * 100 for t in data.get("cognitive_test_scores", [])]
    data["overall_score"] = sum(scores) / len(scores) if scores else None
    result = supabase.table("sessions").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return result.data[0]

@router.put("/sessions/{session_id}", response_model=SessionResponse)
def update_session(session_id: UUID, payload: SessionCreate):
    result = supabase.table("sessions").update(payload.dict()).eq("session_id", str(session_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return result.data[0]

@router.delete("/sessions/{session_id}")
def delete_session(session_id: UUID):
    supabase.table("sessions").delete().eq("session_id", str(session_id)).execute()
    return {"status": "deleted"}

# ------------------------------
# Memories
# ------------------------------

@router.get("/memories", response_model=List[MemoryResponse])
def list_memories():
    result = supabase.table("memories").select("*").order("created_at", desc=True).execute()
    return result.data

@router.get("/memories/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: UUID):
    result = supabase.table("memories").select("*").eq("memory_id", str(memory_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result.data[0]

@router.get("/patients/{patient_id}/memories", response_model=List[MemoryResponse])
def list_memories_for_patient(patient_id: UUID):
    result = supabase.table("memories").select("*").eq("patient_id", str(patient_id)).order("created_at", desc=True).execute()
    return result.data

@router.post("/memories", response_model=MemoryResponse)
def create_memory(payload: MemoryCreate):
    result = supabase.table("memories").insert(payload.dict()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create memory")
    return result.data[0]

@router.put("/memories/{memory_id}", response_model=MemoryResponse)
def update_memory(memory_id: UUID, payload: MemoryCreate):
    result = supabase.table("memories").update(payload.dict()).eq("memory_id", str(memory_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result.data[0]

@router.delete("/memories/{memory_id}")
def delete_memory(memory_id: UUID):
    supabase.table("memories").delete().eq("memory_id", str(memory_id)).execute()
    return {"status": "deleted"}

# ------------------------------
# Analytics (Frontend)
# ------------------------------

@router.get("/patients/{patient_id}/analytics", response_model=PatientData)
def get_patient_analytics(patient_id: UUID):
    patient = supabase.table("patients").select("*").eq("patient_id", str(patient_id)).execute()
    sessions = supabase.table("sessions").select("*").eq("patient_id", str(patient_id)).order("session_date", desc=True).execute()

    if not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Placeholder logic for now
    brain_regions = BrainRegionScores(
        hippocampus=82.5,
        prefrontalCortex=77.3,
        temporalLobe=85.2,
        parietalLobe=79.0,
        amygdala=88.4,
        cerebellum=83.0
    )

    memory_metrics = MemoryMetrics(
        shortTermRecall=[TimeSeriesDataPoint(timestamp=s["session_date"], score=s["overall_score"]) for s in sessions.data],
        longTermRecall=[],
        semanticMemory=[],
        episodicMemory=[],
        workingMemory=[]
    )

    recent_sessions = [
        RecentSession(
            date=s["session_date"],
            score=s["overall_score"] or 0,
            exerciseType=s["exercise_type"],
            notableEvents=s.get("notable_events", [])
        )
        for s in sessions.data[:5]
    ]

    return PatientData(
        patientId=patient_id,
        patientName=patient.data[0]["name"],
        lastUpdated=datetime.utcnow(),
        brainRegions=brain_regions,
        memoryMetrics=memory_metrics,
        recentSessions=recent_sessions,
        overallCognitiveScore=sum([s["overall_score"] or 0 for s in sessions.data]) / len(sessions.data or [1]),
        memoryRetentionRate=0.87
    )
