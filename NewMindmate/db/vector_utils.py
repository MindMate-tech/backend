import numpy as np
from supabase import Client
from typing import List
from uuid import uuid4

VECTOR_DIM = 1536  # Must match your embeddings model

def store_memory_embedding(supabase: Client, patient_id: str, title: str, description: str, embedding: List[float], dateapprox=None, location=None, emotional_tone=None, tags=None, significance_level=1):
    """Store a memory with embedding in Supabase"""
    memory_id = str(uuid4())
    payload = {
        "memory_id": memory_id,
        "patient_id": patient_id,
        "title": title,
        "description": description,
        "dateapprox": dateapprox,
        "location": location,
        "emotional_tone": emotional_tone,
        "tags": tags or [],
        "significance_level": significance_level,
        "embedding": embedding,
    }
    result = supabase.table("memories").insert(payload).execute()
    if not result.data:
        raise RuntimeError(f"Failed to insert memory embedding: {result}")
    return memory_id

def search_similar_memories(supabase: Client, patient_id: str, query_embedding: List[float], limit=5):
    """
    Perform vector similarity search in Supabase pgvector
    """
    # Supabase pgvector query: cosine similarity
    sql = f"""
    SELECT *,
           1 - (embedding <#> '{query_embedding}') AS similarity
    FROM memories
    WHERE patient_id = '{patient_id}'
    ORDER BY embedding <#> '{query_embedding}' ASC
    LIMIT {limit};
    """
    res = supabase.rpc("execute_sql", {"query": sql}).execute()  # or use direct SQL API
    if not res.data:
        return []
    return res.data
