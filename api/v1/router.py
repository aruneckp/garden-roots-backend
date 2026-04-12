from fastapi import APIRouter
from api.v1.endpoints import products, stock, orders, payments, locations, admin, auth, users, delivery, config

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(config.router)
api_router.include_router(products.router)
api_router.include_router(stock.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(locations.router)
api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(delivery.router)
