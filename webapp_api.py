import sys
import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl
from aiohttp import web

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
from database import db
from services.cryptopay_service import CryptoPayService
from services.freekassa_service import FreeKassaService
from services.xui_service import XUIService
import time

logger = logging.getLogger(__name__)

PERIODS_CONFIG = {
    "1": (30, "price_1_month", "1 месяц"),
    "3": (90, "price_3_months", "3 месяца"),
    "6": (180, "price_6_months", "6 месяцев"),
    "12": (365, "price_12_months", "12 месяцев"),
}

def extract_user_id(request: web.Request):
    # Try X-Telegram-Init-Data
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    if init_data:
        try:
            parsed_data = dict(parse_qsl(init_data))
            if 'user' in parsed_data:
                user_info = json.loads(parsed_data['user'])
                return user_info.get('id')
        except Exception as e:
            logger.error(f"Error parsing initData: {e}")
            pass
            
    # Fallback to X-User-Id
    user_id_str = request.headers.get('X-User-Id')
    if user_id_str and user_id_str.isdigit():
        return int(user_id_str)
        
    return None


@web.middleware
async def auth_middleware(request, handler):
    # Разрешаем все не-API запросы (HTML, CSS, JS, статика, healthcheck)
    if not request.path.startswith('/api/'):
        return await handler(request)
        
    if request.method == 'OPTIONS':
        return await handler(request)

    # Цены могут быть публичными
    if request.path == '/api/prices':
        return await handler(request)
        
    user_id = extract_user_id(request)
    if not user_id:
        response = web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        return add_cors_headers(response)
        
    request['user_id'] = user_id
    return await handler(request)


def add_cors_headers(response: web.Response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


async def handle_options(request):
    return add_cors_headers(web.Response(status=204))


async def handle_root(request):
    index_path = ROOT_DIR / 'webapp' / 'index.html'
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="Ersh VPN WebApp Running", content_type="text/plain")


async def handle_health(request):
    return web.json_response({"status": "ok", "app": "Ersh VPN"})


async def handle_favicon(request):
    return web.Response(status=204)


async def api_user(request):
    user_id = request['user_id']
    user = await db.get_or_create_user(user_id)
    if not user:
        return add_cors_headers(web.json_response({"ok": False, "error": "user_not_found"}, status=404))
        
    username = user.get('username', '')
    full_name = user.get('full_name', '')
    balance = user.get('balance', 0)
    trial_used = bool(user.get('trial_used', 0))
    vpn_key = user.get('vpn_key')
    sub_plan = user.get('sub_plan')
    sub_active_until = user.get('sub_active_until')
    
    # Проверяем активность подписки
    has_active_sub = False
    if sub_active_until:
        try:
            from datetime import datetime
            until_dt = datetime.fromisoformat(sub_active_until)
            has_active_sub = until_dt > datetime.now()
        except Exception:
            pass
    
    # Реферальная статистика
    ref_stats = await db.get_referral_stats(user_id)
    
    bot_username = getattr(config, 'BOT_USERNAME', '') or ''
    referral_link = f"https://t.me/{bot_username}?start=ref{user_id}" if bot_username else f"?start=ref{user_id}"
    
    data = {
        "ok": True,
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "balance": balance,
        "trial_used": trial_used,
        "has_active_sub": has_active_sub,
        "sub_plan": sub_plan if has_active_sub else None,
        "sub_active_until": sub_active_until if has_active_sub else None,
        "vpn_key": vpn_key if has_active_sub else None,
        "referral_count": ref_stats.get("total_invited", 0),
        "referral_active": ref_stats.get("active_referrals", 0),
        "referral_earnings": ref_stats.get("total_earned", 0),
        "referral_link": referral_link
    }
    return add_cors_headers(web.json_response(data))

async def api_prices(request):
    prices = await db.get_prices()
    response_prices = {
        "1": prices.get("price_1_month", 149),
        "3": prices.get("price_3_months", 399),
        "6": prices.get("price_6_months", 749),
        "12": prices.get("price_12_months", 1399),
        "price_1_month": prices.get("price_1_month", 149),
        "price_3_months": prices.get("price_3_months", 399),
        "price_6_months": prices.get("price_6_months", 749),
        "price_12_months": prices.get("price_12_months", 1399),
    }
    return add_cors_headers(web.json_response({"ok": True, "prices": response_prices}))

