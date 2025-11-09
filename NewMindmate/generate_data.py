"""
Consistent sample data generator for the MindMeld database.
Ensures all relations are properly linked and patients are represented across all dependent tables.
"""

import random
from datetime import datetime
from faker import Faker
from db.supabase_client import get_supabase

# Initialize Supabase client
supabase = get_supabase()

# Initialize Faker
fake = Faker()

# ------------------------------------------------------
# Helper functions to insert rows with Supabase
# ------------------------------------------------------

def insert_row(table_name, data):
    """Helper to insert and return inserted row."""
    response = supabase.table(table_name).insert(data).execute()
    if hasattr(response, "data") and response.data:
        return response.data[0]
    raise RuntimeError(f"Failed to insert into {table_name}: {response}")


# ------------------------------------------------------
# Entity creation functions
# ------------------------------------------------------

def create_doctor():
    """Creates a doctor record."""
    doctor_data = {
        "name": fake.name(),
        "specialization": random.choice(["Neurologist", "Psychiatrist", "Geriatrician"]),
        "email": fake.unique.email(),
        "phone": fake.phone_number(),
    }
    return insert_row("doctors", doctor_data)


def create_patient():
    """Creates a patient record."""
    patient_data = {
        "name": fake.name(),
        "dob": fake.date_of_birth(minimum_age=40, maximum_age=90).isoformat(),
        "gender": random.choice(["Male", "Female", "Other"]),
    }
    return insert_row("patients", patient_data)


def create_session(patient_id, doctor_id):
    """Creates a new cognitive session linked to a patient and doctor."""
    session_data = {
        "patient_id": patient_id,
        "session_date": fake.date_time_this_year().isoformat(),
        "exercise_type": random.choice(["Cognitive Test", "Memory Recall", "Conversation"]),
        "transcript": fake.text(max_nb_chars=400),
        "created_by": doctor_id,
    }
    return insert_row("sessions", session_data)


def create_memory(patient_id):
    """Creates a realistic memory for a patient."""
    memory_data = {
        "patient_id": patient_id,
        "title": fake.sentence(nb_words=5),
        "description": fake.paragraph(nb_sentences=3),
        "dateapprox": fake.date_between(start_date="-50y", end_date="today").isoformat(),
        "location": fake.city(),
        "emotional_tone": random.choice(["Happy", "Sad", "Nostalgic", "Neutral"]),
        "tags": [fake.word(), fake.word()],
        "significance_level": random.randint(1, 10),
    }
    return insert_row("memories", memory_data)


def create_mri_scan(patient_id, doctor_id, session_id=None):
    """Creates a new MRI scan linked to a patient, optionally a session."""
    mri_scan_data = {
        "patient_id": patient_id,
        "uploaded_by": doctor_id,
        "session_id": session_id,
        "original_filename": fake.file_name(extension="nii.gz"),
        "storage_path": f"mri_scans/{patient_id}/{fake.uuid4()}.nii.gz",
        "file_size_bytes": random.randint(1_000_000, 10_000_000),
        "mime_type": "application/gzip",
        "status": random.choice(["completed", "pending", "failed"]),
        "analysis": {"brain_regions": random.sample(["Hippocampus", "Cortex", "Amygdala"], k=2)},
    }
    return insert_row("mri_scans", mri_scan_data)


def create_doctor_record(doctor_id, patient_id, session_id=None, mri_scan_id=None):
    """Creates a doctor record linked to session and/or MRI scan."""
    record_data = {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "session_id": session_id,
        "mri_scan_id": mri_scan_id,
        "record_type": random.choice(["Session Note", "MRI Analysis", "General Observation"]),
        "summary": fake.sentence(),
        "detailed_notes": fake.paragraph(nb_sentences=4),
        "recommendations": fake.paragraph(nb_sentences=2),
        "metadata": {"source": "auto-generated"},
    }
    return insert_row("doctor_records", record_data)


# ------------------------------------------------------
# Main generator logic
# ------------------------------------------------------

def generate_data(
    num_doctors=3,
    num_patients=5,
    sessions_per_patient=3,
    memories_per_patient=4,
    mri_scans_per_patient=2,
):
    """Generates consistent data across all related tables."""
    print("🔄 Generating consistent sample data...")

    # Step 1: Create doctors
    doctors = [create_doctor() for _ in range(num_doctors)]
    print(f"✅ Created {len(doctors)} doctors.")

    # Step 2: Create patients and their data
    for _ in range(num_patients):
        patient = create_patient()
        patient_id = patient["patient_id"]
        print(f"\n🧠 Created patient: {patient['name']} ({patient_id})")

        primary_doctor = random.choice(doctors)
        doctor_id = primary_doctor["doctor_id"]

        # Sessions (with doctor records)
        sessions = []
        for _ in range(sessions_per_patient):
            session = create_session(patient_id, doctor_id)
            sessions.append(session)
            print(f"  📘 Session created: {session['session_id']}")

            # Each session gets a doctor record
            create_doctor_record(doctor_id, patient_id, session_id=session["session_id"])
            print(f"    ✍️ Doctor record for session")

        # MRI scans, possibly linked to a session
        for _ in range(mri_scans_per_patient):
            linked_session = random.choice(sessions) if sessions else None
            mri = create_mri_scan(patient_id, doctor_id, linked_session["session_id"] if linked_session else None)
            print(f"  🧬 MRI scan created: {mri['id']}")

            # Create doctor record for MRI
            create_doctor_record(doctor_id, patient_id, mri_scan_id=mri["id"])
            print(f"    🩺 Doctor record for MRI scan")

        # Memories
        for _ in range(memories_per_patient):
            create_memory(patient_id)
            print(f"  💭 Memory created")

        # A general doctor record (not linked to session/MRI)
        create_doctor_record(doctor_id, patient_id)
        print(f"  📄 General doctor record added")

    print("\n✅ Sample data generation complete. All entities linked consistently.")


# ------------------------------------------------------
# Run script
# ------------------------------------------------------

if __name__ == "__main__":
    generate_data()
