# tests/test_doctors.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4
from NewMindmate.main import app
from datetime import datetime

client = TestClient(app)

# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client for all tests"""
    with patch("NewMindmate.main.get_supabase") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


# -----------------------------
# Test: Create Doctor
# -----------------------------
def test_create_doctor(mock_supabase):
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "doctor_id": str(uuid4()),
            "name": "Dr. Alice",
            "specialization": "Neurology",
            "email": "alice@hospital.org",
            "phone": "555-1234",
            "created_at": datetime.now().isoformat(),
        }
    ]

    payload = {
        "name": "Dr. Alice",
        "specialization": "Neurology",
        "email": "alice@hospital.org",
        "phone": "555-1234",
    }

    response = client.post("/doctors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dr. Alice"
    assert data["specialization"] == "Neurology"
    mock_supabase.table.assert_called_with("doctors")


# -----------------------------
# Test: List Doctors
# -----------------------------
def test_list_doctors(mock_supabase):
    mock_supabase.table.return_value.select.return_value.execute.return_value.data = [
        {
            "doctor_id": str(uuid4()),
            "name": "Dr. Bob",
            "specialization": "Psychiatry",
            "email": "bob@hospital.org",
            "phone": "555-5678",
            "created_at": datetime.now().isoformat(),
        }
    ]

    response = client.get("/doctors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Dr. Bob"


# -----------------------------
# Test: Create Doctor Record
# -----------------------------
def test_create_doctor_record(mock_supabase):
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "record_id": str(uuid4()),
            "doctor_id": str(uuid4()),
            "patient_id": str(uuid4()),
            "session_id": str(uuid4()),
            "record_type": "diagnosis",
            "summary": "Mild cognitive impairment",
            "detailed_notes": "Patient showing early signs of memory decline",
            "recommendations": "Increase physical activity",
            "created_at": datetime.now().isoformat(),
        }
    ]

    payload = {
        "doctor_id": str(uuid4()),
        "patient_id": str(uuid4()),
        "session_id": str(uuid4()),
        "record_type": "diagnosis",
        "summary": "Mild cognitive impairment",
        "detailed_notes": "Patient showing early signs of memory decline",
        "recommendations": "Increase physical activity",
    }

    response = client.post("/doctor-records", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["record_type"] == "diagnosis"
    assert "record_id" in data
    mock_supabase.table.assert_called_with("doctor_records")


# -----------------------------
# Test: Get Patient Records
# -----------------------------
def test_get_patient_records(mock_supabase):
    pid = str(uuid4())
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "record_id": str(uuid4()),
            "doctor_id": str(uuid4()),
            "patient_id": pid,
            "session_id": str(uuid4()),
            "record_type": "note",
            "summary": "Follow-up scheduled",
            "detailed_notes": "Patient was responsive.",
            "recommendations": "Continue with current treatment.",
            "created_at": datetime.now().isoformat(),
        }
    ]

    response = client.get(f"/doctor-records/{pid}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["record_type"] == "note"
    assert data[0]["patient_id"] == pid
