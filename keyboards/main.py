from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(
        text="📱 Virtual raqam",
        callback_data="menu:numbers"
    )

    kb.button(
        text="⭐ Telegram Stars",
        callback_data="menu:stars"
    )

    kb.button(
        text="🚀 Nakrutka",
        callback_data="menu:nakrutka"
    )

    kb.button(
        text="💰 Balans / Hamyon",
        callback_data="menu:wallet"
    )

    kb.button(
        text="🧑‍💻 Qo'llab-quvvatlash",
        callback_data="menu:support"
    )

    kb.adjust(1)

    return kb.as_markup()


def back_button(target: str = "menu:main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(
        text="⬅️ Orqaga",
        callback_data=target
    )

    return kb.as_markup()


def number_providers() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(
        text="📱 SMS-Activate",
        callback_data="numprov:sms_activate"
    )

    kb.button(
        text="📱 5SIM",
        callback_data="numprov:fivesim"
    )

    kb.button(
        text="⬅️ Orqaga",
        callback_data="menu:main"
    )

    kb.adjust(1)

    return kb.as_markup()


def topup_confirm(request_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(
        text="✅ To'lovni tasdiqlash",
        callback_data=f"topup_confirm:{request_id}"
    )

    kb.button(
        text="❌ Bekor qilish",
        callback_data=f"topup_cancel:{request_id}"
    )

    kb.button(
        text="⬅️ Orqaga",
        callback_data="menu:wallet"
    )

    kb.adjust(1)

    return kb.as_markup()


def number_status_actions(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(
        text="🔄 SMS kodni tekshirish",
        callback_data=f"numcheck:{order_id}"
    )

    kb.button(
        text="❌ Bekor qilish",
        callback_data=f"numcancel:{order_id}"
    )

    kb.adjust(1)

    return kb.as_markup()
