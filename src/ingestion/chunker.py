"""Chunk maintenance documents into retrieval-sized text blocks."""

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List

from src.ingestion.parser import ParsedDocument


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of source content ready for embedding.

    document_id:
        Parent document identifier.
    chunk_id:
        Stable unique identifier for this chunk. This becomes the vector key.
    chunk_index:
        Sequential position of the chunk within the document.
    title:
        Original document title copied for citation readability.
    text:
        The actual chunk body sent to the embedding model.
    metadata:
        Filterable and citation-friendly fields stored alongside the vector.
    """

    document_id: str
    chunk_id: str
    chunk_index: int
    title: str
    text: str
    metadata: Dict


def chunk_document(
    document: ParsedDocument,
    max_chars: int = 1200,
    overlap_chars: int = 180,
) -> List[DocumentChunk]:
    """Split a document into overlapping paragraph-aware chunks.

    The function keeps paragraphs intact where possible because procedures and
    incident reports lose meaning when split mid-step. A small character overlap
    preserves context across boundaries without creating very large embeddings.
    """
    # Documents are split on blank lines first so procedures and incident
    # reports stay readable. The chunker tries not to cut through a paragraph
    # unless size forces it to start a new chunk.
    paragraphs = [p.strip() for p in document.body.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = (current + "\n\n" + paragraph).strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        # Carry a small tail from the previous chunk into the next one so the
        # retrieval system preserves context around boundaries.
        current = _with_overlap(chunks[-1] if chunks else "", paragraph, overlap_chars)

    if current:
        chunks.append(current)

    return [
        DocumentChunk(
            document_id=document.document_id,
            chunk_id=_chunk_id(document.document_id, index, text),
            chunk_index=index,
            title=document.title,
            text=text,
            metadata=_chunk_metadata(document, index, text),
        )
        for index, text in enumerate(chunks)
    ]


def chunks_to_vector_records(chunks: Iterable[DocumentChunk], embeddings: Iterable[List[float]]) -> List[Dict]:
    """Combine chunks and embeddings into the S3 Vectors PutVectors shape.

    The embedding model returns only floating-point vectors. This function
    merges those vectors back together with each chunk's ID and metadata so the
    vector store can later return useful citations and filters.
    """
    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append(
            {
                "key": chunk.chunk_id,
                "data": {"float32": [float(value) for value in embedding]},
                "metadata": chunk.metadata,
            }
        )
    return records


def _with_overlap(previous: str, next_paragraph: str, overlap_chars: int) -> str:
    """Start a new chunk while copying a short tail from the previous chunk."""
    overlap = previous[-overlap_chars:].strip()
    if overlap:
        return (overlap + "\n\n" + next_paragraph).strip()
    return next_paragraph


def _chunk_id(document_id: str, chunk_index: int, text: str) -> str:
    """Build a stable chunk key using the document ID, position, and text hash."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return "%s-%04d-%s" % (document_id, chunk_index, digest)


def _chunk_metadata(document: ParsedDocument, chunk_index: int, text: str) -> Dict:
    """Prepare metadata stored with each vector and processed chunk file."""
    metadata = dict(document.metadata)
    metadata.update(
        {
            "document_id": document.document_id,
            "chunk_index": chunk_index,
            "title": document.title,
            "chunk_text": text,
            "content_preview": text[:240],
            "source_uri": "s3://%s" % document.metadata.get("source_key", "unknown"),
        }
    )
    return metadata
