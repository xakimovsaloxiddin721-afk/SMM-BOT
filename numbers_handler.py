from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import NUMBER_MARKUP
from database import db
from keyboards.main import number_providers, back_button, number_status_actions
from services import fivesim

router = Router(name="numbers")

# Eng ko'p so'raladigan xizmatlar (provayder kodlari turlicha, shu yerda soddalashtirilgan)
POPULAR_SERVICES = {
    "sms_activate": {"telegram": "tg", "whatsapp": "wa", "instagram": "ig", "google": "go"},
    "fivesim": {"telegram": "telegram", "whatsapp": "whatsapp", "instagram": "instagram", "google": "google"},
}
DEFAULT_COUNTRY_SMS_ACTIVATE = 0   # 0 = Russia
DEFAULT_COUNTRY_FIVESIM = "russia"


class BuyNumber(StatesGroup):
    choosing_service = State()


@router.callback_query(F.data == "menu:numbers")
async def numbers_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📱 Qaysi provayderdan raqam olmoqchisiz?",
        reply_markup=number_providers(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("numprov:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    provider = callback.data.split(":")[1]
    await state.update_data(provider=provider)

    kb = InlineKeyboardBuilder()
    for label in POPULAR_SERVICES[provider]:
        kb.button(text=label.capitalize(), callback_data=f"numsvc:{label}")
    kb.button(text="⬅️ Orqaga", callback_data="menu:numbers")
    kb.adjust(2)

    await callback.message.edit_text("Qaysi xizmat uchun raqam kerak?", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("numsvc:"))
async def confirm_and_buy(callback: CallbackQuery, state: FSMContext):
    label = callback.data.split(":")[1]
    data = await state.get_data()
    provider = data["provider"]
    service_code = POPULAR_SERVICES[provider][label]

    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    try:
        if provider == "sms_activate":
            cost = await sms_activate.get_price(service_code, DEFAULT_COUNTRY_SMS_ACTIVATE)
        else:
            cost = await fivesim.get_price(DEFAULT_COUNTRY_FIVESIM, service_code)
    except Exception as e:
        await callback.message.edit_text(f"❗️ Narxni olishda xatolik: {e}", reply_markup=back_button("menu:numbers"))
        await callback.answer()
        return

    price = round(cost * NUMBER_MARKUP, 2)

    if user["balance"] < price:
        await callback.message.edit_text(
            f"❗️ Balansingiz yetarli emas. Narxi: {price} so'm, balansingiz: {user['balance']:.2f} so'm.\n"
            "Hamyoningizni to'ldiring.",
            reply_markup=back_button("menu:wallet"),
        )
        await callback.answer()
        return

    try:
        if provider == "sms_activate":
            result = await sms_activate.buy_number(service_code, DEFAULT_COUNTRY_SMS_ACTIVATE)
        else:
            result = await fivesim.buy_number(DEFAULT_COUNTRY_FIVESIM, service_code)
    except Exception as e:
        await callback.message.edit_text(f"❗️ Raqam olishda xatolik: {e}", reply_markup=back_button("menu:numbers"))
        await callback.answer()
        return

    await db.change_balance(callback.from_user.id, -price)
    order_id = await db.create_number_order(
        user["id"], provider, service_code, DEFAULT_COUNTRY_SMS_ACTIVATE if provider == "sms_activate" else DEFAULT_COUNTRY_FIVESIM,
        result["phone"], result["activation_id"], price,
    )

    await callback.message.edit_text(
        f"✅ Raqam olindi!\n\n"
        f"📞 Raqam: <code>{result['phone']}</code>\n"
        f"💵 Narxi: {price} so'm\n\n"
        "SMS kelishini kutib, pastdagi tugma orqali tekshiring.",
        parse_mode="HTML",
        reply_markup=number_status_actions(order_id),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("numcheck:"))
async def check_number(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    async with db.get_db() as conn:
        cur = await conn.execute("SELECT * FROM number_orders WHERE id = ?", (order_id,))
        order = await cur.fetchone()

    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    module = sms_activate if order["provider"] == "sms_activate" else fivesim
    status = await module.get_status(order["activation_id"])

    if status["code"]:
        await db.update_number_order(order_id, status="received", sms_code=status["code"])
        await module.finish_number(order["activation_id"])
        await callback.message.edit_text(
            f"✅ Kod keldi!\n\n📞 Raqam: <code>{order['phone']}</code>\n🔑 Kod: <code>{status['code']}</code>",
            parse_mode="HTML",
        )
    else:
        await callback.answer("⏳ Hali kod kelmadi, birozdan so'ng qayta tekshiring.", show_alert=True)


@router.callback_query(F.data.startswith("numcancel:"))
async def cancel_number(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    async with db.get_db() as conn:
        cur = await conn.execute("SELECT * FROM number_orders WHERE id = ?", (order_id,))
        order = await cur.fetchone()

    if not order or order["status"] != "waiting":
        await callback.answer("Bu buyurtmani bekor qilib bo'lmaydi", show_alert=True)
        return

    module = sms_activate if order["provider"] == "sms_activate" else fivesim
    try:
        await module.cancel_number(order["activation_id"])
    except Exception:
        pass

    await db.update_number_order(order_id, status="cancelled")
    await db.change_balance(callback.from_user.id, order["price"])  # refund
    await callback.message.edit_text("❌ Buyurtma bekor qilindi, mablag' hamyoningizga qaytarildi.")
    await callback.answer()
