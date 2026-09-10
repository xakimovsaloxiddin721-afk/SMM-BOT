from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS
from database import db

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("stats"))
async def stats(message: Message):
    if not _is_admin(message.from_user.id):
        return

    async with db.get_db() as conn:
        users_count = (await (await conn.execute("SELECT COUNT(*) c FROM users")).fetchone())["c"]
        numbers_count = (await (await conn.execute("SELECT COUNT(*) c FROM number_orders")).fetchone())["c"]
        nakrutka_count = (await (await conn.execute("SELECT COUNT(*) c FROM nakrutka_orders")).fetchone())["c"]
        pending_topups = (await (await conn.execute(
            "SELECT COUNT(*) c FROM topup_requests WHERE status = 'pending'")).fetchone())["c"]

    await message.answer(
        "📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {users_count}\n"
        f"📱 Raqam buyurtmalari: {numbers_count}\n"
        f"🚀 Nakrutka buyurtmalari: {nakrutka_count}\n"
        f"⏳ Kutilayotgan to'lovlar: {pending_topups}"
    )


@router.message(Command("addbalance"))
async def add_balance(message: Message):
    """Usage: /addbalance <tg_id> <amount>"""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Foydalanish: /addbalance <tg_id> <summa>")
        return

    try:
        tg_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("❗️ Noto'g'ri format")
        return

    await db.get_or_create_user(tg_id, None)
    await db.change_balance(tg_id, amount)
    await message.answer(f"✅ {tg_id} foydalanuvchiga {amount} so'm qo'shildi")
