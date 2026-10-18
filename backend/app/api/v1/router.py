from fastapi import APIRouter
from app.api.v1.routes import health, market, geo, concierge, data_collection

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(geo.router, prefix="/geo", tags=["geo"])
api_router.include_router(concierge.router, prefix="/concierge", tags=["concierge"])

api_router.include_router(data_collection.router, prefix="/data-collection", tags=["data-collection"])
