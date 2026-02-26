from fastapi import APIRouter

router = APIRouter(prefix='/presence', tags=['presence'])

# Router reservado para expansión futura (heartbeat/global presence).
