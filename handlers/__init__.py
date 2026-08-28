from aiogram import Router
from .user import user_router
from .admin import admin_router

main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(user_router)
