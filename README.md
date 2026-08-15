# Industrial Maintenance RAG on AWS

## Overview

This project provides a retrieval-augmented generation assistant for industrial maintenance teams. It helps technicians and supervisors ask questions about equipment behavior, troubleshooting steps, spare parts, preventive maintenance, and operating procedures, then returns grounded answers with source citations.

The application uses:

- Amazon S3 for raw source documents, processed chunk output, and frontend hosting
- Amazon S3 Vectors for semantic retrieval
- Amazon Bedrock for embeddings and answer generation
- AWS Lambda for ingestion and query handling

The browser UI is a static frontend hosted from S3 and connected directly to a Lambda Function URL.

## Solution Flow

The current implementation follows this sequence:

1. source maintenance documents are generated locally as plain-text files
2. those files are uploaded to the raw S3 bucket
3. the ingestion Lambda reads the files, parses them, chunks them, creates embeddings, writes processed chunk JSON to S3, and stores vectors in S3 Vectors
4. the frontend sends a question to the query Lambda Function URL
5. the query Lambda embeds the question, retrieves relevant chunks from S3 Vectors, builds a grounded prompt, calls Bedrock, and returns an answer with citations

## Repository Structure

- `src/ingestion/` contains the ingestion Lambda
- `src/query_api/` contains the query Lambda
- `src/common/` contains shared config, Bedrock, JSON, and S3 Vectors helpers
- `src/data_generation/generate_seed_data.py` generates the sample maintenance corpus
- `frontend/` contains the static browser UI
- `scripts/build_lambda_packages.sh` builds the Lambda deployment zip files
- `scripts/write_frontend_config.sh` writes the frontend runtime config with the query endpoint

## Prerequisites

Before starting, make sure you have:

- an AWS account
- a region that supports Amazon Bedrock, Amazon S3 Vectors, and Lambda Function URLs
- Bedrock model access enabled for:
  - `amazon.titan-embed-text-v2:0`
  - `amazon.nova-lite-v1:0`
- Python 3.11
- `zip`

Optional but convenient:

- AWS CLI v2

Recommended region:

- `us-east-1`

## AWS Resources

Create these resources in your AWS account:

- one raw document S3 bucket
- one processed output S3 bucket
- one frontend hosting S3 bucket
- one S3 Vector bucket
- one S3 Vector index
- one shared Lambda IAM role
- one ingestion Lambda
- one query Lambda
- one Lambda Function URL for the query Lambda

Example names used in this guide:

- raw bucket: `industrial-maintenance-rag-manual-raw`
- processed bucket: `industrial-maintenance-rag-manual-processed`
- frontend bucket: `industrial-maintenance-rag-manual-frontend`
- vector bucket: `industrial-maintenance-rag-manual-vectors`
- vector index: `maintenance-knowledge`
- ingestion Lambda: `industrial-maintenance-rag-ingestion`
- query Lambda: `industrial-maintenance-rag-query`
- Lambda role: `industrial-maintenance-rag-manual-role`

If an S3 bucket name is already taken, choose a different name and use it consistently in the related environment variables, bucket policies, test payloads, and upload commands.

## Local Preparation

### 1. Open the repository

```bash
cd <project-directory>
```

### 2. Build the Lambda deployment packages

Run:

```bash
./scripts/build_lambda_packages.sh
```

This creates:

- `build/ingestion-lambda.zip`
- `build/query-lambda.zip`

### 3. Generate the sample source documents

Run:

```bash
python -m src.data_generation.generate_seed_data \
  --output-dir generated/source-documents \
  --question-file data/sample_questions/questions.json
```

Expected result:

- multiple `.txt` files inside `generated/source-documents/`

## AWS Setup

### 4. Create the S3 buckets

Create three S3 buckets:

1. raw source documents bucket
2. processed output bucket
3. frontend hosting bucket

Using the example names:

1. `industrial-maintenance-rag-manual-raw`
2. `industrial-maintenance-rag-manual-processed`
3. `industrial-maintenance-rag-manual-frontend`

Recommended settings:

- keep default encryption enabled
- keep the raw and processed buckets private
- versioning is optional

