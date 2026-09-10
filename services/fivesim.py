"""
5sim.net API client.
Docs: https://docs.5sim.net/
"""
import aiohttp

from config import FIVESIM_API_KEY

BASE_URL = "https://5sim.net/v1"

HEADERS = {
    "Authorization": f"Bearer {FIVESIM_API_KEY}",
    "Accept": "application/json",
}


class FiveSimError(Exception):
    pass


async def _get(path: str) -> dict:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(
            f"{BASE_URL}{path}",
            timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            data = await resp.json()

            if resp.status != 200:
                raise FiveSimError(str(data))

            return data


async def get_balance() -> float:
    data = await _get("/user/profile")
    return float(data.get("balance", 0))


async def get_price(country: str, product: str) -> float:
    data = await _get(
        f"/guest/prices?country={country}&product={product}"
    )

    try:
        operators = data[country][product]
        cheapest = min(
            op["cost"] for op in operators.values()
        )
        return float(cheapest)

    except (KeyError, ValueError):
        raise FiveSimError(
            "Bu servis/mamlakat uchun narx topilmadi"
        )


async def buy_number(
    country: str,
    product: str,
    operator: str = "any"
) -> dict:

    data = await _get(
        f"/user/buy/activation/{country}/{operator}/{product}"
    )

    return {
        "activation_id": str(data["id"]),
        "phone": data["phone"]
    }


async def get_status(activation_id: str) -> dict:
    data = await _get(f"/user/check/{activation_id}")

    status_map = {
        "PENDING": "waiting",
        "RECEIVED": "waiting",
        "FINISHED": "received",
        "CANCELED": "cancelled",
        "BANNED": "cancelled",
    }

    status = status_map.get(
        data.get("status", ""),
        "waiting"
    )

    code = None
    sms_list = data.get("sms") or []

    if sms_list:
        code = sms_list[-1].get("code")

    return {
        "status": status,
        "code": code
    }


async def cancel_number(activation_id: str):
    await _get(f"/user/cancel/{activation_id}")


async def finish_number(activation_id: str):
    await _get(f"/user/finish/{activation_id}")
