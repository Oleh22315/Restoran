from aiogram import types


async def answer_callback(callback: types.CallbackQuery, *args, **kwargs):
    await callback.bot.send_message(callback.from_user.id, *args, **kwargs)
