"""Notification backends for Wilson."""

from wilson.notifier.base import Notifier
from wilson.notifier.console import ConsoleNotifier

__all__ = ["ConsoleNotifier", "Notifier"]
