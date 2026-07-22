import os

DYNAMODB_ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT_URL") or None
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
POLLS_TABLE_NAME = os.getenv("POLLS_TABLE_NAME", "Polls")
