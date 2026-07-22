from fastapi import FastAPI

from app.config import DYNAMODB_ENDPOINT_URL
from app.db import ensure_table_exists
from app.routers import polls

app = FastAPI(title="Poll API", version="1.0.0")
app.include_router(polls.router)


@app.on_event("startup")
def startup():
    # Auto-create the table only for local dev against DynamoDB Local.
    # In AWS the table is provisioned via IaC, so this is a no-op there.
    if DYNAMODB_ENDPOINT_URL:
        ensure_table_exists()


@app.get("/health")
def health():
    return {"status": "ok"}
