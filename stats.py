from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db

router = Router(name="stars")

STAR_PACKS = [50, 100, 250, 500, 1000]


class BuyStars(StatesGroup):
    entering_amount = State()


@router.callback_query(F.data == "menu:stars")
async def stars_menu(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    for amount in STAR_PACKS:
        kb.button(text=f"⭐ {amount}", callback_data=f"starspack:{amount}")
    kb.button(text="✏️ Boshqa miqdor", callback_data="starspack:custom")
    kb.button(text="⬅️ Orqaga", callback_data="menu:main")
    kb.adjust(2)

    await callback.message.edit_text(
        "⭐ Qancha Telegram Stars sotib olmoqchisiz?\n"
        "To'lov to'g'ridan-to'g'ri Telegram orqali amalga oshiriladi.",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("starspack:"))
async def stars_pack_chosen(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":")[1]
    if value == "custom":
        await state.set_state(BuyStars.entering_amount)
        await callback.message.edit_text("🔢 Nechta Stars sotib olmoqchisiz? (raqam kiriting)")
        await callback.answer()
        return

    await _send_stars_invoice(callback.message, int(value))
    await callback.answer()


@router.message(StateFilter(BuyStars.entering_amount))
async def stars_custom_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗️ Iltimos, to'g'ri son kiriting")
        return

    await state.clear()
    await _send_stars_invoice(message, amount)


async def _send_stars_invoice(message: Message, amount: int):
    user = await db.get_or_create_user(message.chat.id, message.chat.username)
    order_id = await db.create_stars_order(user["id"], amount)

    await message.answer_invoice(
        title=f"{amount} Telegram Stars",
        description=f"{amount} dona Telegram Stars sotib olish",
        payload=f"stars_order:{order_id}",
        currency="XTR",          # Telegram Stars valyutasi
        prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)],
        provider_token="",       # Stars uchun bo'sh qoldiriladi
    )


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_order:"):
        order_id = int(payload.split(":")[1])
        await db.set_stars_order_paid(order_id)
    await message.answer("✅ To'lov muvaffaqiyatli amalga oshirildi! Rahmat.")
