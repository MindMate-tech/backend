# Cognitive API Integration - Testing Guide

## Overview

This branch (`feature/cognitive-api-integration`) adds **real AI-powered analysis** to the MindMate backend by integrating with the deployed Cognitive API at:

```
https://mindmate-cognitive-api.onrender.com
```

## What Changed

### New Files

1. **`NewMindmate/services/cognitive_api_client.py`**
   - HTTP client that calls the Cognitive API
   - Functions: `analyze_session_with_ai()`, `get_patient_dashboard()`, `health_check()`

2. **`NewMindmate/routes/cognitive_routes.py`**
   - NEW endpoints prefixed with `/cognitive`
   - Does NOT modify existing production routes

3. **`NewMindmate/services/__init__.py`**
   - Makes services a proper Python module

### Modified Files

1. **`NewMindmate/main.py`**
   - Added import: `from NewMindmate.routes.cognitive_routes import router as cognitive_router`
   - Added: `app.include_router(cognitive_router)`

2. **`pyproject.toml`**
   - Added dependency: `httpx>=0.28.1`

---

## New Endpoints

### 1. Health Check
```bash
GET /cognitive/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Cognitive API",
  "url": "https://mindmate-cognitive-api.onrender.com"
}
```

---

### 2. Analyze Session (Real AI)
```bash
POST /cognitive/sessions/{session_id}/analyze
```

**What it does:**
- Fetches session and patient data from Supabase
- Calls Cognitive API for real AI analysis (Dedalus agents)
- Stores results back in Supabase
- Stores extracted memories in ChromaDB
- Returns immediately, analysis runs in background

**Response:**
```json
{
  "status": "Analysis started in background",
  "session_id": "uuid-here",
  "message": "Check back in 60-120 seconds for results"
}
```

**Console Output:**
```
🧠 Starting Cognitive API analysis for session {session_id}
✅ Analysis complete! Overall score: 0.68
💾 Stored analysis in Supabase
📝 Stored memory: Trip to Paris
📝 Stored memory: Grandma's birthday
🎉 Analysis pipeline complete for session {session_id}
```

---

### 3. Get Patient Dashboard (Real Data)
```bash
GET /cognitive/patients/{patient_id}/analytics
```

**What it does:**
- Fetches patient and sessions from Supabase
- Calls Cognitive API to generate dashboard
- Returns REAL brain regions from MRI CSV
- Returns REAL memory metrics time series

**Response:**
```json
{
  "patientId": "uuid-here",
  "patientName": "John Doe",
  "lastUpdated": "2025-11-08T12:00:00Z",
  "brainRegions": {
    "hippocampus": 0.75,        // REAL from MRI CSV
    "prefrontalCortex": 0.80,   // REAL calculated
    "temporalLobe": 0.78,       // REAL from MRI CSV
    "parietalLobe": 0.82,       // REAL calculated
    "amygdala": 0.88,           // REAL calculated
    "cerebellum": 0.83          // REAL calculated
  },
  "memoryMetrics": {
    "shortTermRecall": [
      {"timestamp": "2025-11-01T10:00:00Z", "score": 0.65},
      {"timestamp": "2025-11-02T10:00:00Z", "score": 0.68}
    ],
    "longTermRecall": [...],    // REAL time series
    "semanticMemory": [...],     // REAL time series
    "episodicMemory": [...],     // REAL time series
    "workingMemory": [...]       // REAL time series
  },
  "recentSessions": [...],
  "overallCognitiveScore": 0.68,
  "memoryRetentionRate": 0.65
}
```

---

### 4. Frontend Alias Endpoint
```bash
GET /cognitive/patients/{patient_id}/cognitive-data
```

**What it does:**
- Alias for `/analytics` endpoint
- Fixes frontend endpoint mismatch
- Frontend calls `/cognitive-data`, this endpoint provides it

---

## Old vs New Endpoints

### OLD (Still in Production - UNCHANGED)
```bash
POST /sessions/analyze/{session_id}
# ❌ Stub - returns mock response, does nothing

GET /patients/{patient_id}/analytics
# ❌ Does NOT exist in production main.py
```

### NEW (On This Branch - REAL AI)
```bash
POST /cognitive/sessions/{session_id}/analyze
# ✅ Calls Cognitive API, real analysis

GET /cognitive/patients/{patient_id}/analytics
# ✅ Calls Cognitive API, returns real data

GET /cognitive/patients/{patient_id}/cognitive-data
# ✅ Alias for frontend compatibility
```

---

## Local Testing

### Step 1: Install Dependencies

```bash
cd /home/lucas/mindmate-backend

# If using uv
uv sync

# If using pip
pip install -e .
```

### Step 2: Set Environment Variables

