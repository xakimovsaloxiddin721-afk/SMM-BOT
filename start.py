from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards.main import main_menu, back_button

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 Xush kelibsiz!\n\n"
        "Bu bot orqali siz:\n"
        "📱 Virtual raqam sotib olishingiz\n"
        "⭐ Telegram Stars sotib olishingiz\n"
        "🚀 Nakrutka xizmatlaridan foydalanishingiz mumkin\n\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Bosh menyu:", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧑‍💻 Savol yoki muammo bo'lsa, admin bilan bog'laning: @your_admin_username",
        reply_markup=back_button(),
    )
    await callback.answer()
