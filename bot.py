import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.strategy import FSMStrategy

import config
import handlers


async def main():
    dp = Dispatcher(fsm_strategy=FSMStrategy.CHAT)
    bot = Bot(token=config.TOKEN)
    await bot.set_my_commands(commands=[{"command": "start", "description": "Start the bot"}])
    dp.include_router(handlers.router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())