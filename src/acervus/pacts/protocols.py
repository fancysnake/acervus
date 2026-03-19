"""Pacts protocols — interfaces for repositories, UoW, and DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from pathlib import Path

    from acervus.pacts.dataclasses import FileInfo
    from acervus.pacts.dtos import FileDTO, MarkDTO, RootDTO, StackDTO


@runtime_checkable
class FilesystemReaderProtocol(Protocol):
    def scan(self, root_path: Path) -> list[FileInfo]: ...


@runtime_checkable
class RootRepositoryProtocol(Protocol):
    def sync_roots(self, roots: dict[str, Path]) -> None: ...
    def list_all(self) -> list[RootDTO]: ...
    def read(self, pk: int) -> RootDTO: ...
    def read_by_alias(self, alias: str) -> RootDTO: ...


@runtime_checkable
class FileRepositoryProtocol(Protocol):
    def list_all(self) -> list[FileDTO]: ...
    def list_by_root(self, root_id: int) -> list[FileDTO]: ...


@runtime_checkable
class MarkRepositoryProtocol(Protocol):
    def list_all(self) -> list[MarkDTO]: ...


@runtime_checkable
class StackRepositoryProtocol(Protocol):
    def list_all(self) -> list[StackDTO]: ...


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    @staticmethod
    def atomic() -> AbstractContextManager[None]: ...

    @property
    def roots(self) -> RootRepositoryProtocol: ...

    @property
    def files(self) -> FileRepositoryProtocol: ...

    @property
    def marks(self) -> MarkRepositoryProtocol: ...

    @property
    def stacks(self) -> StackRepositoryProtocol: ...


@runtime_checkable
class DependencyInjectorProtocol(Protocol):
    @property
    def uow(self) -> UnitOfWorkProtocol: ...
