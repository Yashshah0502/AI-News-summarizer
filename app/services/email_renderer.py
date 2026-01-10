# app/services/email_renderer.py
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Tuple, List

from sqlalchemy import select

from app.db.models import Digest, DigestItem, Article
from app.services.database import SessionLocal


def render_digest(digest_id: int) -> Tuple[str, str, str]:
    with SessionLocal() as s:
        d = s.get(Digest, digest_id)
        if not d:
            raise ValueError(f"Digest not found: {digest_id}")

        rows = s.execute(
            select(
                DigestItem.rank,
                Article.title,
                Article.url,
                Article.source,
                DigestItem.item_summary,
            )
            .join(Article, Article.id == DigestItem.article_id)
            .where(DigestItem.digest_id == digest_id)
            .order_by(DigestItem.rank)
        ).all()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"News Digest (Last 10 Hours) — Top {len(rows)} — {timestamp}"
    window = f"Window: {d.window_start} → {d.window_end}"

    # ---------- TEXT ----------
    lines: List[str] = [subject, window, ""]
    if d.overall_summary:
        lines += ["Overall:", d.overall_summary.strip(), ""]

    for rank, title, url, source, item_summary in rows:
        lines.append(f"{rank}) {title} [{source}]")
        if item_summary:
            # item_summary can already contain bullets; keep as-is
            lines.append(item_summary.strip())
        lines.append(url)
        lines.append("")

    text_body = "\n".join(lines).strip() + "\n"

    # ---------- HTML ----------
    parts: List[str] = []
    parts.append(f"<h2>{escape(subject)}</h2>")
    parts.append(f"<p><em>{escape(window)}</em></p>")

    if d.overall_summary:
        parts.append("<h3>Overall</h3>")
        overall_html = escape(d.overall_summary).replace("\n", "<br>")
        parts.append(f"<p>{overall_html}</p>")

    parts.append("<h3>Top stories</h3><ol>")
    for rank, title, url, source, item_summary in rows:
        parts.append(
            f'<li><a href="{escape(url)}">{escape(title)}</a> '
            f'<small>[{escape(source)}]</small>'
        )
        if item_summary:
            # render newlines as <br> (simple + safe)
            item_html = escape(item_summary).replace("\n", "<br>")
            parts.append(f"<div style='margin-top:6px'>{item_html}</div>")
        parts.append("</li>")
    parts.append("</ol>")

    html_body = "\n".join(parts)
    return subject, text_body, html_body
