from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.enums import UserStatus
from app.shared.exceptions import ConflictError, NotFoundError


class UsersService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id):
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuario no encontrado')
        return user

    def ensure_username_available(self, username: str) -> None:
        existing = self.repo.get_by_username(username)
        if existing:
            raise ConflictError('El username ya existe')

    def set_status(self, user: User, status: UserStatus) -> User:
        user.status = status
        return self.repo.update(user)
