import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException

from app.db import get_polls_table
from app.models import OptionResult, PollCreate, PollResponse, VoteRequest

router = APIRouter(prefix="/polls", tags=["polls"])


def _item_to_response(item: dict) -> PollResponse:
    votes = item["votes"]
    options = [
        OptionResult(id=label["id"], text=label["text"], votes=int(votes[label["id"]]))
        for label in item["option_labels"]
    ]
    return PollResponse(
        poll_id=item["poll_id"],
        question=item["question"],
        options=options,
        total_votes=sum(o.votes for o in options),
        created_at=item["created_at"],
    )


@router.post("", response_model=PollResponse, status_code=201)
def create_poll(poll: PollCreate):
    poll_id = str(uuid.uuid4())
    option_labels = [{"id": f"opt_{i + 1}", "text": text} for i, text in enumerate(poll.options)]
    votes = {label["id"]: 0 for label in option_labels}

    item = {
        "poll_id": poll_id,
        "question": poll.question,
        "option_labels": option_labels,
        "votes": votes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    get_polls_table().put_item(Item=item)
    return _item_to_response(item)


@router.get("", response_model=list[PollResponse])
def list_polls():
    response = get_polls_table().scan()
    return [_item_to_response(item) for item in response["Items"]]


@router.get("/{poll_id}", response_model=PollResponse)
def get_poll(poll_id: str):
    response = get_polls_table().get_item(Key={"poll_id": poll_id})
    item = response.get("Item")
    if item is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    return _item_to_response(item)


@router.post("/{poll_id}/vote", response_model=PollResponse)
def vote(poll_id: str, vote_request: VoteRequest):
    table = get_polls_table()
    try:
        response = table.update_item(
            Key={"poll_id": poll_id},
            UpdateExpression="ADD votes.#opt :inc",
            ConditionExpression="attribute_exists(poll_id) AND attribute_exists(votes.#opt)",
            ExpressionAttributeNames={"#opt": vote_request.option_id},
            ExpressionAttributeValues={":inc": 1},
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Could be a missing poll or an invalid option_id; check which.
            existing = table.get_item(Key={"poll_id": poll_id}).get("Item")
            if existing is None:
                raise HTTPException(status_code=404, detail="Poll not found")
            raise HTTPException(status_code=400, detail="Invalid option_id")
        raise
    return _item_to_response(response["Attributes"])


@router.delete("/{poll_id}", status_code=204)
def delete_poll(poll_id: str):
    table = get_polls_table()
    try:
        table.delete_item(
            Key={"poll_id": poll_id},
            ConditionExpression="attribute_exists(poll_id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=404, detail="Poll not found")
        raise
