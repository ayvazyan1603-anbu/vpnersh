from aiogram import Router
from .start import router as start_router
from .balance import router as balance_router
from .subscription import router as sub_router
from .promocode import router as promo_router
from .partner import router as partner_router
from .support import router as support_router

user_router = Router()
user_router.include_router(start_router)
user_router.include_router(balance_router)
user_router.include_router(sub_router)
user_router.include_router(promo_router)
user_router.include_router(partner_router)
user_router.include_router(support_router)
