"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from story_companion import __version__


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: Literal["ok"]


app = FastAPI(
    title="Story Companion",
    description="Spoiler-safe, evidence-grounded reading companion API.",
    version=__version__,
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report whether the API process is ready to serve requests."""

    return HealthResponse(status="ok")
