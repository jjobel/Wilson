"""Base notification interface."""

from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    """Protocol for notification backends."""

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        """Send a notification.

        Args:
            title: Notification title/headline.
            body: Notification body text.
            url: Optional URL to include (e.g. link to full digest).

        Returns:
            True if the notification was sent successfully.
        """
        ...
