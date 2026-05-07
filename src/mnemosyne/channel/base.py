"""Base channel abstraction."""

from abc import ABC, abstractmethod


class BaseChannel(ABC):
    """Abstract base class for communication channels."""

    @abstractmethod
    async def start(self):
        """Start the channel."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self):
        """Stop the channel."""
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, chat_id: str, text: str, image_url: str | None = None):
        """Send a message through the channel."""
        raise NotImplementedError
