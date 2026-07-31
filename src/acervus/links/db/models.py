"""SQLAlchemy models for Acervus."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Root(Base):
    __tablename__ = "roots"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(255), unique=True)
    path: Mapped[str] = mapped_column(String(4096))

    files: Mapped[list[File]] = relationship(
        back_populates="root", cascade="all, delete-orphan",
    )


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("root_id", "relative_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    root_id: Mapped[int] = mapped_column(ForeignKey("roots.id"))
    relative_path: Mapped[str] = mapped_column(String(4096))
    size: Mapped[int] = mapped_column()
    mtime: Mapped[float] = mapped_column()

    root: Mapped[Root] = relationship(back_populates="files")
    marks: Mapped[list[Mark]] = relationship(
        secondary="file_marks", back_populates="files",
    )
    stack_id: Mapped[int | None] = mapped_column(ForeignKey("stacks.id"), default=None)
    stack: Mapped[Stack | None] = relationship(back_populates="files")


class Mark(Base):
    __tablename__ = "marks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    files: Mapped[list[File]] = relationship(
        secondary="file_marks", back_populates="marks",
    )


class FileMark(Base):
    __tablename__ = "file_marks"

    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    mark_id: Mapped[int] = mapped_column(ForeignKey("marks.id"), primary_key=True)


class Stack(Base):
    __tablename__ = "stacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    files: Mapped[list[File]] = relationship(back_populates="stack")
