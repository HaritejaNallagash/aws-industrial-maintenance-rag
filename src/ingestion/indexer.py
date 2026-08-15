"""Index parsed maintenance documents into S3, DynamoDB, and S3 Vectors."""

import json
import time
from typing import Dict, Iterable, List, Optional

import boto3

from src.common.bedrock_client import BedrockModelClient
from src.common.json_utils import dumps
from src.common.s3_vectors_client import S3VectorsStore
from src.ingestion.chunker import (
    DocumentChunk,
    chunk_document,
    chunks_to_vector_records,
)
from src.ingestion.parser import ParsedDocument


class MaintenanceDocumentIndexer:
    """Coordinates chunk persistence, metadata lineage, and vector writes.

    This class is the core of the ingestion path. It takes one normalized
    ``ParsedDocument`` and turns it into everything needed for retrieval:

    - chunk JSON files for inspection/debugging
    - optional DynamoDB lineage rows
    - vector records stored in S3 Vectors
    """

    def __init__(
        self,
        processed_bucket: str,
        document_table_name: Optional[str],
        vector_store: S3VectorsStore,
        bedrock: BedrockModelClient,
        vector_dimensions: int,
    ):
        """Prepare the AWS clients used during indexing.

        Parameters
        ----------
        processed_bucket:
            Bucket where chunk-level JSON output is written.

        document_table_name:
            Optional DynamoDB table for document/chunk lineage. When omitted,
            ingestion still works and simply skips the metadata write.

        vector_store:
            Wrapper around the S3 Vectors API.

        bedrock:
            Embedding client used to turn chunk text into vectors.

        vector_dimensions:
            Number of coordinates expected in each embedding.
        """
        self.processed_bucket = processed_bucket
        self.document_table = None

        if document_table_name:
            self.document_table = boto3.resource(
                "dynamodb"
            ).Table(document_table_name)

        self.s3 = boto3.client("s3")
        self.vector_store = vector_store
        self.bedrock = bedrock
        self.vector_dimensions = vector_dimensions

    def index_document(
        self,
        document: ParsedDocument,
    ) -> Dict:
        """Chunk one document and write all retrieval artifacts.

        The steps happen in this order:

        1. split the document into chunk-sized text blocks
        2. embed each chunk
        3. write vectors to S3 Vectors
        4. write processed chunk JSON to S3
        5. optionally write metadata rows to DynamoDB
        """
        chunks = chunk_document(document)

        embeddings = []

        for chunk in chunks:
            embedding = self.bedrock.embed_text(
                _embedding_text(chunk),
                self.vector_dimensions,
            )

            embeddings.append(embedding)

            # Small delay between Bedrock embedding requests to reduce
            # the chance of hitting the Bedrock request-rate limit.
            time.sleep(1.0)

        vector_records = chunks_to_vector_records(
            chunks,
            embeddings,
        )

        self.vector_store.put_vectors(vector_records)

        self._write_processed_chunks(chunks)

        self._write_metadata_records(
            document,
            chunks,
        )

        return {
            "document_id": document.document_id,
            "chunk_count": len(chunks),
            "vector_count": len(vector_records),
        }

    def _write_processed_chunks(
        self,
        chunks: Iterable[DocumentChunk],
    ) -> None:
        """Persist human-readable chunk JSON files to the processed S3 bucket."""
        for chunk in chunks:
            key = (
                "chunks/document_id=%s/%s.json"
                % (
                    chunk.document_id,
                    chunk.chunk_id,
                )
            )

            payload = {
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }

            self.s3.put_object(
                Bucket=self.processed_bucket,
                Key=key,
                Body=dumps(payload).encode("utf-8"),
                ContentType="application/json",
            )

    def _write_metadata_records(
        self,
        document: ParsedDocument,
        chunks: List[DocumentChunk],
    ) -> None:
        """Persist optional lineage rows for later inspection or auditing."""
        if self.document_table is None:
            return

        now_epoch = int(time.time())

        with self.document_table.batch_writer() as batch:
            for chunk in chunks:
                batch.put_item(
                    Item={
                        "document_id": document.document_id,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.chunk_index,
                        "title": chunk.title,
                        "source_key": document.metadata.get(
                            "source_key",
                            "",
                        ),
                        "document_type": document.metadata.get(
                            "document_type",
                            "",
                        ),
                        "equipment_id": document.metadata.get(
                            "equipment_id",
                            "",
                        ),
                        "production_line": document.metadata.get(
                            "production_line",
                            "",
                        ),
                        "site_id": document.metadata.get(
                            "site_id",
                            "",
                        ),
                        "indexed_at_epoch": now_epoch,
                        "metadata_json": json.dumps(
                            chunk.metadata,
                            sort_keys=True,
                        ),
                    }
                )


def _embedding_text(
    chunk: DocumentChunk,
) -> str:
    """Include the title and core metadata in the embedding input.

    The embedding model sees more than the raw chunk text. Including a few key
    metadata fields improves retrieval quality because the vector captures both
    the content and high-level context such as equipment and document type.
    """
    metadata = chunk.metadata

    prefix = (
        "Title: {title}\n"
        "Equipment: {equipment}\n"
        "Document type: {document_type}\n"
        "Line: {line}\n\n"
    ).format(
        title=chunk.title,
        equipment=metadata.get(
            "equipment_id",
            "unknown",
        ),
        document_type=metadata.get(
            "document_type",
            "unknown",
        ),
        line=metadata.get(
            "production_line",
            "unknown",
        ),
    )

    return prefix + chunk.text