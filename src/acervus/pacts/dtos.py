"""Pacts DTOs — Pydantic models with from_attributes support."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RootDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alias: str
    path: str


class FileDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    root_id: int
    relative_path: str
    size: int
    mtime: datetime


class MarkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StackDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
