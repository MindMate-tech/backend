"""
Cognitive API Client
Integration with MindMate Cognitive Analysis microservice
"""
import httpx
from uuid import UUID
from typing import Dict, List, Optional
from datetime import datetime


# Your deployed Cognitive API (use local for testing if Render is sleeping)
# COGNITIVE_API_URL = "http://localhost:8000"  # Local for testing
COGNITIVE_API_URL = "https://mindmate-cognitive-api.onrender.com"  # Production


async def analyze_session_with_ai(
    session_id: UUID,
    patient_id: UUID,
    transcript: str,
    patient_data: Dict,
    previous_sessions: Optional[List[Dict]] = None
) -> Dict:
    """
    Call MindMate Cognitive API to analyze a session

    Args:
        session_id: Session UUID
        patient_id: Patient UUID
        transcript: Full conversation transcript
        patient_data: Patient profile from Supabase
        previous_sessions: Recent historical sessions for context

    Returns:
        Complete analysis with memories, scores, metrics, alerts
    """

    # Calculate patient age
    age = calculate_age(patient_data.get("dob"))

    payload = {
        "session_id": str(session_id),
        "patient_id": str(patient_id),
        "transcript": transcript,
        "exercise_type": "memory_recall",
        "session_date": datetime.utcnow().isoformat(),
        "patient_profile": {
            "name": patient_data.get("name", "Patient"),
            "age": age,
            "diagnosis": patient_data.get("diagnosis", ""),
            "interests": patient_data.get("interests", []),
            "expected_info": {
                "family_members": [],
                "profession": "",
                "hometown": ""
            }
        },
        "previous_sessions": previous_sessions or []
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{COGNITIVE_API_URL}/analyze/session",
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"Cognitive API error: {response.text}")

            result = response.json()
            return result["data"]

    except httpx.TimeoutException:
        raise Exception("Cognitive API timeout - analysis takes 60-120 seconds")
    except Exception as e:
        raise Exception(f"Failed to call Cognitive API: {str(e)}")


async def get_patient_dashboard(
    patient_id: UUID,
    patient_name: str,
    sessions: List[Dict],
    mri_csv_path: Optional[str] = None
) -> Dict:
    """
    Get complete dashboard data formatted for frontend

    Args:
        patient_id: Patient UUID
        patient_name: Patient name
        sessions: Historical sessions from Supabase
        mri_csv_path: Optional path to MRI CSV file

    Returns:
        PatientData formatted for frontend (brain regions, memory metrics, etc.)
    """

    payload = {
        "patient_id": str(patient_id),
        "patient_name": patient_name,
        "sessions": sessions,
        "mri_csv_path": mri_csv_path,
        "days_back": 30
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{COGNITIVE_API_URL}/patient/dashboard",
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"Cognitive API error: {response.text}")

            result = response.json()
            return result["data"]

    except httpx.TimeoutException:
        raise Exception("Cognitive API timeout")
    except Exception as e:
        raise Exception(f"Failed to get dashboard: {str(e)}")


async def health_check() -> Dict:
    """Check if Cognitive API is healthy"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{COGNITIVE_API_URL}/health")
            return response.json()
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def doctor_query(query: str, context: Optional[Dict] = None) -> Dict:
    """
    Natural language query interface for doctors

    Uses AI agent with tool calling to answer questions about patients and sessions.

    Args:
        query: Natural language question (e.g., "Show me at-risk patients")
        context: Optional context (doctor_id, patient_id, session_id, etc.)

    Returns:
        Dict with:
            - success: bool
            - query: str (original query)
            - response: str (AI-generated response)
            - tools_used: List[str]
            - model_info: Dict (model selection info, complexity, etc.)
            - raw_data: Dict (raw tool results)

    Examples:
        - "Show me all at-risk patients"
        - "Why is this patient declining?"
        - "Get recent sessions for patient X"
        - "Compare these two patients"
    """
    try:
        payload = {
            "query": query,
            "context": context or {}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COGNITIVE_API_URL}/doctor/query",
                json=payload
            )

            if response.status_code != 200:
                raise Exception(f"Doctor query API error: {response.text}")

            return response.json()

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Query timeout",
            "query": query
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


async def get_session_insights(session_id: UUID, query: Optional[str] = None) -> Dict:
    """
    Get AI-powered insights about a specific session

    Args:
        session_id: UUID of the session
        query: Optional specific question about the session
                If None, returns general session analysis

    Returns:
        AI analysis of the session with natural language response
    """
    default_query = f"Analyze session {session_id} and provide detailed insights about performance, concerns, and recommendations"

    result = await doctor_query(
        query=query or default_query,
        context={"session_id": str(session_id)}
    )

    return result


async def get_patient_risk_assessment(patient_id: UUID) -> Dict:
    """
    Get AI risk assessment for a specific patient

    Args:
        patient_id: UUID of the patient

    Returns:
        Risk assessment with reasoning and recommendations
    """
    result = await doctor_query(
        query=f"Analyze patient {patient_id} and identify any risk factors or concerns",
        context={"patient_id": str(patient_id)}
    )

    return result


def calculate_age(dob) -> int:
    """Calculate age from date of birth"""
    if not dob:
        return 0

    try:
        birth_date = datetime.fromisoformat(str(dob).replace('Z', ''))
        today = datetime.utcnow()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    except:
        return 0
