"""API write contracts."""
from typing import Literal
from pydantic import BaseModel, Field

IssueStatus = Literal["OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED"]


class IssueUpdate(BaseModel):
    status: IssueStatus
    actor: str = Field(min_length=2, max_length=100)
    note: str = Field(min_length=10, max_length=2000)


class AIInsight(BaseModel):
    headline: str = Field(min_length=8, max_length=180)
    summary: str = Field(min_length=15, max_length=750)
    recommendations: list[str] = Field(min_length=1, max_length=3)
