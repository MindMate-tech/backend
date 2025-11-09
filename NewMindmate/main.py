from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from NewMindmate.db.supabase_client import get_supabase
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
import os
from pathlib import Path
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

# ------------------------------
# Audio Upload Response Schema
# ------------------------------
class AudioUploadResponse(BaseModel):
    success: bool
    file_path: str
    public_url: str
    file_size: int
    content_type: str
    session_id: Optional[UUID] = None
    message: str

# ------------------------------
# Audio Upload Helper Functions
# ------------------------------
AUDIO_BUCKET_NAME = os.getenv("SUPABASE_AUDIO_BUCKET", "audio")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}

def upload_audio_to_supabase_storage(
    file_content: bytes,
    file_path: str,
    content_type: str
) -> dict:
    """
    Upload audio file to Supabase Storage.
    
    Returns:
        dict with 'path' and 'public_url' keys
    """
    supabase = get_supabase()
    
    try:
        # Upload file to Supabase Storage
        # Supabase Python client returns a tuple (data, error)
        data, error = supabase.storage.from_(AUDIO_BUCKET_NAME).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": content_type, "upsert": "false"}
        )
        
        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload audio to Supabase Storage: {error.message if hasattr(error, 'message') else str(error)}"
            )
        
        # Extract path from response (may be in data dict or use original path)
        uploaded_path = file_path
        if isinstance(data, dict) and 'path' in data:
            uploaded_path = data['path']
        elif hasattr(data, 'path'):
            uploaded_path = data.path
        
        # Get public URL
        url_response = supabase.storage.from_(AUDIO_BUCKET_NAME).get_public_url(uploaded_path)
        
        # Extract public URL from response
        public_url = ""
        if isinstance(url_response, dict):
            public_url = url_response.get('publicUrl', url_response.get('public_url', ''))
        elif hasattr(url_response, 'publicUrl'):
            public_url = url_response.publicUrl
        elif isinstance(url_response, str):
            public_url = url_response
        else:
            # Fallback: construct URL manually
            supabase_url = os.getenv("SUPABASE_URL", "")
            if supabase_url:
                public_url = f"{supabase_url}/storage/v1/object/public/{AUDIO_BUCKET_NAME}/{uploaded_path}"
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to construct public URL: SUPABASE_URL not configured"
                )
        
        return {
            "path": uploaded_path,
            "public_url": public_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error uploading audio: {str(e)}"
        )

# ------------------------------
# Audio Upload Endpoint
# ------------------------------
@app.post("/audio/upload", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(..., description="Audio file to upload"),
    patient_id: Optional[UUID] = Form(None, description="Patient ID for organizing files"),
    session_id: Optional[UUID] = Form(None, description="Session ID to link audio to")
):
    """
    Upload an audio file to Supabase Storage.
    
    - **file**: Audio file (MP3, WAV, FLAC, M4A, OGG, AAC)
    - **patient_id**: Optional patient ID for file organization
    - **session_id**: Optional session ID to update with audio_url
    
    Returns the public URL and optionally updates the session.
    """
    # Validate file type
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Allowed types: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size} bytes. Maximum size: {MAX_FILE_SIZE} bytes (50MB)"
        )
    
    # Validate patient_id exists if provided
    if patient_id:
        supabase = get_supabase()
        patient = supabase.table("patients").select("*").eq("patient_id", str(patient_id)).execute()
        if not patient.data:
            raise HTTPException(status_code=404, detail=f"Patient not found: {patient_id}")
    
    # Validate session_id exists if provided
    if session_id:
        supabase = get_supabase()
        session = supabase.table("sessions").select("*").eq("session_id", str(session_id)).execute()
        if not session.data:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    # Generate file path
    timestamp = int(datetime.utcnow().timestamp() * 1000)  # milliseconds
    safe_filename = file.filename.replace(" ", "_")
    
    if patient_id:
        file_path = f"audio/{patient_id}/{timestamp}-{safe_filename}"
    else:
        file_path = f"audio/{timestamp}-{safe_filename}"
    
    # Determine content type
    content_type = file.content_type or "audio/wav"
    if not content_type.startswith("audio/"):
        # Map extension to content type
        content_type_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.aac': 'audio/aac'
        }
        content_type = content_type_map.get(file_extension, 'audio/wav')
    
    # Upload to Supabase Storage
    try:
        upload_result = upload_audio_to_supabase_storage(
            file_content,
            file_path,
            content_type
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload audio: {str(e)}"
        )
    
    # Update session with audio_url if session_id provided
    updated_session_id = None
    if session_id:
        supabase = get_supabase()
        update_result = supabase.table("sessions").update({
            "audio_url": upload_result["public_url"]
        }).eq("session_id", str(session_id)).execute()
        
        if not update_result.data:
            # Log warning but don't fail the upload
            print(f"Warning: Failed to update session {session_id} with audio_url")
        else:
            updated_session_id = session_id
    
    return AudioUploadResponse(
        success=True,
        file_path=upload_result["path"],
        public_url=upload_result["public_url"],
        file_size=file_size,
        content_type=content_type,
        session_id=updated_session_id,
        message="Audio uploaded successfully"
    )

