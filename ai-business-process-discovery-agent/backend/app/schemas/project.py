from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    objective: str = Field(...)
    status: str = Field(default="draft", max_length=50)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    objective: str | None = Field(default=None)
    status: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")


class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
