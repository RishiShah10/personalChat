"""Chunking, embedding, and Chroma vector store management."""

import os
from pathlib import Path
from typing import List

import chromadb
import tiktoken
from openai import OpenAI

# OpenAI embedding model — 1536-dim vectors, cheap ($0.00002 / 1K tokens)
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 200    # tokens per chunk
CHUNK_OVERLAP = 50  # tokens of overlap between chunks to avoid losing context at boundaries

_encoder = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str) -> List[str]:
    """Split text into token-bounded chunks with overlap."""
    tokens = _encoder.encode(text)

    # Short messages — no chunking needed
    if len(tokens) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_encoder.decode(chunk_tokens))
        start += CHUNK_SIZE - CHUNK_OVERLAP  # slide forward with overlap

    return chunks


def embed(text: str, api_key: str = None) -> List[float]:
    """Embed a single text string via OpenAI."""
    client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


def init_chroma(directory: Path) -> chromadb.Collection:
    """Open or create on-disk Chroma collection for chat chunks."""
    chroma_path = directory / "chroma"
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    # get_or_create so restarts don't wipe existing embeddings
    return client.get_or_create_collection(
        name="chat_chunks",
        metadata={"hnsw:space": "cosine"},  # use cosine similarity
    )
