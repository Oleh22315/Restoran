from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from sqlalchemy import select, update
from db.user import User
from common import LocaleManager, answer_callback
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import State, StatesGroup

router = Router(name="commands-router")


async def start_message(bot, user_id: int, locale: LocaleManager.Locale):
    kb = [
        [types.InlineKeyboardButton(text="Змінити мову/Сhange language", callback_data="change_language")],
        [types.InlineKeyboardButton(text=locale.get("order.start"), callback_data="start_order")],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb, resize_keyboard=True)

    await bot.send_message(user_id, locale.get("start"), reply_markup=keyboard)


@router.message(CommandStart())
async def start(message: types.Message, locale: LocaleManager.Locale, session: AsyncSession):
    user: User = (await session.execute(select(User).filter(User.id == message.from_user.id))).scalars().first()

    if user is None:
        user = User(id=message.from_user.id, locale="en")
        session.add(user)
        await session.commit()

    now_time = datetime.now().time()

    time_start_work = datetime.strptime("00:00", "%H:%M").time()
    time_finish_work = datetime.strptime("23:59", "%H:%M").time()

    if not (time_start_work <= now_time <= time_finish_work):
        await message.answer(locale.get("closed"))
        return

    await start_message(message.bot, message.from_user.id, locale)


@router.callback_query(F.data == "change_language")
async def change_language(callback: types.CallbackQuery, manager: LocaleManager):
    kb = []

    for key, locale in manager.loaded_locales.items():
        kb.append(
            [
                types.InlineKeyboardButton(
                    text=locale.get("language.name"),
                    callback_data=f"change_language_{key}",
                )
            ]
        )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb, resize_keyboard=True)

    await answer_callback(callback, "Оберіть мову/Choose language", reply_markup=keyboard)


@router.callback_query(F.data.startswith("change_language_"))
async def update_language(callback: types.CallbackQuery, manager: LocaleManager, session: AsyncSession):
    language = callback.data.split("_")[-1]
    user_id = callback.from_user.id

    LocaleManager.USER_LOCALS[user_id] = language
    locale = manager.get_locale(language)

    await session.execute(update(User).where(User.id == user_id).values(locale=language))

    await callback.answer(locale.get("language.selected"))
    await start_message(callback.bot, user_id, locale)
