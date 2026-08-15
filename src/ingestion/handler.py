"""AWS Lambda entrypoint for the ingestion workflow."""

import logging
import os
from typing import Dict, Iterable, List
from urllib.parse import unquote_plus

import boto3

from src.common.bedrock_client import BedrockModelClient
from src.common.config import IngestionConfig
from src.common.s3_vectors_client import S3VectorsStore
from src.ingestion.indexer import MaintenanceDocumentIndexer
from src.ingestion.parser import parse_document_bytes

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def lambda_handler(event: Dict, context) -> Dict:
    """Index one object, an S3-style event, or an entire S3 prefix.

    Supported inputs include:

    - a direct ``{"bucket": "...", "key": "..."}`` payload
    - a direct ``{"bucket": "...", "prefix": "..."}`` payload
    - an S3 event with ``Records``
    - an EventBridge object-created event shape

    Returning a structured summary makes Lambda console tests easier to inspect.
    """
    config = IngestionConfig.from_env()
    s3 = boto3.client("s3")
    indexer = MaintenanceDocumentIndexer(
        processed_bucket=config.processed_bucket,
        document_table_name=config.document_table,
        vector_store=S3VectorsStore(config.vector.bucket_name, config.vector.index_name),
        bedrock=BedrockModelClient(config.bedrock.embedding_model_id),
        vector_dimensions=config.vector.dimensions,
    )

    objects = list(_resolve_objects(event, config.raw_bucket, s3))
    logger.info("Resolved %s object(s) for ingestion", len(objects))

    results = []
    for bucket, key in objects:
        # The project primarily uses ``.txt`` source files, but ``.json`` is
        # still accepted for backward compatibility with older sample data.
        if not (key.endswith(".txt") or key.endswith(".json")):
            logger.info("Skipping unsupported object type s3://%s/%s", bucket, key)
            continue
        response = s3.get_object(Bucket=bucket, Key=key)
        parsed = parse_document_bytes(response["Body"].read(), key)
        results.append(indexer.index_document(parsed))

    return {"status": "indexed", "objects_seen": len(objects), "documents": results}


def _resolve_objects(event: Dict, default_bucket: str, s3_client) -> Iterable:
    """Normalize the supported trigger shapes into ``(bucket, key)`` tuples.

    The ingestion Lambda is intentionally flexible so you can:

    - test one object directly
    - reindex a whole prefix manually
    - later connect it to event-driven triggers without changing the code
    """
    if "Records" in event:
        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])
            yield bucket, key
        return

    if event.get("detail", {}).get("bucket") and event.get("detail", {}).get("object"):
        yield event["detail"]["bucket"]["name"], unquote_plus(event["detail"]["object"]["key"])
        return

    if event.get("bucket") and event.get("key"):
        yield event["bucket"], unquote_plus(event["key"])
        return

    if event.get("prefix"):
        bucket = event.get("bucket", default_bucket)
        continuation_token = None
        while True:
            # Prefix reindexing may span multiple paginated S3 responses.
            request = {"Bucket": bucket, "Prefix": event["prefix"]}
            if continuation_token:
                request["ContinuationToken"] = continuation_token
            response = s3_client.list_objects_v2(**request)
            for item in response.get("Contents", []):
                yield bucket, item["Key"]
            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
        return

    raise ValueError("Unsupported ingestion event shape: %s" % sorted(event.keys()))
