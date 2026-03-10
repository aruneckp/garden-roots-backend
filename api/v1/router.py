from fastapi import APIRouter
from api.v1.endpoints import products, stock, orders, payments, locations

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(products.router)
api_router.include_router(stock.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(locations.router)
