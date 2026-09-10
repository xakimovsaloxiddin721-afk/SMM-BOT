import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

SMM_PANEL_API_URL = os.getenv(
    "SMM_PANEL_API_URL",
    "https://smmpanel.co/api/v2"
)

SMM_PANEL_API_KEY = os.getenv("SMM_PANEL_API_KEY")

NUMBER_MARKUP = float(os.getenv("NUMBER_MARKUP", "1.2"))

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

if not SMM_PANEL_API_KEY:
    raise RuntimeError("SMM_PANEL_API_KEY topilmadi!")
