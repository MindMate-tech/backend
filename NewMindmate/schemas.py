from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, date
from uuid import UUID

# ------------------------------
# Cognitive Test Result
# ------------------------------
class CognitiveTestScore(BaseModel):
    test: str
    score: float
    max_score: float

# ------------------------------
# Memory Object
# ------------------------------
class MemoryCreate(BaseModel):
    title: str
    description: str
    dateapprox: Optional[date]
    location: Optional[str]
    peopleinvolved: Optional[List[str]] = []
    emotional_tone: Optional[str]
    tags: Optional[List[str]] = []
    significance_level: Optional[int] = 1

class MemoryResponse(MemoryCreate):
    memory_id: UUID
    patient_id: UUID
    created_at: datetime
    embedding: Optional[List[float]] = None

# ------------------------------
# Session
# ------------------------------
class SessionCreate(BaseModel):
    patient_id: UUID
    session_date: Optional[datetime] = None
    exercise_type: Optional[str] = "memory_recall"
    transcript: Optional[str] = ""
    ai_extracted_data: Optional[dict] = {}
    cognitive_test_scores: Optional[List[CognitiveTestScore]] = []
    notable_events: Optional[List[str]] = []
    doctor_notes: Optional[str] = None

class SessionResponse(SessionCreate):
    session_id: UUID
    overall_score: Optional[float] = None
    created_at: datetime

# ------------------------------
# Patient
# ------------------------------
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List

class PatientCreate(BaseModel):
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None

class PatientResponse(PatientCreate):
    patient_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # For ORM & dict compatibility


# ------------------------------
# Cognitive Metrics for frontend
# ------------------------------
class BrainRegionScores(BaseModel):
    hippocampus: float
    prefrontalCortex: float
    temporalLobe: float
    parietalLobe: float
    amygdala: float
    cerebellum: float

class TimeSeriesDataPoint(BaseModel):
    timestamp: datetime
    score: float

class MemoryMetrics(BaseModel):
    shortTermRecall: List[TimeSeriesDataPoint] = []
    longTermRecall: List[TimeSeriesDataPoint] = []
    semanticMemory: List[TimeSeriesDataPoint] = []
    episodicMemory: List[TimeSeriesDataPoint] = []
    workingMemory: List[TimeSeriesDataPoint] = []

class RecentSession(BaseModel):
    date: datetime
    score: float
    exerciseType: str
    notableEvents: List[str] = []

class PatientData(BaseModel):
    patientId: UUID
    patientName: str
    lastUpdated: datetime
    brainRegions: BrainRegionScores
    memoryMetrics: MemoryMetrics
    recentSessions: List[RecentSession] = []
    overallCognitiveScore: float
    memoryRetentionRate: float

class DoctorCreate(BaseModel):
    name: str
    specialization: Optional[str]
    email: Optional[str]
    phone: Optional[str]

class DoctorResponse(DoctorCreate):
    doctor_id: UUID
    created_at: datetime

class DoctorRecordCreate(BaseModel):
    doctor_id: UUID
    patient_id: UUID
    session_id: Optional[UUID]
    record_type: Optional[str]
    summary: Optional[str]
    detailed_notes: Optional[str]
    recommendations: Optional[str]

class DoctorRecordResponse(DoctorRecordCreate):
    record_id: UUID
    created_at: datetime
