"""
Generic client for the industry-standard "SMM API v2" protocol used by
JAP-compatible panels (JAP, SMMcost, most nakrutka providers).
Docs example: https://justanotherpanel.com/api
"""
import aiohttp

from config import SMM_PANEL_API_URL, SMM_PANEL_API_KEY


class SmmPanelError(Exception):
    pass


async def _post(payload: dict) -> dict:
    data = {"key": SMM_PANEL_API_KEY, **payload}
    async with aiohttp.ClientSession() as session:
        async with session.post(SMM_PANEL_API_URL, data=data, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            result = await resp.json(content_type=None)
            if isinstance(result, dict) and "error" in result:
                raise SmmPanelError(result["error"])
            return result


async def get_balance() -> dict:
    return await _post({"action": "balance"})


async def get_services() -> list[dict]:
    """Returns the full upstream catalogue: [{service, name, category, rate, min, max}, ...]"""
    return await _post({"action": "services"})


async def add_order(service_id: int, link: str, quantity: int, extra: dict | None = None) -> int:
    payload = {"action": "add", "service": service_id, "link": link, "quantity": quantity}
    if extra:
        payload.update(extra)
    result = await _post(payload)
    return int(result["order"])


async def get_status(order_id: str) -> dict:
    """Returns {charge, start_count, status, remains, currency}"""
    return await _post({"action": "status", "order": order_id})


async def multi_status(order_ids: list[str]) -> dict:
    return await _post({"action": "status", "orders": ",".join(order_ids)})


async def cancel_order(order_id: str):
    return await _post({"action": "cancel", "order": order_id})
