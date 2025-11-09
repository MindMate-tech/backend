from fastapi import FastAPI, HTTPException, Header
import requests
import os

app = FastAPI(title="Beyond Presence Call Message Retriever")

BEYOND_PRESENCE_BASE_URL = "https://api.beyondpresence.ai/v1"


@app.get("/calls/{call_id}/messages")
def get_call_messages(call_id: str, x_api_key: str = Header(default=None)):
    """
    Retrieve all prior messages from a Beyond Presence call.

    Args:
        call_id (str): The unique call ID.
        x_api_key (str): Your Beyond Presence API key (header or env variable).

    Returns:
        JSON list of messages with fields: message, sent_at, sender
    """
    api_key = x_api_key or os.getenv("BEY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Beyond Presence API key.")

    url = f"{BEYOND_PRESENCE_BASE_URL}/calls/{call_id}/messages"
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        messages = response.json()
        return {"call_id": call_id, "messages": messages}

    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=response.status_code, detail=str(e))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
