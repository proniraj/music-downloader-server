from typing import Any

from pydantic import BaseModel, Field


class HomeQuery(BaseModel):
    limit: int = Field(default=3, ge=1, le=20, description="Number of home rows to return")


class HomeRow(BaseModel):
    title: str | None = None
    contents: list[dict[str, Any]] = Field(default_factory=list)


class HomeResponse(BaseModel):
    rows: list[HomeRow]
    personalized: bool = False
    auth_mode: str = Field(
        default="none",
        description="Auth used for this response: browser, oauth, or none",
    )


class MoodCategory(BaseModel):
    title: str
    params: str


class MoodCategoriesResponse(BaseModel):
    sections: dict[str, list[MoodCategory]]
