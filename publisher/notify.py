"""Email the author when a Medium draft is ready for review.

SMTP settings come from the environment (see README); the password is never logged or stored.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

from .post import Post


class NotConfigured(RuntimeError):
    pass


def build_message(post: Post, draft_url: str, sender: str, to: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Medium draft ready to review: {post.title}"
    msg["From"] = sender
    msg["To"] = to
    tags = ", ".join(post.tags) or "(none suggested)"
    msg.set_content(
        f"""A Medium draft was imported from your blog. Nothing has been published.

Review the Medium draft:
  {draft_url}

Before you hit Publish:
  1. Read it through in Medium's preview; check headings, images and links survived the import.
  2. Publish → add topics. Suggested: {tags}
  3. Story settings → Advanced: confirm the canonical link is
     {post.canonical_url}

Blog post (original):
  {post.canonical_url}

Reddit version, with copy buttons:
  {post.canonical_url}?kit
"""
    )
    return msg


def send(post: Post, draft_url: str) -> None:
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to = os.environ.get("NOTIFY_TO") or user
    if not (user and password and to):
        raise NotConfigured("set SMTP_USER, SMTP_PASSWORD (and optionally NOTIFY_TO) to get email notifications")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(build_message(post, draft_url, user, to))
