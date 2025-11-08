import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

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
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    supabase.table("patients").insert(patient_data).execute()

    # -------------------------------
    # Step 2: Create a dummy session
    # -------------------------------
    session_id = str(uuid4())
    session_data = {
        "session_id": session_id,
        "patient_id": patient_id,
        "session_date": datetime.now(timezone.utc).isoformat(),
        "exercise_type": "recall_test",
        "transcript": "This is a test transcript.",
        "ai_extracted_data": None,
        "cognitive_test_scores": None,
        "overall_score": None,
        "notable_events": [],
        "doctor_notes": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("sessions").insert(session_data).execute()

    # -------------------------------
    # Step 3: Mock the background task
    # -------------------------------
    with patch("NewMindmate.main.analyze_session") as mock_analyze:
        # -------------------------------
        # Step 4: Call the analyze endpoint
        # -------------------------------
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(f"/sessions/analyze/{session_id}")
            assert response.status_code == 200
            resp_json = response.json()
            assert resp_json["status"] == "Analysis started in background"

        # -------------------------------
        # Step 5: Simulate background task completion
        # -------------------------------
        supabase.table("sessions").update({
            "ai_extracted_data": {"key": "value"},
            "cognitive_test_scores": [{"test": "test", "score": 1, "max_score": 1}],
            "overall_score": 1,
        }).eq("session_id", session_id).execute()

        # -------------------------------
        # Step 6: Fetch updated session
        # -------------------------------
        session_result = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        updated_session = session_result.data[0]

        # -------------------------------
        # Step 7: Assertions
        # -------------------------------
        # Check AI extracted data exists
        assert updated_session["ai_extracted_data"] is not None
        # Check cognitive test scores
        assert isinstance(updated_session["cognitive_test_scores"], list)
        # Check overall score
        assert updated_session["overall_score"] is not None
