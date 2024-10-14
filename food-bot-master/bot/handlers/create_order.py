from aiogram import Router, types, F
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from common import LocaleManager, answer_callback
from sqlalchemy.ext.asyncio import AsyncSession
from db import Category, Product
from .runtime_data import RuntimeData

router = Router(name="create_order-router")


@router.callback_query(F.data == "start_order")
async def start_order(
    callback: types.CallbackQuery,
    session: AsyncSession,
    current_locale: str,
    locale: LocaleManager.Locale,
):
    categories = (await session.execute(select(Category))).scalars().all()
    kb = []

    for category in categories:
        kb.append(
            [types.InlineKeyboardButton(text=category.name(current_locale), callback_data=f"category_{category.id}")]
        )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await answer_callback(callback, locale.get("order.menu"), reply_markup=keyboard)


@router.callback_query(F.data.startswith("category_"))
async def menu(
    callback: types.CallbackQuery,
    session: AsyncSession,
    current_locale: str,
    locale: LocaleManager.Locale,
):
    category_id = int(callback.data.split("_")[-1])

    category = (
        (
            await session.execute(
                select(Category).filter(Category.id == category_id).options(selectinload(Category.products))
            )
        )
        .scalars()
        .first()
    )

    for product in category.products:
        kb = [
            [
                types.InlineKeyboardButton(
                    text=locale.get("order.add_to_cart"), callback_data=f"add_to_cart_{product.id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=locale.get("order.remove_from_cart"), callback_data=f"remove_from_cart_{product.id}"
                )
            ],
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

        photo = types.URLInputFile(url=product.url)
        await callback.bot.send_photo(
            callback.from_user.id,
            photo,
            caption=product.name(current_locale),
            reply_markup=keyboard,
        )


async def current_cart(
    bot,
    user_id: int,
    session: AsyncSession,
    current_locale: str,
    locale: LocaleManager.Locale,
):
    if not RuntimeData.user_cart.get(user_id, []):
        return

    products = (
        (await session.execute(select(Product).filter(Product.id.in_(RuntimeData.user_cart.get(user_id, [])))))
        .scalars()
        .all()
    )
    products_str_l = []
    sum = 0
    for product in products:
        products_str_l.append(
            f"{product.name(current_locale)} - {product.price} {locale.get('payment-options.currency')}"
        )
        sum += product.price

    products_str = "\n".join(products_str_l)

    kb = [[types.InlineKeyboardButton(text=locale.get("order.checkout"), callback_data=f"process_order")]]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await bot.send_message(
        user_id,
        locale.get("order.items_in_cart").format(products_str, sum, locale.get("payment-options.currency")),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(
    callback: types.CallbackQuery,
    session: AsyncSession,
    current_locale: str,
    locale: LocaleManager.Locale,
):
    product_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    RuntimeData.user_cart[user_id] = RuntimeData.user_cart.get(user_id, []) + [product_id]

    product: Product = (await session.execute(select(Product).filter(Product.id == product_id))).scalars().first()

    await callback.answer(locale.get("order.new_item").format(product.name(current_locale)))
    await current_cart(callback.bot, user_id, session, current_locale, locale)


@router.callback_query(F.data.startswith("remove_from_cart_"))
async def remove_from_cart(
    callback: types.CallbackQuery,
    session: AsyncSession,
    current_locale: str,
    locale: LocaleManager.Locale,
):
    product_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    product: Product = (await session.execute(select(Product).filter(Product.id == product_id))).scalars().first()

    if not user_id in RuntimeData.user_cart or not product_id in RuntimeData.user_cart[user_id]:
        await callback.answer(locale.get("order.not_in_cart").format(product.name(current_locale)))
        return

    RuntimeData.user_cart[user_id].remove(product_id)
    await callback.answer(locale.get("order.remove_item").format(product.name(current_locale)))
