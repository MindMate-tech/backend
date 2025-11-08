import uuid
from datetime import datetime
from NewMindmate.db.supabase_client import get_supabase

supabase = get_supabase()

# ------------------------------
# Step 1: Create a patient
# ------------------------------
patient_payload = {
    "name": "Alice Example",
    "dob": "1980-06-15",
    "gender": "female"
}

patient_result = supabase.table("patients").insert(patient_payload).execute()
if not patient_result.data:
    raise RuntimeError(f"Failed to create patient: {patient_result}")

patient = patient_result.data[0]
patient_id = patient["patient_id"]
print(f"Created patient: {patient_id}, name: {patient['name']}")

# ------------------------------
# Step 2: Create a session
# ------------------------------
session_payload = {
    "patient_id": patient_id,
    "exercise_type": "memory_recall",
    "transcript": "Patient talked about visiting her granddaughter in Boston last month.",
}

session_result = supabase.table("sessions").insert(session_payload).execute()
if not session_result.data:
    raise RuntimeError(f"Failed to create session: {session_result}")

session = session_result.data[0]
session_id = session["session_id"]
print(f"Created session: {session_id}, transcript: {session_payload['transcript']}")

# ------------------------------
# Step 3: Analyze session (AI placeholder)
# ------------------------------
ai_extracted_data = {
    "memories": [
        {
            "title": "Visit to Boston",
            "description": "Patient visited granddaughter in Boston",
            "dateapprox": "2025-10-01",
            "tags": ["family", "travel"],
            "emotional_tone": "happy"
        }
    ],
    "cognitive_test_scores": [
        {"test": "recall", "score": 8, "max_score": 10}
    ]
}

# Compute overall score
scores = [(t["score"] / t["max_score"]) * 100 for t in ai_extracted_data["cognitive_test_scores"]]
overall_score = sum(scores) / len(scores)

# Update session
update_data = {
    "ai_extracted_data": ai_extracted_data,
    "cognitive_test_scores": ai_extracted_data["cognitive_test_scores"],
    "overall_score": overall_score
}

update_result = supabase.table("sessions").update(update_data).eq("session_id", session_id).execute()
if not update_result.data:
    raise RuntimeError(f"Failed to update session: {update_result}")

print(f"Session analyzed. Overall score: {overall_score}")

# ------------------------------
# Step 4: List all sessions for this patient
# ------------------------------
sessions_result = supabase.table("sessions").select("*").eq("patient_id", patient_id).order("session_date", desc=True).execute()
if not sessions_result.data:
    raise RuntimeError(f"Failed to fetch sessions: {sessions_result}")

print("\nAll sessions for patient:")
for s in sessions_result.data:
    print(f"- {s['session_id']}: score={s.get('overall_score')} transcript={s.get('transcript')}")
