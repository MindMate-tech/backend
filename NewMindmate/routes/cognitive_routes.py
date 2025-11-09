"""
Cognitive API Integration Routes
New endpoints that use the Cognitive API for real AI-powered analysis
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import UUID
from datetime import datetime
from typing import List
from NewMindmate.db.supabase_client import get_supabase
from NewMindmate.db.vector_utils import store_memory_embedding
from NewMindmate.schemas import PatientData
from NewMindmate.services.cognitive_api_client import (
    analyze_session_with_ai,
    get_patient_dashboard,
    health_check as cognitive_health_check
)

router = APIRouter(prefix="/cognitive", tags=["cognitive"])
supabase = get_supabase()


@router.get("/health")
async def check_cognitive_api_health():
    """Check if Cognitive API is reachable"""
    health = await cognitive_health_check()
    return health


@router.post("/sessions/{session_id}/analyze")
async def analyze_session_with_cognitive_api(session_id: UUID, background_tasks: BackgroundTasks):
    """
    Analyze session using Cognitive API (NEW - uses real AI)

    This is the NEW endpoint that calls the deployed Cognitive API
    """

    # Fetch session
    result = supabase.table("sessions").select("*").eq("session_id", str(session_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result.data[0]
    patient_id = session["patient_id"]

    # Fetch patient
    patient_result = supabase.table("patients").select("*").eq("patient_id", patient_id).execute()
    if not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_data = patient_result.data[0]

    # Fetch previous sessions for context
    prev_sessions = (
        supabase.table("sessions")
        .select("*")
        .eq("patient_id", patient_id)
        .order("session_date", desc=True)
        .limit(5)
        .execute()
    )

    async def run_analysis():
        """Background task to run AI analysis"""
        try:
            print(f"🧠 Starting Cognitive API analysis for session {session_id}")

            # CALL COGNITIVE API
            analysis = await analyze_session_with_ai(
                session_id=session_id,
                patient_id=UUID(patient_id),
                transcript=session.get("transcript", ""),
                patient_data=patient_data,
                previous_sessions=prev_sessions.data
            )

            print(f"✅ Analysis complete! Overall score: {analysis['overall_score']:.1%}")

            # Store results in Supabase
            supabase.table("sessions").update({
                "ai_extracted_data": analysis,
                "cognitive_test_scores": analysis.get("cognitive_test_scores", []),
                "overall_score": analysis.get("overall_score"),
                "notable_events": analysis.get("notable_events", [])
            }).eq("session_id", str(session_id)).execute()

            print(f"💾 Stored analysis in Supabase")

            # Store extracted memories in ChromaDB
            for memory in analysis.get("memories", []):
                try:
                    store_memory_embedding(
                        supabase,
                        patient_id=patient_id,
                        title=memory.get("title", "Memory"),
                        description=memory.get("description", ""),
                        embedding=memory.get("embedding"),
                        dateapprox=memory.get("dateapprox"),
                        location=memory.get("location"),
                        emotional_tone=memory.get("emotional_tone"),
                        tags=memory.get("tags", []),
                        significance_level=memory.get("significance_level", 1)
                    )
                    print(f"📝 Stored memory: {memory.get('title')}")
                except Exception as e:
                    print(f"⚠️  Failed to store memory: {e}")

            print(f"🎉 Analysis pipeline complete for session {session_id}")

        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            # Store error in session
            supabase.table("sessions").update({
                "ai_extracted_data": {"error": str(e)}
            }).eq("session_id", str(session_id)).execute()

    # Run analysis in background
    background_tasks.add_task(run_analysis)

    return {
        "status": "Analysis started in background",
        "session_id": str(session_id),
        "message": "Check back in 60-120 seconds for results"
    }


@router.get("/patients/{patient_id}/analytics")
async def get_patient_analytics_from_cognitive_api(patient_id: UUID):
    """
    Get patient analytics using Cognitive API (NEW - returns REAL data)

    This replaces the hardcoded brain regions with real AI-powered analysis
    """

    # Fetch patient
    patient_result = supabase.table("patients").select("*").eq("patient_id", str(patient_id)).execute()
    if not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = patient_result.data[0]

    # Fetch all sessions
    sessions_result = (
        supabase.table("sessions")
        .select("*")
        .eq("patient_id", str(patient_id))
        .order("session_date", desc=True)
        .limit(30)
        .execute()
    )

    # Check for MRI data (optional)
    mri_path = f"data/mri_outputs/report_{patient_id}.csv"

    try:
        # Call Cognitive API for dashboard data
        dashboard = await get_patient_dashboard(
            patient_id=patient_id,
            patient_name=patient["name"],
            sessions=sessions_result.data,
            mri_csv_path=mri_path
        )

        return dashboard  # Already in PatientData format!

    except Exception as e:
        print(f"❌ Cognitive API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analytics: {str(e)}"
        )


@router.get("/patients/{patient_id}/cognitive-data")
async def get_patient_cognitive_data(patient_id: UUID):
    """
    Alias endpoint for frontend compatibility

    Frontend calls /cognitive-data but backend has /analytics
    This endpoint bridges the gap
    """
    return await get_patient_analytics_from_cognitive_api(patient_id)
