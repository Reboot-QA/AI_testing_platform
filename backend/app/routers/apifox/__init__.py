from app.routers.apifox.cases import router as cases_router
from app.routers.apifox.data_models import router as data_models_router
from app.routers.apifox.endpoints import router
from app.routers.apifox.variables import router as variables_router

__all__ = ["router", "variables_router", "cases_router", "data_models_router"]
