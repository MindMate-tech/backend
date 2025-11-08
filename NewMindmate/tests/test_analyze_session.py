import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI
from httpx import AsyncClient

from NewMindmate.main import app  # your FastAPI app
from NewMindmate.db.supabase_client import get_supabase

supabase = get_supabase()


@pytest.mark.asyncio
async def test_analyze_session_flow():
    # -------------------------------
    # Step 1: Create a dummy patient
    # -------------------------------
    patient_id = str(uuid4())
    patient_data = {
        "patient_id": patient_id,
        "name": "Test Patient",
        "dob": "1970-01-01",
        "gender": "other",
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table("patients").insert(patient_data).execute()

    # -------------------------------
    # Step 2: Create a dummy session
    # -------------------------------
    session_id = str(uuid4())
    session_data = {
        "session_id": session_id,
        "patient_id": patient_id,
        "session_date": datetime.utcnow().isoformat(),
        "exercise_type": "recall_test",
        "transcript": None,
        "ai_extracted_data": None,
        "cognitive_test_scores": None,
        "overall_score": None,
        "notable_events": [],
        "doctor_notes": "",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": str(uuid4())
    }
    supabase.table("sessions").insert(session_data).execute()

    # -------------------------------
    # Step 3: Call the analyze endpoint
    # -------------------------------
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(f"/sessions/analyze/{session_id}")
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["status"] == "Analysis started"
        assert resp_json["session_id"] == session_id

    # -------------------------------
    # Step 4: Wait for background task to complete (simulate)
    # -------------------------------
    # In real test, you might mock Dedalus orchestrator to run instantly
    await asyncio.sleep(1)  # wait briefly for background task

    # -------------------------------
    # Step 5: Fetch updated session
    # -------------------------------
    session_result = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
    updated_session = session_result.data[0]

    # -------------------------------
    # Step 6: Assertions
    # -------------------------------
    # Check AI extracted data exists
    assert updated_session["ai_extracted_data"] is not None
    # Check cognitive test scores
    assert isinstance(updated_session["cognitive_test_scores"], list)
    # Check overall score
    assert updated_session["overall_score"] is not None

    # Optionally, check memories
    memories_result = supabase.table("memories").select("*").eq("patient_id", patient_id).execute()
    assert len(memories_result.data) > 0
    memory = memories_result.data[0]
    assert "title" in memory
    assert "description" in memory
    assert "embedding" in memory
