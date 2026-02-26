from app.modules.presence.models import UserPresence
from app.modules.presence.repository import PresenceRepository


class PresenceService:
    def __init__(self, repo: PresenceRepository):
        self.repo = repo

    def get_or_create(self, user_id):
        presence = self.repo.get(user_id)
        if presence:
            return presence
        presence = UserPresence(user_id=user_id)
        return self.repo.save(presence)

    def set_online(self, user_id):
        presence = self.get_or_create(user_id)
        presence.mark_online()
        return self.repo.save(presence)

    def set_offline(self, user_id):
        presence = self.get_or_create(user_id)
        presence.mark_offline()
        return self.repo.save(presence)
