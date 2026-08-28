import hashlib
import hmac
import time
import logging
import aiohttp
from typing import Optional, Dict, Any
import config

logger = logging.getLogger(__name__)

# Официальные IP-адреса серверов FreeKassa для проверки оповещений
FREEKASSA_IPS = {
    "168.119.157.136",
    "168.119.60.227",
    "178.154.197.79",
    "51.250.54.238"
}


class FreeKassaService:
    """Сервис взаимодействия с FreeKassa SCI и REST API"""

    @staticmethod
    def generate_payment_url(
        order_id: int | str,
        amount: float | int,
        currency: str = "RUB",
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> str:
        """
        Генерация ссылки на оплату через форму FreeKassa SCI.
        Адрес формы: https://pay.fk.money/
        Формула подписи: md5(m:oa:secret_1:currency:o)
        """
        merchant_id = getattr(config, "FK_MERCHANT_ID", "")
        secret_1 = getattr(config, "FK_SECRET_1", "")

        if not merchant_id or not secret_1:
            logger.warning("FreeKassa credentials (FK_MERCHANT_ID / FK_SECRET_1) not configured in config/.env")
            return f"https://pay.fk.money/?m=DEMO&oa={amount:.2f}&o={order_id}&currency={currency}"

        amount_str = f"{amount:.2f}"
        # Подпись платежной формы: ID Магазина:Сумма:Секретное_слово_1:Валюта:Номер_заказа
        raw_sign_str = f"{merchant_id}:{amount_str}:{secret_1}:{currency}:{order_id}"
        signature = hashlib.md5(raw_sign_str.encode("utf-8")).hexdigest()

        url = (
            f"https://pay.fk.money/?"
            f"m={merchant_id}&"
            f"oa={amount_str}&"
            f"o={order_id}&"
            f"s={signature}&"
            f"currency={currency}&"
            f"lang=ru"
        )

        if phone:
            clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
            url += f"&phone={clean_phone}"

        if email:
            url += f"&em={email}"

        return url

    @staticmethod
    def verify_webhook_sign(merchant_id: str, amount: str, order_id: str, sign: str) -> bool:
        """
        Проверка подписи уведомления об оплате от FreeKassa Result URL.
        Формула: md5(MERCHANT_ID:AMOUNT:secret_word_2:MERCHANT_ORDER_ID)
        """
        secret_2 = getattr(config, "FK_SECRET_2", "")
        if not secret_2:
            logger.warning("FK_SECRET_2 is not configured in config/.env")
            return False

        raw_str = f"{merchant_id}:{amount}:{secret_2}:{order_id}"
        expected_sign = hashlib.md5(raw_str.encode("utf-8")).hexdigest()

        return expected_sign.lower() == sign.lower()

    @staticmethod
    async def check_order_status_api(order_id: int | str) -> dict:
        """
        Проверка статуса заказа через официальный REST API FreeKassa.
        Эндпоинт: POST https://api.fk.life/v1/orders
        Статусы заказа:
          0 - Новый
          1 - Оплачен
          6 - Возврат
          8 - Ошибка
          9 - Отмена
        """
        merchant_id = getattr(config, "FK_MERCHANT_ID", "")
        api_key = getattr(config, "FK_API_KEY", "")

        if not merchant_id or not api_key:
            logger.warning("FK_MERCHANT_ID or FK_API_KEY not set for API check")
            return {"status": "unconfigured"}

        url = "https://api.fk.life/v1/orders"
        nonce = int(time.time() * 1000)

        payload = {
            "shopId": int(merchant_id),
            "nonce": nonce,
            "paymentId": str(order_id)
        }

        sorted_keys = sorted(payload.keys())
        sign_raw = "|".join(str(payload[k]) for k in sorted_keys)
        signature = hmac.new(
            api_key.encode("utf-8"),
            sign_raw.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        payload["signature"] = signature

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"FreeKassa API response for order {order_id}: {data}")
                        return data
                    else:
                        err_text = await resp.text()
                        logger.warning(f"FreeKassa API error HTTP {resp.status}: {err_text}")
                        return {"status": "error", "code": resp.status, "text": err_text}
        except Exception as e:
            logger.error(f"FreeKassa API request failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def is_order_paid(cls, order_id: int | str) -> bool:
        """Проверить, оплачен ли заказ через REST API"""
        res = await cls.check_order_status_api(order_id)
        # Если API вернуло статус заказа == 1 (оплачен)
        if isinstance(res, dict):
            # В зависимости от ответа API (status: 1 или type: 'success' / orders item status 1)
            if res.get("status") == 1:
                return True
            orders = res.get("orders") or res.get("data")
            if isinstance(orders, list) and orders:
                if orders[0].get("status") == 1:
                    return True
        return False
