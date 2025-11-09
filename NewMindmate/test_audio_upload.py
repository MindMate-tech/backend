# test_audio_upload.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
from uuid import uuid4
from io import BytesIO
from NewMindmate.main import app
from datetime import datetime
import os

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


@pytest.fixture
def sample_audio_file():
    """Fixture to create a sample audio file for testing"""
    # Create a small WAV file header (minimal valid WAV file)
    # This is just enough to pass file type validation
    wav_header = b'RIFF' + b'\x24\x08\x00\x00' + b'WAVE' + b'fmt ' + b'\x10\x00\x00\x00' + b'\x01\x00' + b'\x01\x00' + b'\x44\xac\x00\x00' + b'\x88\x58\x01\x00' + b'\x02\x00' + b'\x10\x00' + b'data' + b'\x00\x08\x00\x00'
    audio_data = wav_header + b'\x00' * 1000  # Add some data
    return BytesIO(audio_data)


@pytest.fixture
def large_audio_file():
    """Fixture to create a large audio file (>50MB) for size validation testing"""
    # Create a file larger than 50MB
    large_data = b'\x00' * (51 * 1024 * 1024)  # 51MB
    return BytesIO(large_data)


# -----------------------------
# Test: Successful Audio Upload (no patient_id or session_id)
# -----------------------------
def test_upload_audio_success(mock_supabase, sample_audio_file):
    """Test successful audio upload without patient_id or session_id"""
    # Mock Supabase Storage upload
    mock_storage = MagicMock()
    mock_storage.from_.return_value.upload.return_value = (
        {"path": "audio/1731234567890-test.wav"},
        None  # No error
    )
    mock_storage.from_.return_value.get_public_url.return_value = {
        "publicUrl": "https://project.supabase.co/storage/v1/object/public/audio/audio/1731234567890-test.wav"
    }
    mock_supabase.storage = mock_storage
    
    # Mock environment variable
    with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
        response = client.post(
            "/audio/upload",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "file_path" in data
    assert "public_url" in data
    assert data["file_size"] > 0
    assert data["content_type"] == "audio/wav"
    assert data["session_id"] is None
    assert data["message"] == "Audio uploaded successfully"


# -----------------------------
# Test: Successful Audio Upload with patient_id
# -----------------------------
def test_upload_audio_with_patient_id(mock_supabase, sample_audio_file):
    """Test successful audio upload with patient_id"""
    patient_id = str(uuid4())
    
    # Mock patient exists
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"patient_id": patient_id, "name": "Test Patient"}
    ]
    mock_supabase.table.return_value = mock_table
    
    # Mock Supabase Storage
    mock_storage = MagicMock()
    mock_storage.from_.return_value.upload.return_value = (
        {"path": f"audio/{patient_id}/1731234567890-test.wav"},
        None
    )
    mock_storage.from_.return_value.get_public_url.return_value = {
        "publicUrl": f"https://project.supabase.co/storage/v1/object/public/audio/audio/{patient_id}/1731234567890-test.wav"
    }
    mock_supabase.storage = mock_storage
    
    with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
        response = client.post(
            "/audio/upload",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            data={"patient_id": patient_id},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert patient_id in data["file_path"]
    assert data["session_id"] is None


# -----------------------------
# Test: Successful Audio Upload with session_id (updates session)
# -----------------------------
def test_upload_audio_with_session_id(mock_supabase, sample_audio_file):
    """Test successful audio upload with session_id and verify session is updated"""
    patient_id = str(uuid4())
    session_id = str(uuid4())
    
    # Mock patient exists
    mock_patient_table = MagicMock()
    mock_patient_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"patient_id": patient_id, "name": "Test Patient"}
    ]
    
    # Mock session exists
    mock_session_table = MagicMock()
    mock_session_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"session_id": session_id, "patient_id": patient_id}
    ]
    mock_session_table.update.return_value.eq.return_value.execute.return_value.data = [
        {"session_id": session_id, "audio_url": "https://project.supabase.co/storage/v1/object/public/audio/test.wav"}
    ]
    
    # Configure table mock to return different mocks based on table name
    def table_side_effect(table_name):
        if table_name == "patients":
            return mock_patient_table
        elif table_name == "sessions":
            return mock_session_table
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    # Mock Supabase Storage
    mock_storage = MagicMock()
    public_url = "https://project.supabase.co/storage/v1/object/public/audio/test.wav"
    mock_storage.from_.return_value.upload.return_value = (
        {"path": "audio/test.wav"},
        None
    )
    mock_storage.from_.return_value.get_public_url.return_value = {
        "publicUrl": public_url
    }
    mock_supabase.storage = mock_storage
    
    with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
        response = client.post(
            "/audio/upload",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            data={"patient_id": patient_id, "session_id": session_id},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    # Verify session was updated
    mock_session_table.update.assert_called_once()
    update_call = mock_session_table.update.call_args[0][0]
    assert update_call["audio_url"] == public_url


# -----------------------------
# Test: File Type Validation
# -----------------------------
def test_upload_audio_invalid_file_type(mock_supabase):
    """Test that non-audio files are rejected"""
    invalid_file = BytesIO(b"This is not an audio file")
    
    response = client.post(
        "/audio/upload",
        files={"file": ("test.txt", invalid_file, "text/plain")},
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file type" in data["detail"]
    assert ".txt" in data["detail"]


# -----------------------------
# Test: File Size Validation
# -----------------------------
def test_upload_audio_file_too_large(mock_supabase, large_audio_file):
    """Test that files larger than 50MB are rejected"""
    response = client.post(
        "/audio/upload",
        files={"file": ("large.wav", large_audio_file, "audio/wav")},
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "File too large" in data["detail"]
    assert "50MB" in data["detail"]


# -----------------------------
# Test: Patient ID Validation
# -----------------------------
def test_upload_audio_invalid_patient_id(mock_supabase, sample_audio_file):
    """Test that invalid patient_id returns 404"""
    invalid_patient_id = str(uuid4())
    
    # Mock patient doesn't exist
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.table.return_value = mock_table
    
    response = client.post(
        "/audio/upload",
        files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        data={"patient_id": invalid_patient_id},
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "Patient not found" in data["detail"]
    assert invalid_patient_id in data["detail"]


# -----------------------------
# Test: Session ID Validation
# -----------------------------
def test_upload_audio_invalid_session_id(mock_supabase, sample_audio_file):
    """Test that invalid session_id returns 404"""
    patient_id = str(uuid4())
    invalid_session_id = str(uuid4())
    
    # Mock patient exists
    mock_patient_table = MagicMock()
    mock_patient_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"patient_id": patient_id, "name": "Test Patient"}
    ]
    
    # Mock session doesn't exist
    mock_session_table = MagicMock()
    mock_session_table.select.return_value.eq.return_value.execute.return_value.data = []
    
    def table_side_effect(table_name):
        if table_name == "patients":
            return mock_patient_table
        elif table_name == "sessions":
            return mock_session_table
        return MagicMock()
    
    mock_supabase.table.side_effect = table_side_effect
    
    response = client.post(
        "/audio/upload",
        files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        data={"patient_id": patient_id, "session_id": invalid_session_id},
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "Session not found" in data["detail"]
    assert invalid_session_id in data["detail"]


# -----------------------------
# Test: Supabase Storage Upload Error
# -----------------------------
def test_upload_audio_storage_error(mock_supabase, sample_audio_file):
    """Test handling of Supabase Storage upload errors"""
    # Mock Supabase Storage upload error
    mock_storage = MagicMock()
    mock_storage_error = MagicMock()
    mock_storage_error.message = "Storage quota exceeded"
    mock_storage.from_.return_value.upload.return_value = (
        None,
        mock_storage_error
    )
    mock_supabase.storage = mock_storage
    
    with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
        response = client.post(
            "/audio/upload",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )
    
    assert response.status_code == 500
    data = response.json()
    assert "Failed to upload audio" in data["detail"]


# -----------------------------
# Test: Different Audio Formats
# -----------------------------
@pytest.mark.parametrize("extension,content_type", [
    (".mp3", "audio/mpeg"),
    (".wav", "audio/wav"),
    (".flac", "audio/flac"),
    (".m4a", "audio/mp4"),
    (".ogg", "audio/ogg"),
    (".aac", "audio/aac"),
])
def test_upload_audio_different_formats(mock_supabase, extension, content_type):
    """Test that all supported audio formats are accepted"""
    # Create minimal valid audio file
    audio_data = b'RIFF' + b'\x24\x08\x00\x00' + b'WAVE' + b'fmt ' + b'\x10\x00\x00\x00' + b'\x01\x00' + b'\x01\x00' + b'\x44\xac\x00\x00' + b'\x88\x58\x01\x00' + b'\x02\x00' + b'\x10\x00' + b'data' + b'\x00\x08\x00\x00' + b'\x00' * 100
    audio_file = BytesIO(audio_data)
    
    # Mock Supabase Storage
    mock_storage = MagicMock()
    mock_storage.from_.return_value.upload.return_value = (
        {"path": f"audio/test{extension}"},
        None
    )
    mock_storage.from_.return_value.get_public_url.return_value = {
        "publicUrl": f"https://project.supabase.co/storage/v1/object/public/audio/audio/test{extension}"
    }
    mock_supabase.storage = mock_storage
    
    with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
        response = client.post(
            "/audio/upload",
            files={"file": (f"test{extension}", audio_file, content_type)},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert extension in data["file_path"]


# -----------------------------
# Test: Public URL Generation
# -----------------------------
def test_upload_audio_public_url_generation(mock_supabase, sample_audio_file):
    """Test that public URL is correctly generated"""
    supabase_url = "https://test-project.supabase.co"
    
    # Mock Supabase Storage
    mock_storage = MagicMock()
    file_path = "audio/1731234567890-test.wav"
    mock_storage.from_.return_value.upload.return_value = (
        {"path": file_path},
        None
    )
    # Test different return formats for get_public_url
    mock_storage.from_.return_value.get_public_url.return_value = {
        "publicUrl": f"{supabase_url}/storage/v1/object/public/audio/{file_path}"
    }
    mock_supabase.storage = mock_storage
    
    with patch.dict(os.environ, {"SUPABASE_URL": supabase_url}):
        response = client.post(
            "/audio/upload",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "public_url" in data
    assert data["public_url"].startswith(supabase_url)
    assert "storage/v1/object/public/audio" in data["public_url"]

