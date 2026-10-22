from fastapi import APIRouter

from app.api.v1 import (admin, analytics, auth, collections, customers, events, ml,
                        products, recommendations)

api_router = APIRouter()
for module in (auth, products, events, customers, collections, recommendations,
               analytics, ml, admin):
    api_router.include_router(module.router)
