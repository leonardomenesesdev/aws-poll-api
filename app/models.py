from typing import List

from pydantic import BaseModel, Field


class PollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    options: List[str] = Field(min_length=2, max_length=10)


class VoteRequest(BaseModel):
    option_id: str


class OptionResult(BaseModel):
    id: str
    text: str
    votes: int


class PollResponse(BaseModel):
    poll_id: str
    question: str
    options: List[OptionResult]
    total_votes: int
    created_at: str
