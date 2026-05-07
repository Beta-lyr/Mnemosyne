"""Multi-bot manager for running multiple Telegram bots concurrently."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.channel.telegram import TelegramChannel
from mnemosyne.db.models import Character
from mnemosyne.db.session import async_session

logger = logging.getLogger(__name__)


class BotManager:
    """Manages multiple Telegram bot instances, one per character."""

    def __init__(self):
        self.bots: dict[str, TelegramChannel] = {}

    async def start_all(self):
        """Start bots for all characters with configured Telegram tokens."""
        async with async_session() as session:
            result = await session.execute(
                select(Character).where(Character.telegram_token.isnot(None))
            )
            characters = result.scalars().all()

        for char in characters:
            if char.telegram_token:
                await self.register_bot(str(char.id), char.telegram_token, char.name)

    async def register_bot(self, character_id: str, token: str, name: str = ""):
        """Register and start a new bot for a character."""
        if character_id in self.bots:
            await self.unregister_bot(character_id)

        bot = TelegramChannel(token=token, character_id=character_id)
        try:
            await bot.start()
            self.bots[character_id] = bot
            logger.info("Registered bot for character %s (%s)", name or character_id, character_id[:8])
        except Exception as e:
            logger.error("Failed to start bot for character %s: %s", name or character_id, e)

    async def unregister_bot(self, character_id: str):
        """Stop and remove a bot."""
        if character_id in self.bots:
            await self.bots[character_id].stop()
            del self.bots[character_id]
            logger.info("Unregistered bot for character %s", character_id[:8])

    async def stop_all(self):
        """Stop all bots."""
        for char_id in list(self.bots.keys()):
            await self.unregister_bot(char_id)
        logger.info("All bots stopped")
