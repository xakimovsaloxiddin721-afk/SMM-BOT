"""
SMS-Activate.org API client (v1, GET-based).
Docs: https://sms-activate.org/en/api2
"""
import aiohttp

from config import SMS_ACTIVATE_API_KEY

BASE_URL = "https://api.sms-activate.org/stubs/handler_api.php"

STATUS_MAP = {
    "STATUS_WAIT_CODE": "waiting",
    "STATUS_OK": "received",
    "STATUS_CANCEL": "cancelled",
}


class SmsActivateError(Exception):
    pass


async def _request(params: dict) -> str:
    params = {"api_key": SMS_ACTIVATE_API_KEY, **params}
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if text.startswith("BAD_") or text == "NO_BALANCE" or text == "ERROR_SQL":
                raise SmsActivateError(text)
            return text


async def get_balance() -> float:
    text = await _request({"action": "getBalance"})
    # format: ACCESS_BALANCE:123.45
    return float(text.split(":")[1])


async def get_price(service: str, country: int) -> float:
    """Returns cost in RUB for the cheapest available number for a service/country."""
    import json
    text = await _request({"action": "getPrices", "service": service, "country": country})
    data = json.loads(text)
    country_data = data.get(str(country), {})
    service_data = country_data.get(service, {})
    if not service_data:
        raise SmsActivateError("Bu servis/mamlakat uchun narx topilmadi")
    return float(service_data.get("cost", 0))


async def buy_number(service: str, country: int) -> dict:
    """Buys a number. Returns {activation_id, phone}."""
    text = await _request({"action": "getNumber", "service": service, "country": country})
    # format: ACCESS_NUMBER:activationId:phoneNumber
    parts = text.split(":")
    if parts[0] != "ACCESS_NUMBER":
        raise SmsActivateError(text)
    return {"activation_id": parts[1], "phone": parts[2]}


async def get_status(activation_id: str) -> dict:
    """Returns {status, code} where status is one of waiting/received/cancelled."""
    text = await _request({"action": "getStatus", "id": activation_id})
    parts = text.split(":")
    raw_status = parts[0]
    code = parts[1] if len(parts) > 1 else None
    return {"status": STATUS_MAP.get(raw_status, "waiting"), "code": code}


async def cancel_number(activation_id: str):
    # status 8 = cancel activation
    await _request({"action": "setStatus", "id": activation_id, "status": 8})


async def finish_number(activation_id: str):
    # status 6 = complete activation
    await _request({"action": "setStatus", "id": activation_id, "status": 6})
