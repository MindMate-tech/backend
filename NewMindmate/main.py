from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.supabase_client import get_supabase
from routes import sessions


from uuid import UUID
from fastapi import BackgroundTasks


app = FastAPI(title="MindMate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/patients")
def list_patients():
    supabase = get_supabase()
    result = supabase.table("patients").select("*").execute()
    return result.data

@app.post("/patients")
def create_patient(payload: dict):
    supabase = get_supabase()
    result = supabase.table("patients").insert(payload).execute()
    return result.data


@app.post("/sessions/analyze/{session_id}")
def analyze_session(session_id: UUID, background_tasks: BackgroundTasks):
    session = db_fetch_session(session_id)  # existing DB fetch
    audio_url = session.get("audio_url")

    def run_agents():
        orchestrator.run({"patient_id": session["patient_id"], "audio_url": audio_url})

    background_tasks.add_task(run_agents)
    return {"status": "Analysis started in background."}
