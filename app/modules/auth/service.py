from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.service import UsersService
from app.shared.exceptions import PermissionDeniedError


class AuthService:
    def __init__(self, users_repo: UserRepository):
        self.users_repo = users_repo
        self.users_service = UsersService(users_repo)

    def register(self, username: str, password: str) -> User:
        self.users_service.ensure_username_available(username)
        user = User(username=username, password_hash=hash_password(password))
        return self.users_repo.create(user)

    def login(self, username: str, password: str) -> str:
        user = self.users_repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise PermissionDeniedError('Credenciales inválidas')
        return create_access_token(user.id)
