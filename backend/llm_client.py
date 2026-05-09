import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client: genai.Client | None = None

GEN_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "models/gemini-embedding-001"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def generate(prompt: str) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model=GEN_MODEL,
        contents=prompt,
    )
    return response.text


def embed(text: str) -> list[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=[text],
    )
    return result.embeddings[0].values
