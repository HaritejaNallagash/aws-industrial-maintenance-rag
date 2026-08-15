"""S3 Vectors access wrapper.

The boto3 service name for S3 Vectors is ``s3vectors``. The API stores vectors
in a vector bucket and vector index rather than in a general-purpose S3 bucket.
"""

from typing import Dict, Iterable, List, Optional

import boto3


class S3VectorsStore:
    """Read and write vectors in a single S3 Vector Index.

    This class hides the AWS API shapes from the rest of the application so the
    ingestion and query code can think in terms of Python dicts and lists.
    """

    def __init__(self, bucket_name: str, index_name: str):
        """Remember the vector bucket/index names and create the boto3 client."""
        self.bucket_name = bucket_name
        self.index_name = index_name
        self.client = boto3.client("s3vectors")

    def put_vectors(self, vectors: Iterable[Dict]) -> int:
        """Write vectors in batches accepted by the S3 Vectors API.

        The API has batch-size limits, so the code buffers vectors and flushes
        them in chunks of 100.
        """
        batch = []
        count = 0
        for vector in vectors:
            batch.append(vector)
            if len(batch) == 100:
                self._put_batch(batch)
                count += len(batch)
                batch = []
        if batch:
            self._put_batch(batch)
            count += len(batch)
        return count

    def query(
        self,
        embedding: List[float],
        top_k: int,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """Return nearest-neighbor matches for a query embedding.

        Parameters
        ----------
        embedding:
            Vector representation of the user's question.
        top_k:
            Number of nearest matches to ask the index for.
        metadata_filter:
            Optional filter expression that narrows the search to matching
            metadata such as a specific equipment ID or document type.
        """
        request = {
            "vectorBucketName": self.bucket_name,
            "indexName": self.index_name,
            "queryVector": {"float32": embedding},
            "topK": top_k,
            "returnDistance": True,
            "returnMetadata": True,
        }
        if metadata_filter:
            request["filter"] = metadata_filter

        response = self.client.query_vectors(**request)
        return response.get("vectors", [])

    def _put_batch(self, batch: List[Dict]) -> None:
        """Send one already-sized vector batch to the AWS API."""
        self.client.put_vectors(
            vectorBucketName=self.bucket_name,
            indexName=self.index_name,
            vectors=batch,
        )