async def api_trial(request):
    user_id = request['user_id']
    user = await db.get_user(user_id)
    if not user:
         return add_cors_headers(web.json_response({"ok": False, "error": "user_not_found"}))

    if user.get('trial_used'):
        return add_cors_headers(web.json_response({"ok": False, "error": "already_used"}))
        
    trial_days = getattr(config, 'TRIAL_DAYS', 3)
    
    # Создаем клиент в 3x-ui
    vpn_data = await XUIService.create_or_extend_client(user_id, trial_days)
    vpn_link = vpn_data.get("link", "") if isinstance(vpn_data, dict) else str(vpn_data)
    
    # Активируем тестовый период
    active_until = await db.use_trial_subscription(user_id, trial_days, vpn_link)
    if not active_until:
         return add_cors_headers(web.json_response({"ok": False, "error": "already_used"}))
    
    return add_cors_headers(web.json_response({
        "ok": True,
        "active_until": active_until.isoformat() if hasattr(active_until, 'isoformat') else str(active_until),
        "vpn_key": vpn_link
    }))

async def api_deposit(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        amount = int(body.get('amount', 0))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if not (10 <= amount <= 100000):
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_amount"}))
        
    invoice = await CryptoPayService.create_invoice(
        amount_rub=amount,
        description=f"Пополнение баланса пользователя {user_id}",
        payload=f"deposit_{user_id}_{amount}"
    )
    if not invoice:
        return add_cors_headers(web.json_response({"ok": False, "error": "crypto_error"}))
        
    await db.create_db_invoice(
        invoice_id=invoice['invoice_id'],
        user_id=user_id,
        invoice_type="deposit",
        plan_key="",
        days=0,
        amount=amount,
        pay_url=invoice['pay_url']
    )
    
    return add_cors_headers(web.json_response({
        "ok": True,
        "invoice_id": invoice['invoice_id'],
        "pay_url": invoice['pay_url']
    }))

async def api_check_invoice(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        invoice_id = body.get('invoice_id')
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if not invoice_id:
        return add_cors_headers(web.json_response({"ok": False, "error": "missing_invoice_id"}))
        
    is_paid = await CryptoPayService.is_invoice_paid(invoice_id)
    if not is_paid:
        return add_cors_headers(web.json_response({"ok": False, "error": "not_paid"}))
        
    invoice = await db.mark_invoice_paid(invoice_id)
    if not invoice:
        return add_cors_headers(web.json_response({"ok": False, "error": "already_processed"}))
    
    amount = invoice['amount']
    inv_type = invoice['invoice_type']
    
    if inv_type == 'deposit':
        new_balance = await db.update_balance(user_id, amount)
        await db.add_transaction(user_id, 'deposit', amount, 'Пополнение баланса через CryptoBot (WebApp)')
        await db.process_referral_reward_on_payment(user_id, amount)
        return add_cors_headers(web.json_response({"ok": True, "type": "deposit", "new_balance": new_balance}))
        
    elif inv_type == 'subscription':
        plan_key = invoice.get('plan_key', '')
        days = invoice.get('days', 30)
        
        vpn_data = await XUIService.create_or_extend_client(user_id, days)
        vpn_link = vpn_data.get("link", "") if isinstance(vpn_data, dict) else str(vpn_data)
        active_until = await db.activate_subscription(user_id, days, "Стандартный", vpn_link)
        await db.add_transaction(user_id, 'purchase', -amount, f'Покупка тарифа через CryptoBot (WebApp)')
        await db.process_referral_reward_on_payment(user_id, amount)
        
        return add_cors_headers(web.json_response({
            "ok": True, 
            "type": "subscription", 
            "active_until": active_until.isoformat() if hasattr(active_until, 'isoformat') else str(active_until),
            "vpn_key": vpn_link
        }))
        
    return add_cors_headers(web.json_response({"ok": False, "error": "unknown_invoice_type"}))

async def api_buy_with_balance(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        period = str(body.get('period'))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if period not in PERIODS_CONFIG:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_period"}))
        
    days, price_key, plan_name = PERIODS_CONFIG[period]
    prices = await db.get_prices()
    price = int(prices.get(price_key, 0))
    
    user = await db.get_user(user_id)
    if not user:
        return add_cors_headers(web.json_response({"ok": False, "error": "user_not_found"}))
        
    balance = int(user.get('balance', 0))
    if balance < price:
        return add_cors_headers(web.json_response({"ok": False, "error": "insufficient_balance"}))
        
    await db.update_balance(user_id, -price)
    vpn_data = await XUIService.create_or_extend_client(user_id, days)
    vpn_link = vpn_data.get("link", "") if isinstance(vpn_data, dict) else str(vpn_data)
    active_until = await db.activate_subscription(user_id, days, "Стандартный", vpn_link)
    await db.add_transaction(user_id, 'purchase', -price, f'Покупка тарифа «Стандартный» на {plan_name}')
    await db.process_referral_reward_on_payment(user_id, price)
    
    return add_cors_headers(web.json_response({
        "ok": True,
        "active_until": active_until.isoformat() if hasattr(active_until, 'isoformat') else str(active_until),
        "vpn_key": vpn_link
    }))

async def api_buy_with_crypto(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        period = str(body.get('period'))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if period not in PERIODS_CONFIG:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_period"}))
        
    days, price_key, plan_name = PERIODS_CONFIG[period]
    prices = await db.get_prices()
    price = int(prices.get(price_key, 0))
    
    invoice = await CryptoPayService.create_invoice(
        amount_rub=price,
        description=f"Оплата VPN «Стандартный» на {plan_name}",
        payload=f"sub_{user_id}_{period}"
    )
    if not invoice:
        return add_cors_headers(web.json_response({"ok": False, "error": "crypto_error"}))
        
    await db.create_db_invoice(
        invoice_id=invoice['invoice_id'],
        user_id=user_id,
        invoice_type="subscription",
        plan_key="Стандартный",
        days=days,
        amount=price,
        pay_url=invoice['pay_url']
    )
    
    return add_cors_headers(web.json_response({
        "ok": True,
        "invoice_id": invoice['invoice_id'],
        "pay_url": invoice['pay_url']
    }))

async def api_promo(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        code = body.get('code')
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if not code:
        return add_cors_headers(web.json_response({"ok": False, "error": "missing_code"}))
        
    result = await db.activate_promocode(code, user_id)
    if result.get('success'):
        return add_cors_headers(web.json_response({
            "ok": True,
            "reward_desc": result.get('reward_desc', 'Промокод активирован')
        }))
    else:
        return add_cors_headers(web.json_response({
            "ok": False,
            "error": result.get('msg', 'Ошибка активации промокода')
        }))

async def api_tickets(request):
    user_id = request['user_id']
    tickets = await db.get_user_tickets(user_id)
    return add_cors_headers(web.json_response({"ok": True, "tickets": tickets}))

async def api_tickets_create(request):
    user_id = request['user_id']
    try:
        body = await request.json()
        text = body.get('text')
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))
        
    if not text:
        return add_cors_headers(web.json_response({"ok": False, "error": "missing_text"}))
        
    user = await db.get_user(user_id)
    username = user.get('username') if user else None
    full_name = user.get('full_name') if user else None
    
    ticket_id = await db.create_ticket(user_id, username, full_name, text)
    if ticket_id:
        return add_cors_headers(web.json_response({"ok": True, "ticket_id": ticket_id}))
    return add_cors_headers(web.json_response({"ok": False, "error": "create_failed"}))

async def api_transactions(request):
    user_id = request['user_id']
    transactions = await db.get_user_transactions(user_id)
    return add_cors_headers(web.json_response({"ok": True, "transactions": transactions}))


# --- FREEKASSA API & WEBHOOKS ---

async def api_deposit_freekassa(request):
    """Создать счет на пополнение баланса через FreeKassa"""
    user_id = request['user_id']
    try:
        body = await request.json()
        amount = int(body.get('amount', 0))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))

    if not (10 <= amount <= 100000):
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_amount"}))

    order_id = int(time.time() * 1000) % 2147483647
    pay_url = FreeKassaService.generate_payment_url(
        order_id=order_id,
        amount=amount,
        currency="RUB"
    )

    await db.create_db_invoice(
        invoice_id=order_id,
        user_id=user_id,
        invoice_type="deposit",
        plan_key="",
        days=0,
        amount=amount,
        pay_url=pay_url,
        provider="freekassa"
    )

    return add_cors_headers(web.json_response({
        "ok": True,
        "invoice_id": order_id,
        "pay_url": pay_url
    }))


async def api_buy_with_freekassa(request):
    """Создать счет на покупку тарифа напрямую через FreeKassa"""
    user_id = request['user_id']
    try:
        body = await request.json()
        period = str(body.get('period'))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))

    if period not in PERIODS_CONFIG:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_period"}))

    days, price_key, plan_name = PERIODS_CONFIG[period]
    prices = await db.get_prices()
    price = int(prices.get(price_key, 0))

    order_id = int(time.time() * 1000) % 2147483647
    pay_url = FreeKassaService.generate_payment_url(
        order_id=order_id,
        amount=price,
        currency="RUB"
    )

    await db.create_db_invoice(
        invoice_id=order_id,
        user_id=user_id,
        invoice_type="subscription",
        plan_key="Стандартный",
        days=days,
        amount=price,
        pay_url=pay_url,
        provider="freekassa"
    )

    return add_cors_headers(web.json_response({
        "ok": True,
        "invoice_id": order_id,
        "pay_url": pay_url
    }))


