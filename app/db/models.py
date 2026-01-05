# app/db/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # dedupe key
    category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    extraction_attempts: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    next_extract_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    importance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reason_selected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


Index("ix_articles_source_scraped_at", Article.source, Article.scraped_at)


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    overall_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class DigestItem(Base):
    __tablename__ = "digest_items"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"), primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)

    rank: Mapped[int] = mapped_column(nullable=False)
    item_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
