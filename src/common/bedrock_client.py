"""Bedrock client wrapper for embeddings and grounded answer generation."""

import json
import random
import time
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError


class BedrockModelClient:
    """Thin wrapper around Bedrock Runtime.

    The ingestion and query paths both need embeddings. The query path also
    needs a text generation call. Bedrock's Converse API keeps generation model
    payloads consistent across modern chat-capable models, while embeddings use
    the Titan embedding model's invoke_model payload shape.
    """

    def __init__(
        self,
        embedding_model_id: str,
        generation_model_id: str = None,
    ):
        """Create a reusable Bedrock Runtime client.

        Parameters
        ----------
        embedding_model_id:
            Model used to convert text into vectors for both indexing and query
            lookup.

        generation_model_id:
            Optional text-generation model used only in the query path to turn
            retrieved chunks into a final natural-language answer.
        """
        self.embedding_model_id = embedding_model_id
        self.generation_model_id = generation_model_id
        self.runtime = boto3.client("bedrock-runtime")

    def embed_text(self, text: str, dimensions: int) -> List[float]:
        """Return a normalized Titan text embedding for one text value.

        Parameters
        ----------
        text:
            Raw text to embed. The method truncates to 50,000 characters to stay
            within safe request sizes for the embedding model.

        dimensions:
            Number of coordinates expected by the downstream vector index.
        """

        # ``normalize=True`` makes cosine-style similarity comparisons more
        # stable because each vector is scaled to a consistent length.
        payload = {
            "inputText": text[:50000],
            "dimensions": dimensions,
            "normalize": True,
        }

        # Bedrock can temporarily throttle requests. Retry with exponential
        # backoff instead of immediately failing the entire ingestion Lambda.
        max_attempts = 8

        for attempt in range(max_attempts):
            try:
                response = self.runtime.invoke_model(
                    modelId=self.embedding_model_id,
                    body=json.dumps(payload).encode("utf-8"),
                    contentType="application/json",
                    accept="application/json",
                )
                break

            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code", "")

                retryable_errors = {
                    "ThrottlingException",
                    "TooManyRequestsException",
                    "ServiceUnavailableException",
                }

                # If the error is not retryable, or this was the final attempt,
                # immediately raise the original AWS error.
                if (
                    error_code not in retryable_errors
                    or attempt == max_attempts - 1
                ):
                    raise

                # Exponential backoff:
                # attempt 0 -> ~1-2 seconds
                # attempt 1 -> ~2-3 seconds
                # attempt 2 -> ~4-5 seconds
                # ...
                delay = min(20, 2 ** attempt) + random.uniform(0, 1)

                print(
                    "Bedrock request throttled. "
                    f"Retrying in {delay:.2f} seconds "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )

                time.sleep(delay)

        else:
            raise RuntimeError(
                "Bedrock embedding request failed after retries"
            )

        response_body = json.loads(response["body"].read())

        embedding = response_body.get("embedding")

        if not embedding:
            raise RuntimeError(
                "Bedrock embedding response did not contain an embedding"
            )

        return [float(value) for value in embedding]

    def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate an answer using Bedrock Converse.

        ``system_prompt`` defines the assistant behavior, while ``user_prompt``
        contains the actual question plus retrieved evidence chunks.
        """

        if not self.generation_model_id:
            raise RuntimeError(
                "generation_model_id is required for answer generation"
            )

        # The Converse API returns message content as a list of blocks. The code
        # joins only text blocks because that is all this project uses.
        response = self.runtime.converse(
            modelId=self.generation_model_id,
            system=[
                {
                    "text": system_prompt
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": user_prompt
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 900,
                "temperature": 0.2,
                "topP": 0.9,
            },
        )

        content = (
            response
            .get("output", {})
            .get("message", {})
            .get("content", [])
        )

        text_blocks = [
            block["text"]
            for block in content
            if "text" in block
        ]

        return "\n".join(text_blocks).strip()


def compact_embedding_debug(
    embedding: List[float],
) -> Dict[str, float]:
    """Return safe diagnostic information without logging the full vector.

    Full embeddings are noisy, large, and rarely useful in logs. A small
    summary helps verify that embedding generation happened at all.
    """

    if not embedding:
        return {
            "dimensions": 0,
            "first_value": 0.0,
        }

    return {
        "dimensions": len(embedding),
        "first_value": round(embedding[0], 6),
    }