async def api_check_fk_invoice(request):
    """Проверить статус оплаты счета FreeKassa через REST API"""
    user_id = request['user_id']
    try:
        body = await request.json()
        invoice_id = int(body.get('invoice_id'))
    except Exception:
        return add_cors_headers(web.json_response({"ok": False, "error": "invalid_data"}))

    db_inv = await db.get_db_invoice(invoice_id)
    if not db_inv:
        return add_cors_headers(web.json_response({"ok": False, "error": "invoice_not_found"}))

    if db_inv["status"] == "paid":
        return add_cors_headers(web.json_response({"ok": True, "status": "paid"}))

    # Проверяем через REST API FreeKassa
    is_paid = await FreeKassaService.is_order_paid(invoice_id)
    if is_paid:
        bot = request.app.get("bot")
        res = await db.process_paid_invoice(invoice_id, bot=bot)
        return add_cors_headers(web.json_response({"ok": True, "status": "paid", "result": res}))

    return add_cors_headers(web.json_response({"ok": False, "error": "not_paid"}))


async def freekassa_result_handler(request: web.Request) -> web.Response:
    """
    Обработчик входящих уведомлений от FreeKassa Result URL.
    Формула подписи: md5(MERCHANT_ID:AMOUNT:secret_word_2:MERCHANT_ORDER_ID)
    """
    try:
        if request.method == "POST":
            data = await request.post()
        else:
            data = request.query

        merchant_id = str(data.get("MERCHANT_ID", "")).strip()
        amount = str(data.get("AMOUNT", "")).strip()
        order_id_str = str(data.get("MERCHANT_ORDER_ID", "")).strip()
        sign = str(data.get("SIGN", "")).strip()

        logger.info(f"Received FreeKassa notification: order={order_id_str}, amount={amount}, sign={sign}")

        # Проверка доступности/пинг от панели FreeKassa
        if not order_id_str or not sign:
            logger.info("Received FreeKassa healthcheck ping -> returning YES")
            return web.Response(text="YES", status=200)

        # Валидация цифровой подписи
        is_valid = FreeKassaService.verify_webhook_sign(
            merchant_id=merchant_id,
            amount=amount,
            order_id=order_id_str,
            sign=sign
        )

        if not is_valid:
            logger.warning(f"Invalid FreeKassa signature for order {order_id_str}")
            return web.Response(text="BAD SIGN", status=400)

        order_id = int(order_id_str)
        bot = request.app.get("bot")
        await db.process_paid_invoice(order_id, bot=bot)
        logger.info(f"FreeKassa order #{order_id} successfully processed")

        return web.Response(text="YES", status=200)

    except Exception as e:
        logger.error(f"Error processing FreeKassa webhook: {e}")
        return web.Response(text="ERROR", status=500)


