from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from NewMindmate.db.supabase_client import get_supabase
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from NewMindmate.schemas import DoctorCreate, DoctorResponse, DoctorRecordCreate, DoctorRecordResponse, PatientResponse, PatientCreate, SessionResponse, SessionCreate, MemoryResponse, MemoryCreate
from NewMindmate.routes.cognitive_routes import router as cognitive_router

# ------------------------------
# App Initialization
# ------------------------------
app = FastAPI(title="MindMate API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Include Cognitive API Routes
# ------------------------------
app.include_router(cognitive_router)

# ------------------------------
# Health Check
# ------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "MindMate API running"}

# ------------------------------
# Patients
# ------------------------------
@app.get("/patients", response_model=List[PatientResponse])
def list_patients():
    supabase = get_supabase()
    result = supabase.table("patients").select("*").execute()
    return result.data

@app.post("/patients", response_model=PatientResponse)
def create_patient(payload: PatientCreate):
    supabase = get_supabase()
    result = supabase.table("patients").insert(payload.model_dump()).execute()
    return result.data[0]

# ------------------------------
# Sessions
# ------------------------------
@app.get("/sessions", response_model=List[SessionResponse])
def list_sessions():
    supabase = get_supabase()
    result = supabase.table("sessions").select("*").execute()
    return result.data

@app.post("/sessions", response_model=SessionResponse)
def create_session(payload: SessionCreate):
    supabase = get_supabase()
    result = supabase.table("sessions").insert(payload.model_dump()).execute()
    return result.data[0]

@app.post("/sessions/analyze/{session_id}")
def analyze_session(session_id: UUID, background_tasks: BackgroundTasks):
    supabase = get_supabase()
    session = supabase.table("sessions").select("*").eq("session_id", str(session_id)).single().execute()

    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    def mock_analysis():
        print(f"[INFO] Background analysis started for session {session_id}")

    background_tasks.add_task(mock_analysis)
    return {"status": "Analysis started in background"}

# ------------------------------
# Memories
# ------------------------------
@app.get("/memories", response_model=List[MemoryResponse])
def list_memories():
    supabase = get_supabase()
    result = supabase.table("memories").select("*").execute()
    return result.data

@app.post("/memories", response_model=MemoryResponse)
def create_memory(payload: MemoryCreate):
    supabase = get_supabase()
    result = supabase.table("memories").insert(payload.model_dump()).execute()
    return result.data[0]


# ----------------------
# Doctors
# ----------------------
@app.get("/doctors", response_model=list[DoctorResponse])
def list_doctors():
    supabase = get_supabase()
    result = supabase.table("doctors").select("*").execute()
    return result.data

@app.post("/doctors", response_model=DoctorResponse)
def create_doctor(payload: DoctorCreate):
    supabase = get_supabase()
    result = supabase.table("doctors").insert(payload.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create doctor")
    return result.data[0]

# ----------------------
# Doctor Records
# ----------------------
@app.get("/doctor-records/{patient_id}", response_model=list[DoctorRecordResponse])
def get_patient_records(patient_id: UUID):
    supabase = get_supabase()
    result = supabase.table("doctor_records").select("*").eq("patient_id", str(patient_id)).execute()
    return result.data

@app.post("/doctor-records", response_model=DoctorRecordResponse)
def create_doctor_record(payload: DoctorRecordCreate):
    supabase = get_supabase()
    result = supabase.table("doctor_records").insert(payload.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create doctor record")
    return result.data[0]

