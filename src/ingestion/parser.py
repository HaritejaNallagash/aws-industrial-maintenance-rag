"""Parse source maintenance documents into a normalized internal shape."""

import json
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ParsedDocument:
    """A source document with text content and filterable metadata.

    document_id:
        Stable identifier used across chunking, vector keys, and citations.
    title:
        Human-readable document title shown in retrieved citations.
    body:
        Main free-form text that will later be chunked and embedded.
    metadata:
        Structured fields such as equipment ID and document type that can be
        used for filtering during retrieval.
    """

    document_id: str
    title: str
    body: str
    metadata: Dict


def parse_document_bytes(raw_bytes: bytes, source_key: str) -> ParsedDocument:
    """Parse either a raw text document or a legacy JSON source document.

    The preferred raw format is a ``.txt`` file with front matter delimited by
    two ``---`` lines. The parser also accepts the earlier JSON shape so the
    ingestion code remains backward compatible during format transitions.
    """
    if source_key.endswith(".json"):
        return _parse_json_document(raw_bytes, source_key)
    return _parse_text_document(raw_bytes, source_key)


def _parse_json_document(raw_bytes: bytes, source_key: str) -> ParsedDocument:
    """Parse the legacy JSON source shape used by earlier iterations.

    The repository now prefers plain-text documents with front matter, but this
    fallback keeps ingestion tolerant of older files if they still exist.
    """
    payload = json.loads(raw_bytes.decode("utf-8"))
    required = ["document_id", "title", "body", "metadata"]
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError("Document %s is missing required fields: %s" % (source_key, missing))

    metadata = dict(payload["metadata"])
    metadata["source_key"] = source_key
    metadata.setdefault("source_system", "industrial-maintenance-seed")

    return ParsedDocument(
        document_id=str(payload["document_id"]),
        title=str(payload["title"]),
        body=str(payload["body"]),
        metadata=metadata,
    )


def _parse_text_document(raw_bytes: bytes, source_key: str) -> ParsedDocument:
    """Parse a text source document with a simple front-matter block.

    Expected layout
    ---------------
    ---
    key: value
    key: value
    ---
    free-form body text

    Everything before the second ``---`` becomes metadata. Everything after it
    becomes the searchable body text.
    """
    text = raw_bytes.decode("utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ValueError("Text document %s must start with a front-matter delimiter" % source_key)

    header = {}
    body_start_index = None
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body_start_index = index + 1
            break
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError("Malformed front-matter line in %s: %s" % (source_key, line))
        key, value = line.split(":", 1)
        header[key.strip()] = value.strip()

    if body_start_index is None:
        raise ValueError("Text document %s is missing the closing front-matter delimiter" % source_key)

    body = "\n".join(lines[body_start_index:]).strip()
    required = [
        "document_id",
        "title",
        "site_id",
        "production_line",
        "equipment_id",
        "document_type",
        "severity",
        "effective_date",
        "source_system",
    ]
    missing = [field for field in required if not header.get(field)]
    if missing:
        raise ValueError("Document %s is missing required front-matter fields: %s" % (source_key, missing))
    if not body:
        raise ValueError("Text document %s has an empty body" % source_key)

    metadata = {
        "site_id": header["site_id"],
        "production_line": header["production_line"],
        "equipment_id": header["equipment_id"],
        "document_type": header["document_type"],
        "severity": header["severity"],
        "effective_date": header["effective_date"],
        "source_system": header["source_system"],
        "source_key": source_key,
    }

    return ParsedDocument(
        document_id=header["document_id"],
        title=header["title"],
        body=body,
        metadata=metadata,
    )
