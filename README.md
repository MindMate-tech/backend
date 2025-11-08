# MindMate API

The MindMate API is a FastAPI-based backend for a healthcare application focused on cognitive health. It provides services for managing patient data, therapy sessions, and analyzing session audio to extract meaningful cognitive insights.

## Features

*   **Patient Management:** Create, retrieve, and manage patient records.
*   **Session Tracking:** Record and store details of therapy sessions, including transcripts and doctor's notes.
*   **Cognitive Analysis:** Asynchronously analyze session audio to extract cognitive metrics.
*   **Data Modeling:** Rich data models for patients, sessions, memories, and cognitive test scores.
*   **Database Integration:** Uses Supabase for data persistence.

## API Endpoints

Here are the main endpoints provided by the API:

*   `GET /health`: Health check endpoint.
*   `GET /patients`: List all patients.
*   `POST /patients`: Create a new patient.
*   `POST /sessions/analyze/{session_id}`: Trigger a background task to analyze a session.
*   _(Other session-related endpoints are available in the `sessions` router)_

## Getting Started

### Prerequisites

*   Python 3.11+
*   [uv](https://github.com/astral-sh/uv) for dependency management.
*   A Supabase project for the database.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/mindmate-api.git
    cd mindmate-api
    ```

2.  **Create a `.env` file:**
    Create a `.env` file in the root of the project and add your Supabase credentials:
    ```
    SUPABASE_URL="your-supabase-url"
    SUPABASE_KEY="your-supabase-key"
    ```

3.  **Install dependencies:**
    ```bash
    uv sync
    ```

### Running the Application

To start the FastAPI server, run the following command:

```bash
uv run uvicorn NewMindmate.main:app --reload
```

The API will be available at `http://1227.0.0.1:8000`.

## Running Tests

To run the test suite, use the following command:

```bash
uv run pytest
```