Make sure you have:
```bash
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### Step 3: Run the Server

```bash
cd /home/lucas/mindmate-backend
uvicorn NewMindmate.main:app --reload --port 8000
```

### Step 4: Test Health Check

```bash
curl http://localhost:8000/health
# Should return: {"status": "ok", "message": "MindMate API running"}

curl http://localhost:8000/cognitive/health
# Should return: {"status": "healthy", "service": "Cognitive API", ...}
```

### Step 5: Test Session Analysis

First, create a test session:
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "your-patient-uuid",
    "transcript": "Patient: I remember going to Paris last summer with my wife...",
    "exercise_type": "memory_recall",
    "session_date": "2025-11-08T10:00:00Z"
  }'
```

Then trigger analysis:
```bash
curl -X POST http://localhost:8000/cognitive/sessions/{session_id}/analyze
```

Wait 60-120 seconds, then check the session in Supabase:
```sql
SELECT ai_extracted_data, cognitive_test_scores, overall_score
FROM sessions
WHERE session_id = 'your-session-id';
```

### Step 6: Test Patient Dashboard

```bash
curl http://localhost:8000/cognitive/patients/{patient_id}/analytics
```

This should return real brain regions and memory metrics!

---

## Integration with Frontend

### Current Issue
Frontend calls:
```typescript
api.patients.getCognitiveData(patientId)
// → GET /patients/{id}/cognitive-data
```

But backend (on main branch) doesn't have this endpoint.

### Solution on This Branch
The NEW endpoint provides it:
```
GET /cognitive/patients/{patient_id}/cognitive-data
```

### Frontend Update Required
Update `doctor-frontend/lib/api/client.ts`:

```typescript
async getCognitiveData(patientId: string): Promise<BackendPatientData> {
  const response = await fetchWithTimeout(
    `${API_URL}/cognitive/patients/${patientId}/cognitive-data`  // ✅ Now with /cognitive prefix
  );
  return handleResponse<BackendPatientData>(response);
}
```

---

## Deployment to Render

### Option 1: Test on Separate Service

1. Create a NEW web service on Render (don't touch production!)
2. Connect to this branch: `feature/cognitive-api-integration`
3. Build command: `pip install -e .`
4. Start command: `uvicorn NewMindmate.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

### Option 2: Merge to Main (After Testing)

Once you've verified locally:

```bash
cd /home/lucas/mindmate-backend

# Switch to main
git checkout main

# Merge feature branch
git merge feature/cognitive-api-integration

# Push to trigger Render deployment
git push origin main
```

---

## Verification Checklist

- [ ] Install dependencies (`uv sync`)
- [ ] Run server locally (`uvicorn NewMindmate.main:app --reload`)
- [ ] Test health check (`GET /health`)
- [ ] Test cognitive health (`GET /cognitive/health`)
- [ ] Create test session with transcript
- [ ] Trigger analysis (`POST /cognitive/sessions/{id}/analyze`)
- [ ] Wait 90 seconds
- [ ] Check Supabase for `ai_extracted_data`
- [ ] Test dashboard (`GET /cognitive/patients/{id}/analytics`)
- [ ] Verify brain regions are numbers (not hardcoded 82.5, 77.3)
- [ ] Verify memory metrics have time series data
- [ ] Update frontend to use `/cognitive/patients/{id}/cognitive-data`
- [ ] Deploy to Render (new service or merge to main)

---

## Troubleshooting

### Issue: "No module named 'httpx'"
**Solution:** Run `uv sync` or `pip install httpx`

### Issue: "Cannot import cognitive_routes"
**Solution:** Make sure you're running from the repo root, not inside NewMindmate/

### Issue: Cognitive API timeout
**Solution:** Render free tier sleeps after inactivity. First request takes 60s to wake up.

### Issue: "Session not found"
**Solution:** Make sure the session exists in Supabase first

### Issue: Frontend still gets 404
**Solution:** Make sure frontend is calling the NEW endpoint: `/cognitive/patients/{id}/cognitive-data`

---

## Next Steps

1. **Test locally** using the steps above
2. **Update frontend** to call `/cognitive/*` endpoints
3. **Deploy to Render** (new service or merge to main)
4. **Verify end-to-end** flow:
   - Video call → Session created → Analysis triggered → Dashboard shows real data

---

## Summary

This integration replaces:
- ❌ Hardcoded brain regions (82.5, 77.3, etc.)
- ❌ Empty memory metrics arrays
- ❌ Stub analysis endpoint

With:
- ✅ Real brain regions from MRI CSV files
- ✅ Real memory metrics time series (5 types)
- ✅ Real AI-powered analysis using Dedalus agents
- ✅ Complete analytics pipeline

**Total time to deploy:** ~5-10 minutes after local testing
**Breaking changes:** NONE - all new routes are under `/cognitive` prefix