### 5. Enable static website hosting for the frontend bucket

For the frontend bucket:

1. open the bucket in S3
2. open `Properties`
3. enable `Static website hosting`
4. set `Index document` to `index.html`
5. open `Permissions`
6. turn off `Block all public access`
7. add a bucket policy allowing public `s3:GetObject`

Example policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadFrontend",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::industrial-maintenance-rag-manual-frontend/*"
    }
  ]
}
```

Save the bucket website endpoint. You will use it later in the browser.

### 6. Create the S3 Vector bucket

In Amazon S3 Vectors, create a vector bucket.

Example name:

- `industrial-maintenance-rag-manual-vectors`

### 7. Create the S3 Vector index

Inside the vector bucket, create an index with these settings:

- name: `maintenance-knowledge`
- dimensions: `1024`
- distance metric: `cosine`
- data type: `float32`

### 8. Create the shared Lambda IAM role

Create one IAM role for both Lambdas.

Suggested fast setup:

1. open IAM
2. create a role for `Lambda`
3. name it `industrial-maintenance-rag-manual-role`
4. attach only the IAM permissions required for S3, S3 Vectors, Bedrock, CloudWatch Logs, and Lambda execution

This keeps setup simple and avoids permission issues during initial deployment.

### 9. Create the ingestion Lambda

Create a Lambda function with:

- name: `industrial-maintenance-rag-ingestion`
- runtime: `Python 3.11`
- execution role: `industrial-maintenance-rag-manual-role`

Upload:

- `build/ingestion-lambda.zip`

Set the handler to:

```text
src.ingestion.handler.lambda_handler
```

Set these environment variables:

```text
RAW_BUCKET=industrial-maintenance-rag-manual-raw
PROCESSED_BUCKET=industrial-maintenance-rag-manual-processed
VECTOR_BUCKET_NAME=industrial-maintenance-rag-manual-vectors
VECTOR_INDEX_NAME=maintenance-knowledge
VECTOR_DIMENSIONS=1024
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
LOG_LEVEL=INFO
```

Optional:

- `DOCUMENT_TABLE`

Recommended Lambda settings:

- timeout: `5 minutes`
- memory: `1024 MB` or higher

### 10. Create the query Lambda

Create a Lambda function with:

- name: `industrial-maintenance-rag-query`
- runtime: `Python 3.11`
- execution role: `industrial-maintenance-rag-manual-role`

Upload:

- `build/query-lambda.zip`

Set the handler to:

```text
src.query_api.handler.lambda_handler
```

Set these environment variables:

```text
VECTOR_BUCKET_NAME=industrial-maintenance-rag-manual-vectors
VECTOR_INDEX_NAME=maintenance-knowledge
VECTOR_DIMENSIONS=1024
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
GENERATION_MODEL_ID=amazon.nova-lite-v1:0
LOG_LEVEL=INFO
```

Optional:

- `QUERY_AUDIT_TABLE`

Recommended Lambda settings:

- timeout: `30 seconds`
- memory: `1024 MB`

### 11. Create the query Lambda Function URL

For the query Lambda:

1. open `Configuration`
2. open `Function URL`
3. create a Function URL
4. set auth type to `NONE`

Set CORS like this:

- allowed origin:
  - `http://industrial-maintenance-rag-manual-frontend.s3-website-us-east-1.amazonaws.com`
- allowed methods:
  - `POST`
  - `OPTIONS`
- allowed headers:
  - `*`

Copy the Function URL. It will look similar to:

```text
https://abc123456789.lambda-url.us-east-1.on.aws/
```

## Frontend Setup

### 12. Write the frontend runtime config

Run:

```bash
./scripts/write_frontend_config.sh "https://abc123456789.lambda-url.us-east-1.on.aws/"
```

This updates:

- `frontend/runtime-config.js`

### 13. Upload the frontend files

Upload the contents of `frontend/` to the frontend S3 bucket.

Using AWS CLI:

```bash
aws s3 sync frontend s3://industrial-maintenance-rag-manual-frontend/ --delete
```

Files expected in the bucket root:

