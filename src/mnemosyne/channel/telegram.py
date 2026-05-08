"""Telegram Bot channel implementation."""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from mnemosyne.agent.core import DialogEngine
from mnemosyne.channel.base import BaseChannel
from mnemosyne.db.session import async_session

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram Bot channel for a single character."""

    def __init__(self, token: str, character_id: str):
        self.token = token
        self.character_id = character_id
        self.app: Application | None = None
        self.dialog_engine = DialogEngine()

    async def start(self):
        """Start the Telegram bot."""
        self.app = Application.builder().token(self.token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("clear", self._handle_clear))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started for character %s", self.character_id)

    async def stop(self):
        """Stop the Telegram bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped for character %s", self.character_id)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        image_url: str | None = None,
        audio_url: str | None = None,
        video_url: str | None = None,
    ):
        """Send a message via Telegram."""
        if not self.app:
            return
        try:
            if image_url:
                await self.app.bot.send_photo(chat_id=chat_id, photo=image_url, caption=text)
            elif audio_url:
                await self.app.bot.send_audio(chat_id=chat_id, audio=audio_url, caption=text)
            elif video_url:
                await self.app.bot.send_video(chat_id=chat_id, video=video_url, caption=text)
            else:
                await self.app.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text("你好！我是你的伴侣，很高兴认识你~")

    async def _handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command - clear conversation history."""
        from sqlalchemy import delete
        from mnemosyne.db.models import Conversation

        async with async_session() as session:
            await session.execute(
                delete(Conversation).where(Conversation.character_id == self.character_id)
            )
            await session.commit()
        await update.message.reply_text("记忆已清除，我们重新开始吧~")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_message = update.message.text
        chat_id = str(update.message.chat_id)

        async with async_session() as session:
            # Save user message
            from mnemosyne.db.models import Conversation
            user_msg = Conversation(
                character_id=self.character_id,
                role="user",
                content=user_message,
            )
            session.add(user_msg)
            await session.commit()

            # Generate response
            response_text, image_url, audio_url, video_url = await self.dialog_engine.process_message(
                character_id=self.character_id,
                user_message=user_message,
                session=session,
            )

            # Save assistant response
            assistant_msg = Conversation(
                character_id=self.character_id,
                role="assistant",
                content=response_text,
                has_image=image_url is not None,
                image_url=image_url,
                audio_url=audio_url,
                video_url=video_url,
            )
            session.add(assistant_msg)
            await session.commit()

        # Send response
        await self.send_message(chat_id, response_text, image_url, audio_url, video_url)