def get_html_page(title: str, icon: str, heading: str, text: str, is_success: bool = True) -> str:
    bot_user = getattr(config, 'BOT_USERNAME', '') or 'ErshVPN_bot'
    color = "#22c55e" if is_success else "#ef4444"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <title>{title} — Ersh VPN</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0a0d16;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .card {{
            background: rgba(18, 24, 38, 0.95);
            border-radius: 20px;
            padding: 40px 30px;
            text-align: center;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .icon {{
            font-size: 56px;
            margin-bottom: 16px;
        }}
        h1 {{
            font-size: 22px;
            margin: 0 0 12px;
            color: {color};
            font-weight: 800;
        }}
        p {{
            font-size: 14px;
            line-height: 1.6;
            color: #94a3b8;
            margin: 0 0 24px;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #06b6d4, #3b82f6);
            color: #ffffff;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 15px;
            box-shadow: 0 8px 20px rgba(6, 182, 212, 0.3);
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <h1>{heading}</h1>
        <p>{text}</p>
        <a href="https://t.me/{bot_user}" class="btn">Вернуться в Telegram</a>
    </div>
    <script>
        setTimeout(() => {{
            window.location.href = "https://t.me/{bot_user}";
        }}, 3000);
    </script>
</body>
</html>"""


async def success_page_handler(request: web.Request) -> web.Response:
    html_content = get_html_page(
        title="Оплата успешна",
        icon="✅",
        heading="Оплата успешно завершена!",
        text="Средства зачислены или подписка активирована. Вернитесь в Telegram-бот для использования VPN.",
        is_success=True
    )
    return web.Response(text=html_content, content_type="text/html")


async def fail_page_handler(request: web.Request) -> web.Response:
    html_content = get_html_page(
        title="Оплата отменена",
        icon="❌",
        heading="Оплата не выполнена",
        text="Платеж был отменен или произошла ошибка. Вы можете повторить попытку в боте.",
        is_success=False
    )
    return web.Response(text=html_content, content_type="text/html")


def setup_routes(app):
    webapp_dir = ROOT_DIR / 'webapp'

    # Базовые маршруты для проверки работоспособности Railway и прямого открытия
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/healthcheck', handle_health)
    app.router.add_get('/favicon.ico', handle_favicon)

    # FreeKassa Webhooks и страницы
    app.router.add_post('/freekassa/result', freekassa_result_handler)
    app.router.add_get('/freekassa/result', freekassa_result_handler)
    app.router.add_post('/webhook/freekassa', freekassa_result_handler)
    app.router.add_get('/webhook/freekassa', freekassa_result_handler)
    app.router.add_get('/success', success_page_handler)
    app.router.add_post('/success', success_page_handler)
    app.router.add_get('/fail', fail_page_handler)
    app.router.add_post('/fail', fail_page_handler)

    routes = [
        ('GET', '/api/user', api_user),
        ('GET', '/api/prices', api_prices),
        ('POST', '/api/trial', api_trial),
        ('POST', '/api/deposit', api_deposit),
        ('POST', '/api/deposit_freekassa', api_deposit_freekassa),
        ('POST', '/api/check_invoice', api_check_invoice),
        ('POST', '/api/check_fk_invoice', api_check_fk_invoice),
        ('POST', '/api/buy_with_balance', api_buy_with_balance),
        ('POST', '/api/buy_with_crypto', api_buy_with_crypto),
        ('POST', '/api/buy_with_freekassa', api_buy_with_freekassa),
        ('POST', '/api/promo', api_promo),
        ('GET', '/api/tickets', api_tickets),
        ('POST', '/api/tickets', api_tickets_create),
        ('GET', '/api/transactions', api_transactions),
    ]

    for method, path, handler in routes:
        app.router.add_route(method, path, handler)
        
    paths = {path for _, path, _ in routes}
    for path in paths:
        app.router.add_route('OPTIONS', path, handle_options)

    # Статические файлы Mini App
    if webapp_dir.exists():
        app.router.add_static('/webapp/', webapp_dir, name='webapp')
        # Для случаев когда файлы запрашиваются из корня (/style.css, /app.js и т.д.)
        app.router.add_static('/', webapp_dir, name='webapp_root')


async def start_webapp_server(bot=None):
    app = web.Application(middlewares=[auth_middleware])
    if bot:
        app['bot'] = bot
    setup_routes(app)
    
    # Если задан WEBAPP_PORT или PORT, используем его
    port_val = os.environ.get('WEBAPP_PORT') or os.environ.get('PORT') or str(getattr(config, 'WEBAPP_PORT', 8080))
    port = int(port_val)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"WebApp server started on port {port}")
    return app
