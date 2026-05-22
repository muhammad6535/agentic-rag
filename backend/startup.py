"""Startup script that waits for dependencies and pulls Ollama models."""

import asyncio
import httpx
import os
import sys
import time


async def wait_for_postgres():
    """Wait for PostgreSQL to accept connections."""
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "raguser")
    password = os.getenv("POSTGRES_PASSWORD", "ragpassword")
    db = os.getenv("POSTGRES_DB", "ragdb")
    print(f"Waiting for PostgreSQL at {host}:{port}...")
    while True:
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host=host, port=port, user=user, database=db, password=password
            )
            await conn.close()
            print("PostgreSQL is ready.")
            return
        except Exception as e:
            print(f"Waiting for DB: {e}")
            time.sleep(2)


async def wait_for_ollama():
    """Wait for Ollama server to be ready."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    print(f"Waiting for Ollama at {base_url}...")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get(f"{base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    print("Ollama is ready.")
                    return
            except Exception:
                pass
            time.sleep(2)


async def pull_ollama_models():
    """Pull required models into Ollama."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    llm_model = os.getenv("LLM_MODEL", "llama3.2:3b")

    async with httpx.AsyncClient(timeout=300) as client:
        for model in [embedding_model, llm_model]:
            print(f"Pulling model: {model}...")
            resp = await client.post(f"{base_url}/api/pull", json={"name": model})
            if resp.status_code == 200:
                print(f"Model {model} pulled successfully.")
            else:
                print(f"Warning: Failed to pull {model}: {resp.text}")


async def warm_llm():
    """Send a trivial request to load the model into Ollama's memory."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    model = os.getenv("LLM_MODEL", "llama3.2:3b")
    print(f"Pre-warming LLM model: {model}...")
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": "hello", "stream": False},
            )
            if resp.status_code == 200:
                print("LLM model is warmed up.")
            else:
                print(f"Warning: model warm-up returned {resp.status_code}")
        except Exception as e:
            print(f"Warning: model warm-up failed: {e}")


async def main():
    await wait_for_postgres()
    await wait_for_ollama()
    await pull_ollama_models()
    await warm_llm()
    print("All dependencies ready. Starting backend...")
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])


if __name__ == "__main__":
    asyncio.run(main())
