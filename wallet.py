from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from database import db
from keyboards.main import back_button, topup_confirm

router = Router(name="wallet")


def wallet_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Hamyonni to'ldirish", callback_data="wallet:topup")
    kb.button(text="⬅️ Orqaga", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


class TopUp(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


@router.callback_query(F.data == "menu:wallet")
async def wallet_menu(callback: CallbackQuery):
    balance = await db.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"💰 Sizning balansingiz: <b>{balance:.2f} so'm</b>\n\n"
        "Hamyonni to'ldirish uchun pastdagi tugmani bosing.",
        parse_mode="HTML",
        reply_markup=wallet_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "wallet:topup")
async def topup_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TopUp.waiting_amount)
    await callback.message.edit_text(
        "💵 Qancha summaga hamyoningizni to'ldirmoqchisiz?\n"
        "Summani so'mda kiriting (masalan: 50000):"
    )
    await callback.answer()


@router.message(StateFilter(TopUp.waiting_amount))
async def topup_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗️ Iltimos, to'g'ri raqam kiriting (masalan: 50000)")
        return

    await state.update_data(amount=amount)
    await state.set_state(TopUp.waiting_receipt)
    await message.answer(
        f"Summasi: <b>{amount:.0f} so'm</b>\n\n"
        "To'lovni admin karta raqamiga o'tkazing, so'ng chek skrinshotini shu yerga yuboring.\n"
        "(Chek majburiy emas — istasangiz shunchaki 'yubordim' deb yozing)",
        parse_mode="HTML",
    )


@router.message(StateFilter(TopUp.waiting_receipt))
async def topup_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data["amount"]

    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    receipt_file_id = None
    if message.photo:
        receipt_file_id = message.photo[-1].file_id

    request_id = await db.create_topup_request(user["id"], amount, receipt_file_id)
    await state.clear()

    await message.answer(
        "✅ So'rovingiz qabul qilindi, admin tasdiqlashini kuting.\n"
        f"So'rov raqami: #{request_id}"
    )

    admin_text = (
        f"🆕 Hamyon to'ldirish so'rovi #{request_id}\n"
        f"Foydalanuvchi: @{message.from_user.username or message.from_user.id} "
        f"(id: {message.from_user.id})\n"
        f"Summa: {amount:.0f} so'm"
    )
    for admin_id in ADMIN_IDS:
        try:
            if receipt_file_id:
                await bot.send_photo(admin_id, receipt_file_id, caption=admin_text,
                                      reply_markup=topup_confirm(request_id))
            else:
                await bot.send_message(admin_id, admin_text, reply_markup=topup_confirm(request_id))
        except Exception:
            pass


@router.callback_query(F.data.startswith("topup:"))
async def topup_decision(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Sizga ruxsat yo'q", show_alert=True)
        return

    _, action, request_id_str = callback.data.split(":")
    request_id = int(request_id_str)
    request = await db.get_topup_request(request_id)

    if not request:
        await callback.answer("So'rov topilmadi", show_alert=True)
        return
    if request["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
        return

    async with db.get_db() as conn:
        cur = await conn.execute("SELECT tg_id FROM users WHERE id = ?", (request["user_id"],))
        user_row = await cur.fetchone()
    tg_id = user_row["tg_id"]

    if action == "approve":
        await db.change_balance(tg_id, request["amount"])
        await db.set_topup_status(request_id, "approved")
        await callback.message.edit_caption(caption=f"{callback.message.caption or callback.message.text}\n\n✅ Tasdiqlandi") \
            if callback.message.caption else \
            await callback.message.edit_text(f"{callback.message.text}\n\n✅ Tasdiqlandi")
        await bot.send_message(tg_id, f"✅ Hamyoningiz {request['amount']:.0f} so'mga to'ldirildi!")
    else:
        await db.set_topup_status(request_id, "rejected")
        await callback.message.edit_caption(caption=f"{callback.message.caption or callback.message.text}\n\n❌ Rad etildi") \
            if callback.message.caption else \
            await callback.message.edit_text(f"{callback.message.text}\n\n❌ Rad etildi")
        await bot.send_message(tg_id, f"❌ Hamyon to'ldirish so'rovingiz (#{request_id}) rad etildi.")

    await callback.answer("Bajarildi")
