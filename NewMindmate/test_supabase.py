from db.supabase_client import get_supabase

supabase = get_supabase()

# Fetch patients
patients = supabase.table("patients").select("*").execute()
print("Patients:", patients.data)

# Insert a test patient
response = supabase.table("patients").insert({
    "name": "John Doe",
    "dob": "1980-05-12",
    "gender": "male"
}).execute()

print("Inserted:", response.data)
