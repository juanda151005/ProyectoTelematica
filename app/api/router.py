from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.files.router import router as files_router
from app.modules.groups.router import router as groups_router
from app.modules.messages.router import router as messages_router
from app.modules.presence.router import router as presence_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(groups_router)
api_router.include_router(messages_router)
api_router.include_router(files_router)
api_router.include_router(users_router)
api_router.include_router(presence_router)
