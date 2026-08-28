import aiohttp
import logging
from typing import Optional, Dict, Any
import config

logger = logging.getLogger(__name__)


class CryptoPayService:
    """Сервис взаимодействия с CryptoPay (@CryptoBot) API"""

    @staticmethod
    def _base_url() -> str:
        if getattr(config, "CRYPTO_BOT_NET", "mainnet") == "testnet":
            return "https://testnet-pay.crypt.bot/api"
        return "https://pay.crypt.bot/api"

    @staticmethod
    def _headers() -> dict:
        return {
            "Crypto-Pay-API-Token": config.CRYPTO_BOT_TOKEN,
            "Content-Type": "application/json"
        }

    @classmethod
    async def create_invoice(
        cls,
        amount_rub: int | float,
        description: str,
        payload: str = "",
        expires_in: int = 3600
    ) -> Optional[dict]:
        """
        Создать счет на оплату в рублях (конвертируется в USDT/TON/BTC при оплате).
        """
        if not config.CRYPTO_BOT_TOKEN:
            logger.error("CRYPTO_BOT_TOKEN не задан!")
            return None

        url = f"{cls._base_url()}/createInvoice"
        data = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": amount_rub,
            "description": description,
            "payload": payload,
            "expires_in": expires_in
        }

        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(headers=cls._headers()) as session:
                async with session.post(url, json=data, timeout=timeout) as resp:
                    res = await resp.json()
                    if resp.status == 200 and res.get("ok"):
                        inv = res["result"]
                        return {
                            "invoice_id": inv["invoice_id"],
                            "pay_url": inv.get("bot_invoice_url") or inv.get("pay_url"),
                            "mini_app_url": inv.get("mini_app_invoice_url"),
                            "amount": inv["amount"],
                            "status": inv["status"],
                            "payload": inv.get("payload")
                        }
                    else:
                        logger.error(f"CryptoPay API createInvoice error: {res}")
        except Exception as e:
            logger.error(f"CryptoPay API request failed: {e}")
        return None

    @classmethod
    async def get_invoice(cls, invoice_id: int) -> Optional[dict]:
        """Получить статус счета по ID"""
        if not config.CRYPTO_BOT_TOKEN:
            return None

        url = f"{cls._base_url()}/getInvoices?invoice_ids={invoice_id}"
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(headers=cls._headers()) as session:
                async with session.get(url, timeout=timeout) as resp:
                    res = await resp.json()
                    if resp.status == 200 and res.get("ok"):
                        items = res.get("result", {}).get("items", [])
                        if items:
                            return items[0]
                    else:
                        logger.error(f"CryptoPay API getInvoices error: {res}")
        except Exception as e:
            logger.error(f"CryptoPay API get_invoice failed: {e}")
        return None

    @classmethod
    async def is_invoice_paid(cls, invoice_id: int) -> bool:
        """Проверить, оплачен ли счет"""
        inv = await cls.get_invoice(invoice_id)
        if inv and inv.get("status") == "paid":
            return True
        return False
