"""Environment-backed configuration helpers.

Lambda functions receive deployment-specific values through environment
variables. Keeping the parsing in one module makes runtime code easier to
follow and keeps missing configuration failures explicit.
"""

import os
from dataclasses import dataclass
from typing import Optional


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error.

    Parameters
    ----------
    name:
        Environment variable name to read from the Lambda runtime.

    Returns
    -------
    str
        The non-empty environment variable value.

    Raises
    ------
    RuntimeError
        Raised when the variable is missing so deployment/configuration
        mistakes fail fast with a readable message.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("Missing required environment variable: %s" % name)
    return value


def optional_env(name: str) -> Optional[str]:
    """Return an optional environment variable or ``None``.

    This helper keeps the rest of the code from having to repeatedly check
    whether Lambda environment variables are present before using them.
    """
    value = os.environ.get(name)
    if value in (None, ""):
        return None
    return value


def optional_int(name: str, default: int) -> int:
    """Parse an optional integer environment variable.

    Parameters
    ----------
    name:
        Environment variable name to inspect.
    default:
        Fallback integer to use when the variable is not set.
    """
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    return int(value)


@dataclass(frozen=True)
class VectorConfig:
    """Configuration needed to read and write S3 Vectors.

    Attributes
    ----------
    bucket_name:
        Name of the S3 Vector bucket that stores semantic vectors.
    index_name:
        Name of the searchable index within the vector bucket.
    dimensions:
        Length of every embedding vector. The index, ingestion path, and query
        path must all agree on this number.
    """

    bucket_name: str
    index_name: str
    dimensions: int

    @classmethod
    def from_env(cls) -> "VectorConfig":
        """Build vector configuration from Lambda environment variables."""
        return cls(
            bucket_name=require_env("VECTOR_BUCKET_NAME"),
            index_name=require_env("VECTOR_INDEX_NAME"),
            dimensions=optional_int("VECTOR_DIMENSIONS", 1024),
        )


@dataclass(frozen=True)
class BedrockConfig:
    """Configuration for Bedrock embedding and generation models.

    The ingestion Lambda only needs an embedding model, while the query Lambda
    needs both an embedding model and a text generation model.
    """

    embedding_model_id: str
    generation_model_id: Optional[str] = None

    @classmethod
    def for_ingestion(cls) -> "BedrockConfig":
        """Return the subset of model config needed during indexing."""
        return cls(embedding_model_id=require_env("EMBEDDING_MODEL_ID"))

    @classmethod
    def for_query(cls) -> "BedrockConfig":
        """Return the model config needed when answering user questions."""
        return cls(
            embedding_model_id=require_env("EMBEDDING_MODEL_ID"),
            generation_model_id=require_env("GENERATION_MODEL_ID"),
        )


@dataclass(frozen=True)
class IngestionConfig:
    """Storage and model settings required by the ingestion Lambda.

    raw_bucket:
        Bucket containing uploaded source maintenance documents.
    processed_bucket:
        Bucket that receives normalized chunk JSON output.
    document_table:
        Optional DynamoDB table for lineage/metadata records.
    vector:
        Nested vector-store settings used for embeddings and search writes.
    bedrock:
        Embedding-model settings used during indexing.
    """

    raw_bucket: str
    processed_bucket: str
    document_table: Optional[str]
    vector: VectorConfig
    bedrock: BedrockConfig

    @classmethod
    def from_env(cls) -> "IngestionConfig":
        """Build ingestion configuration from Lambda environment variables."""
        return cls(
            raw_bucket=require_env("RAW_BUCKET"),
            processed_bucket=require_env("PROCESSED_BUCKET"),
            document_table=optional_env("DOCUMENT_TABLE"),
            vector=VectorConfig.from_env(),
            bedrock=BedrockConfig.for_ingestion(),
        )


@dataclass(frozen=True)
class QueryConfig:
    """Storage, model, and audit settings required by the query Lambda.

    query_audit_table:
        Optional DynamoDB table that records question/answer metadata.
    vector:
        Vector-store settings used for semantic retrieval.
    bedrock:
        Embedding and generation model settings used during answering.
    """

    query_audit_table: Optional[str]
    vector: VectorConfig
    bedrock: BedrockConfig

    @classmethod
    def from_env(cls) -> "QueryConfig":
        """Build query configuration from Lambda environment variables."""
        return cls(
            query_audit_table=optional_env("QUERY_AUDIT_TABLE"),
            vector=VectorConfig.from_env(),
            bedrock=BedrockConfig.for_query(),
        )
