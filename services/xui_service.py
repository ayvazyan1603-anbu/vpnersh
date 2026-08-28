import aiohttp
import uuid
import time
import ssl
import json
import logging
import urllib.parse
import config

logger = logging.getLogger(__name__)

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class XUIService:
    """Сервис для интеграции с 3x-ui панелью."""

    @staticmethod
    def _base_url() -> str:
        return config.XUI_URL.rstrip("/") if config.XUI_URL else ""

    @staticmethod
    def _headers() -> dict:
        return {
            "Authorization": f"Bearer {config.XUI_API_TOKEN}",
            "Content-Type": "application/json",
        }

    @classmethod
    async def create_or_extend_client(cls, user_id: int, days: int) -> dict:
        """
        Создает клиента в 3x-ui панели на инбаундах и формирует рабочий VLESS Reality ключ.
        """
        expire_ms = int((time.time() + days * 86400) * 1000)
        client_id = str(uuid.uuid4())
        email = f"user_{user_id}_{int(time.time())}"
        sub_id = f"sub_{user_id}_{uuid.uuid4().hex[:6]}"

        base = cls._base_url()
        host = config.XUI_HOST or "31.77.182.30"
        port = config.XUI_PORT or 30965

        # Параметры Reality XHTTP инбаунда (Inbound 2 / 3x-ui)
        pbk = "SVjt03ffNHFyBUoMoOX0Xr630b9jkHbO53B3ocpwohA"
        sni = "www.amazon.com"
        sid = "4af065ff"
        spx = urllib.parse.quote("/togFHgkWYcXN8uR")
        fp = "chrome"
        path = urllib.parse.quote("/")
        mode = "auto"
        remark = urllib.parse.quote("🇩🇪 Ersh VPN (XHTTP)")

        vless_link = (
            f"vless://{client_id}@{host}:{port}"
            f"?type=xhttp&security=reality&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx={spx}&path={path}&mode={mode}"
            f"#{remark}"
        )

        if not base or not config.XUI_API_TOKEN:
            logger.info(f"Панель 3x-ui не настроена. Сгенерирован локальный VLESS ключ для user_id={user_id}")
            return {
                "client_id": client_id,
                "email": email,
                "link": vless_link,
                "days": days,
                "is_mock": True
            }

        # Добавляем клиента в панель через API
        payload = {
            "client": {
                "id": client_id,
                "email": email,
                "totalGB": 0,
                "expiryTime": expire_ms,
                "tgId": user_id,
                "subId": sub_id,
                "limitIp": 3,
                "enable": True
            },
            "inboundIds": getattr(config, "XUI_INBOUND_IDS", [config.XUI_INBOUND_ID])
        }

        add_url = f"{base}/panel/api/clients/add"
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(headers=cls._headers()) as session:
                async with session.post(add_url, json=payload, ssl=ssl_ctx, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            logger.info(f"Клиент {email} успешно добавлен в 3x-ui панель.")
                            return {
                                "client_id": client_id,
                                "email": email,
                                "link": vless_link,
                                "days": days,
                                "is_mock": False
                            }
                        else:
                            logger.warning(f"Панель 3x-ui вернула ответ: {data.get('msg')}")
                    else:
                        resp_text = await resp.text()
                        logger.error(f"Ошибка API 3x-ui (код {resp.status}): {resp_text[:200]}")
        except Exception as e:
            logger.error(f"Исключение при обращении к 3x-ui: {e}")

        # Возвращаем ссылку даже при сбое сети, чтобы не ломать сценарий
        return {
            "client_id": client_id,
            "email": email,
            "link": vless_link,
            "days": days,
            "is_mock": True
        }

    @classmethod
    async def delete_client(cls, email_or_id: str) -> bool:
        """Удалить клиента из 3x-ui панели по email или UUID."""
        base = cls._base_url()
        if not base or not config.XUI_API_TOKEN:
            return False

        url = f"{base}/panel/api/clients/del/{email_or_id}"
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(headers=cls._headers()) as session:
                async with session.post(url, ssl=ssl_ctx, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return bool(data.get("success"))
        except Exception as e:
            logger.error(f"Ошибка при удалении клиента {email_or_id}: {e}")
        return False
