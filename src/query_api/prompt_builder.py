"""Build grounded prompts and citation payloads from vector search results."""

from typing import Dict, List, Tuple


SYSTEM_PROMPT = """You are a maintenance operations assistant for an industrial manufacturing site.
Answer only from the provided retrieved context. If the context is insufficient,
say what is missing and recommend the safest next source to check. Include
concise operational guidance, preserve safety warnings, and cite sources using
the bracketed citation IDs provided in the context."""


def build_prompt(question: str, matches: List[Dict]) -> Tuple[str, List[Dict]]:
    """Create the user prompt and structured citations from vector matches.

    Parameters
    ----------
    question:
        The original user question.
    matches:
        Retrieval results returned by S3 Vectors, including metadata and
        distance values.

    Returns
    -------
    tuple[str, list[dict]]
        A prompt for the generation model and a structured citations list for
        the API response.
    """
    context_blocks = []
    citations = []

    for index, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        citation_id = "S%s" % index
        # Prefer the full chunk text when available. ``content_preview`` exists
        # as a fallback if a smaller metadata payload is ever returned.
        chunk_text = metadata.get("chunk_text") or metadata.get("content_preview", "")
        context_blocks.append(
            "[{citation}] {title}\n"
            "equipment_id={equipment_id}; production_line={line}; document_type={doc_type}; distance={distance}\n"
            "{text}".format(
                citation=citation_id,
                title=metadata.get("title", "Untitled source"),
                equipment_id=metadata.get("equipment_id", "unknown"),
                line=metadata.get("production_line", "unknown"),
                doc_type=metadata.get("document_type", "unknown"),
                distance=round(float(match.get("distance", 0.0)), 5),
                text=chunk_text,
            )
        )
        citations.append(
            {
                "citation_id": citation_id,
                "document_id": metadata.get("document_id"),
                "chunk_id": match.get("key"),
                "title": metadata.get("title"),
                "equipment_id": metadata.get("equipment_id"),
                "document_type": metadata.get("document_type"),
                "production_line": metadata.get("production_line"),
                "distance": match.get("distance"),
                "source_uri": metadata.get("source_uri"),
            }
        )

    # The answering model receives both the original question and the retrieved
    # evidence so it can compose a grounded answer instead of inventing facts.
    user_prompt = (
        "Question:\n{question}\n\nRetrieved context:\n{context}\n\n"
        "Answer requirements:\n"
        "- Start with the most likely answer or procedure.\n"
        "- Include safety or escalation notes when present in the context.\n"
        "- Cite every factual claim with citation IDs such as [S1]."
    ).format(question=question, context="\n\n".join(context_blocks))
    return user_prompt, citations
