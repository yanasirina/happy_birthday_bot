from aiogram import Bot


class TgLogger:
    def __init__(self, bot: Bot, admin_id: str):
        self.bot = bot
        self.admin_id = admin_id

    async def log(self, text: str):
        await self.bot.send_message(chat_id=self.admin_id, text=text)
