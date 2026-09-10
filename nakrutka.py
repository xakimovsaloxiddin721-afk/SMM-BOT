from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import NAKRUTKA_MARKUP
from database import db
from keyboards.main import back_button
from services import smm_panel

router = Router(name="nakrutka")

CATEGORIES_PER_PAGE = 8


class Nakrutka(StatesGroup):
    choosing_service = State()
    entering_link = State()
    entering_quantity = State()


async def _fetch_services() -> list[dict]:
    services = await smm_panel.get_services()
    # keep it simple: only the first N most relevant, real bot should cache in DB
    return services[:50]


@router.callback_query(F.data == "menu:nakrutka")
async def nakrutka_menu(callback: CallbackQuery, state: FSMContext):
    try:
        services = await _fetch_services()
    except Exception as e:
        await callback.message.edit_text(f"❗️ Xizmatlar ro'yxatini olishda xatolik: {e}", reply_markup=back_button())
        await callback.answer()
        return

    await state.update_data(services={str(s["service"]): s for s in services})

    kb = InlineKeyboardBuilder()
    for s in services[:CATEGORIES_PER_PAGE]:
        name = s.get("name", "")[:40]
        kb.button(text=name, callback_data=f"nksvc:{s['service']}")
    kb.button(text="⬅️ Orqaga", callback_data="menu:main")
    kb.adjust(1)

    await callback.message.edit_text(
        "🚀 Nakrutka xizmatini tanlang (mashhur xizmatlar ro'yxati):",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("nksvc:"))
async def choose_link(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split(":")[1]
    data = await state.get_data()
    service = data["services"].get(service_id)

    if not service:
        await callback.answer("Xizmat topilmadi, qayta urinib ko'ring", show_alert=True)
        return

    await state.update_data(chosen_service=service)
    await state.set_state(Nakrutka.entering_link)

    rate = float(service["rate"])
    price_per_1000 = round(rate * NAKRUTKA_MARKUP, 2)

    await callback.message.edit_text(
        f"Xizmat: <b>{service['name']}</b>\n"
        f"Narxi: {price_per_1000} so'm / 1000 ta\n"
        f"Min: {service.get('min', '-')}, Max: {service.get('max', '-')}\n\n"
        "🔗 Havolani (link) yuboring:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(Nakrutka.entering_link))
async def enter_quantity(message: Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("❗️ Iltimos, to'g'ri havola yuboring (https:// bilan boshlanishi kerak)")
        return

    await state.update_data(link=link)
    await state.set_state(Nakrutka.entering_quantity)
    await message.answer("🔢 Nechta miqdorda buyurtma berasiz? (masalan: 1000)")


@router.message(StateFilter(Nakrutka.entering_quantity))
async def place_order(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗️ Iltimos, to'g'ri son kiriting (masalan: 1000)")
        return

    data = await state.get_data()
    service = data["chosen_service"]
    link = data["link"]

    rate = float(service["rate"])
    price = round((rate / 1000) * quantity * NAKRUTKA_MARKUP, 2)

    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    if user["balance"] < price:
        await message.answer(
            f"❗️ Balansingiz yetarli emas. Narxi: {price} so'm, balansingiz: {user['balance']:.2f} so'm."
        )
        await state.clear()
        return

    try:
        panel_order_id = await smm_panel.add_order(int(service["service"]), link, quantity)
    except Exception as e:
        await message.answer(f"❗️ Buyurtma berishda xatolik: {e}")
        await state.clear()
        return

    await db.change_balance(message.from_user.id, -price)
    order_id = await db.create_nakrutka_order(
        user["id"], int(service["service"]), service["name"], link, quantity, price
    )
    await db.update_nakrutka_order(order_id, panel_order_id=str(panel_order_id), status="in_progress")

    await message.answer(
        f"✅ Buyurtma qabul qilindi!\n\n"
        f"Xizmat: {service['name']}\n"
        f"Miqdor: {quantity}\n"
        f"Narxi: {price} so'm\n"
        f"Buyurtma raqami: #{order_id}\n\n"
        "Holatni /myorders orqali tekshirishingiz mumkin."
    )
    await state.clear()
