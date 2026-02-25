"""Pushover notification backend for iOS push notifications."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


class PushoverNotifier:
    """Sends push notifications via the Pushover service."""

    def __init__(self) -> None:
        self._api_token = os.environ.get("PUSHOVER_API_TOKEN", "")
        self._user_key = os.environ.get("PUSHOVER_USER_KEY", "")

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        """Send a push notification via Pushover.

        Requires PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY environment variables.
        """
        if not self._api_token or not self._user_key:
            logger.warning("Pushover credentials not configured — skipping notification")
            return False

        payload = {
            "token": self._api_token,
            "user": self._user_key,
            "title": title,
            "message": body,
            "html": 1,
        }
        if url:
            payload["url"] = url

        try:
            response = httpx.post(PUSHOVER_API_URL, data=payload, timeout=15)
            response.raise_for_status()
            logger.info("Pushover notification sent: %s", title)
            return True
        except httpx.HTTPError:
            logger.exception("Failed to send Pushover notification")
            return False
