from aiogram import Router, types, F
from sqlalchemy import select, func
from common import LocaleManager, answer_callback
from sqlalchemy.ext.asyncio import AsyncSession
from db import Product, Order
from .runtime_data import RuntimeData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os

router = Router(name="process_order-router")


class OrderFood(StatesGroup):
    choose_delivery_type = State()
    choose_name = State()
    choose_phone = State()
    choose_location = State()
    choose_payment = State()


async def finish_checkout(bot, user_id, data: dict, locale: LocaleManager.Locale, session: AsyncSession):
    order = Order(
        user_id=user_id,
        phone=data.get("phone"),
        location=data.get("location"),
        delivery_type=data.get("delivery_type"),
        paid=data.get("paid"),
        price=data.get("price"),
    )
    products = (
        (await session.execute(select(Product).filter(Product.id.in_(RuntimeData.user_cart.get(user_id, [])))))
        .scalars()
        .all()
    )

    order.products.extend(products)

    session.add(order)
    await session.commit()

    RuntimeData.user_cart.pop(user_id)
    await bot.send_message(user_id, locale.get("checkout.finish"), reply_markup=None)


@router.callback_query(F.data == "process_order")
async def process_order(
    callback: types.CallbackQuery,
    locale: LocaleManager.Locale,
    state: FSMContext,
    session: AsyncSession,
):

    price = (
        await session.execute(
            select(func.sum(Product.price)).filter(Product.id.in_(RuntimeData.user_cart.get(callback.from_user.id, [])))
        )
    ).scalar() or 0
    await state.update_data(price=price)

    kb = [
        [
            types.InlineKeyboardButton(text=locale.get("delivery-options.delivery"), callback_data="delivery_delivery"),
            types.InlineKeyboardButton(text=locale.get("delivery-options.in-place"), callback_data="delivery_in-place"),
        ]
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await state.set_state(OrderFood.choose_delivery_type)
    await answer_callback(callback, locale.get("checkout.delivery"), reply_markup=keyboard)


@router.callback_query(OrderFood.choose_delivery_type, F.data.startswith("delivery_"))
async def service_type(
    callback: types.CallbackQuery,
    locale: LocaleManager.Locale,
    state: FSMContext,
):
    service_type = callback.data.split("_")[-1]

    await state.update_data(delivery_type=service_type)
    await state.set_state(OrderFood.choose_name)

    await answer_callback(callback, locale.get("checkout.name"))


@router.message(OrderFood.choose_name)
async def name(
    message: types.Message,
    locale: LocaleManager.Locale,
    state: FSMContext,
):
    await state.update_data(name=message.text)
    await state.set_state(OrderFood.choose_phone)

    kb = [[types.KeyboardButton(text=locale.get("checkout.phone"), request_contact=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(locale.get("checkout.ask_phone"), reply_markup=keyboard)


@router.message(OrderFood.choose_phone)
async def phone(
    message: types.Message,
    locale: LocaleManager.Locale,
    state: FSMContext,
):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(OrderFood.choose_location)

    kb = [[types.KeyboardButton(text=locale.get("checkout.location"), request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(locale.get("checkout.ask_location"), reply_markup=keyboard)


@router.message(OrderFood.choose_location)
async def location(
    message: types.Message,
    locale: LocaleManager.Locale,
    state: FSMContext,
):
    await state.update_data(location_longitude=message.location.longitude)
    await state.update_data(location_latitude=message.location.latitude)
    await state.set_state(OrderFood.choose_payment)

    payment_methods = ["cash", "card", "in-app"]
    kb = []
    for method in payment_methods:
        kb.append(
            types.InlineKeyboardButton(text=locale.get(f"payment-options.{method}"), callback_data=f"payment_{method}")
        )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[kb])

    await message.answer(locale.get("checkout.payment"), reply_markup=keyboard)


@router.callback_query(OrderFood.choose_payment, F.data == "payment_in-app")
async def payment_in_app(
    callback: types.CallbackQuery,
    locale: LocaleManager.Locale,
    state: FSMContext,
):
    bot = callback.bot
    user_id = callback.from_user.id

    payment_type = callback.data.split("_")[-1]
    await state.update_data(payment=payment_type)
    data = await state.get_data()

    await bot.send_invoice(
        user_id,
        title=locale.get("invoice.title"),
        description=locale.get("invoice.description"),
        payload="payload",
        provider_token=os.getenv("PAYMENT_TOKEN"),
        currency="UAH",
        is_flexible=False,
        prices=[types.LabeledPrice(label=locale.get("invoice.label"), amount=data["price"])],
    )


@router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(True)


@router.message(F.successful_payment)
async def process_successful_payment(
    message: types.Message, locale: LocaleManager.Locale, state: FSMContext, session: AsyncSession
):
    await state.update_data(is_paid=True)

    await message.answer(locale.get("invoice.success"))

    data = await state.get_data()
    await state.set_state(None)
    await finish_checkout(message.bot, message.from_user.id, data, locale, session)


@router.callback_query(OrderFood.choose_payment, F.data.startswith("payment_"))
async def payment_type(
    callback: types.CallbackQuery,
    locale: LocaleManager.Locale,
    session: AsyncSession,
    state: FSMContext,
):
    payment_type = callback.data.split("_")[-1]
    await state.update_data(payment=payment_type)
    await state.update_data(is_paid=False)

    data = await state.get_data()
    await state.set_state(None)
    await finish_checkout(callback.bot, callback.from_user.id, data, locale, session)