- `index.html`
- `styles.css`
- `app.js`
- `runtime-config.js`

## Data Load

### 14. Upload the generated source documents

Upload the generated `.txt` files to the raw bucket:

```bash
aws s3 sync generated/source-documents s3://industrial-maintenance-rag-manual-raw/source-documents/ --delete
```

### 15. Run the ingestion Lambda

Create a Lambda test event for the ingestion function using:

```json
{
  "bucket": "industrial-maintenance-rag-manual-raw",
  "prefix": "source-documents/"
}
```

Run the test.

Expected result:

- documents are read from the raw bucket
- processed chunk JSON files appear in the processed bucket
- vectors are written to the S3 Vector index

## Run the Application

### 16. Open the frontend website URL

Open the S3 static website endpoint for the frontend bucket.

It will look similar to:

```text
http://industrial-maintenance-rag-manual-frontend.s3-website-us-east-1.amazonaws.com
```

### 17. Ask a question

Use this sample question first:

- question: `What should a technician inspect when filler FILL-203 reports intermittent pressure loss?`
- equipment filter: `FILL-203`
- document type: leave blank
- results: `5`

Expected result:

- the answer panel shows a grounded answer
- the citations panel shows one or more source citations

## Exact Setup Order

Follow this sequence:

1. open the repository
2. build the Lambda zip files
3. generate the source documents
4. create the S3 buckets
5. enable static website hosting for the frontend bucket
6. create the S3 Vector bucket
7. create the S3 Vector index
8. create the shared Lambda IAM role
9. create and configure the ingestion Lambda
10. create and configure the query Lambda
11. create the query Lambda Function URL
12. write the frontend runtime config
13. upload the frontend files
14. upload the generated source documents
15. run ingestion
16. open the frontend website URL
17. ask a question

## Optional DynamoDB Tables

DynamoDB can be added if you want:

- document lineage written during ingestion
- query audit records written during question handling

If you want those features:

1. create a document metadata table
2. create a query audit table
3. set `DOCUMENT_TABLE` on the ingestion Lambda
4. set `QUERY_AUDIT_TABLE` on the query Lambda

Suggested names:

- `industrial-maintenance-rag-document-metadata`
- `industrial-maintenance-rag-query-audit`

Suggested keys:

- document metadata table:
  - partition key: `document_id`
  - sort key: `chunk_id`
- query audit table:
  - partition key: `query_id`

## Troubleshooting

If ingestion fails:

- confirm the ingestion handler is `src.ingestion.handler.lambda_handler`
- confirm the raw bucket contains `.txt` files under `source-documents/`
- confirm `RAW_BUCKET`, `PROCESSED_BUCKET`, `VECTOR_BUCKET_NAME`, and `VECTOR_INDEX_NAME` match your AWS resource names
- confirm Bedrock model access is enabled for `amazon.titan-embed-text-v2:0`
- check CloudWatch logs for timeout or permission errors

If query works in the Lambda test console but not in the browser:

- confirm the frontend is using the correct Function URL in `frontend/runtime-config.js`
- confirm the Function URL CORS origin exactly matches the frontend S3 website origin
- confirm the frontend bucket website URL is opened with `http://`
- re-upload the frontend files and hard refresh the browser

If the frontend page loads but the answer request fails:

- open browser developer tools
- inspect the network request to the Function URL
- verify the request is reaching the Lambda URL
- verify the response is returning JSON
- check the query Lambda CloudWatch logs

If the frontend website does not load:

- confirm static website hosting is enabled
- confirm `index.html` exists in the bucket root
- confirm the bucket policy allows public `s3:GetObject`

## Minimal Command Summary

```bash
cd "<your-project-folder>"
./scripts/build_lambda_packages.sh
python -m src.data_generation.generate_seed_data --output-dir generated/source-documents --question-file data/sample_questions/questions.json
./scripts/write_frontend_config.sh "YOUR-QUERY-LAMBDA-URL"
aws s3 sync frontend s3://industrial-maintenance-rag-manual-frontend-hn/ --delete
aws s3 sync generated/source-documents s3://industrial-maintenance-rag-manual-raw-hn/source-documents/ --delete
```
