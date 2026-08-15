"""AWS Lambda entrypoint for RAG queries."""

import logging
import os
import time
import uuid
from typing import Dict, Optional

import boto3

from src.common.bedrock_client import BedrockModelClient
from src.common.config import QueryConfig
from src.common.json_utils import dumps, loads_body
from src.common.s3_vectors_client import S3VectorsStore
from src.query_api.prompt_builder import SYSTEM_PROMPT, build_prompt

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def lambda_handler(event: Dict, context) -> Dict:
    """Answer one maintenance question using Bedrock and S3 Vectors.

    High-level flow
    ---------------
    1. parse the incoming request
    2. validate the question
    3. embed the question into a vector
    4. retrieve the nearest document chunks from S3 Vectors
    5. build a grounded prompt from those chunks
    6. ask the generation model for a final answer
    7. return the answer plus machine-readable citations
    """
    config = QueryConfig.from_env()
    request = loads_body(event)
    question = str(request.get("question", "")).strip()
    if not question:
        return _response(400, {"message": "question is required"})

    top_k = int(request.get("top_k", 5))
    top_k = max(1, min(top_k, 10))
    metadata_filter = _build_vector_filter(request.get("filters", {}))

    bedrock = BedrockModelClient(
        embedding_model_id=config.bedrock.embedding_model_id,
        generation_model_id=config.bedrock.generation_model_id,
    )
    # The question is embedded into the same vector space used for stored
    # chunks, which lets the vector index find semantically similar content.
    query_embedding = bedrock.embed_text(question, config.vector.dimensions)

    vector_store = S3VectorsStore(config.vector.bucket_name, config.vector.index_name)
    matches = vector_store.query(query_embedding, top_k=top_k, metadata_filter=metadata_filter)
    if not matches:
        answer = "I could not find matching maintenance knowledge for that question."
        payload = {"answer": answer, "citations": [], "matches": []}
        _audit_query(config.query_audit_table, question, payload)
        return _response(200, payload)

    user_prompt, citations = build_prompt(question, matches)
    answer = bedrock.generate_answer(SYSTEM_PROMPT, user_prompt)
    payload = {
        "answer": answer,
        "citations": citations,
        "retrieval": {
            "top_k": top_k,
            "filter_applied": metadata_filter or {},
            "match_count": len(matches),
        },
    }
    _audit_query(config.query_audit_table, question, payload)
    return _response(200, payload)


def _build_vector_filter(filters: Dict) -> Dict:
    """Convert API filters into the S3 Vectors metadata filter expression.

    S3 Vectors supports metadata filtering. The supported shape can evolve, so
    the code keeps a small adapter here rather than scattering filter syntax
    across the handler.
    """
    if not isinstance(filters, dict) or not filters:
        return {}
    and_filters = []
    for key, value in filters.items():
        if value in (None, "", []):
            continue
        # Each UI filter becomes an equality check against vector metadata.
        and_filters.append({key: {"$eq": value}})
    if not and_filters:
        return {}
    if len(and_filters) == 1:
        return and_filters[0]
    return {"$and": and_filters}


def _audit_query(table_name: Optional[str], question: str, payload: Dict) -> None:
    """Persist an audit record with a 30-day TTL.

    The feature is optional. If no audit table is configured, the rest of the
    query path still succeeds and simply skips this bookkeeping step.
    """
    if not table_name:
        return
    table = boto3.resource("dynamodb").Table(table_name)
    now = int(time.time())
    table.put_item(
        Item={
            "query_id": str(uuid.uuid4()),
            "question": question,
            "created_at_epoch": now,
            "expires_at_epoch": now + 30 * 24 * 60 * 60,
            "answer_preview": payload.get("answer", "")[:500],
            "citation_count": len(payload.get("citations", [])),
        }
    )


def _response(status_code: int, body: Dict) -> Dict:
    """Wrap the response in the Lambda proxy shape expected by the frontend."""
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
        },
        "body": dumps(body),
    }
