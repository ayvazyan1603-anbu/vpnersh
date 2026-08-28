import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8898632185:AAEjeyDm6luvEt4jnmgQYJKCWKBCvNBBmlA")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# WebApp Mini App
WEBAPP_PORT = int(str(os.getenv("WEBAPP_PORT", os.getenv("PORT", "8443"))).strip('"\''))
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip('"\'').rstrip("/")

# Admins & Channels
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip() and x.strip().isdigit()]
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "tigranayvvv").lstrip("@")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@Ershvpn").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/Ershvpn").strip()

# CryptoBot (CryptoPay)
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "627391:AACFdT0506tYHsif59YA9y3r1ZoswLvLBSU")
CRYPTO_BOT_NET = os.getenv("CRYPTO_BOT_NET", "mainnet")

# FreeKassa (Карты МИР/Visa/Mastercard, СБП, кошельки)
FK_MERCHANT_ID = os.getenv("FK_MERCHANT_ID", "").strip('"\'')
FK_SECRET_1 = os.getenv("FK_SECRET_1", "").strip('"\'')
FK_SECRET_2 = os.getenv("FK_SECRET_2", "").strip('"\'')
FK_API_KEY = os.getenv("FK_API_KEY", "").strip('"\'')

# Tariffs & Prices (in RUB)
PRICE_STANDARD_1_MONTH = int(os.getenv("PRICE_STANDARD_1_MONTH", "149"))
PRICE_STANDARD_3_MONTHS = int(os.getenv("PRICE_STANDARD_3_MONTHS", "399"))
PRICE_STANDARD_6_MONTHS = int(os.getenv("PRICE_STANDARD_6_MONTHS", "749"))
PRICE_STANDARD_12_MONTHS = int(os.getenv("PRICE_STANDARD_12_MONTHS", "1399"))

# Subscription Settings
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "3"))
REFERRAL_BONUS_RUB = int(os.getenv("REFERRAL_BONUS_RUB", "10"))
REFERRAL_PERCENT = int(os.getenv("REFERRAL_PERCENT", "0"))

# 3x-ui / X-UI Panel credentials
XUI_URL = os.getenv("XUI_URL", "https://31.77.182.30:6767/ersh/").rstrip("/")
XUI_USERNAME = os.getenv("XUI_USERNAME", "Maraboy23")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "Bor345@55@")
XUI_API_TOKEN = os.getenv("XUI_API_TOKEN", "MO2m5okHOIPhEIvYCe47exj7Vfc8S3An1G6RpDeOTQatvf1x")
XUI_HOST = os.getenv("XUI_HOST", "31.77.182.30")
XUI_PORT = int(os.getenv("XUI_PORT", "30965"))
XUI_INBOUND_ID = int(os.getenv("XUI_INBOUND_ID", "2"))
XUI_INBOUND_IDS = [int(x.strip()) for x in os.getenv("XUI_INBOUND_IDS", "1,2,3").split(",") if x.strip() and x.strip().isdigit()]
XUI_SUB_URL = os.getenv("XUI_SUB_URL", "https://31.77.182.30:2096/sub/").rstrip("/") + "/"
