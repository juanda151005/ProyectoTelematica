# Import explícito de modelos para registrar metadata.
from app.modules.files.models import FileAttachment  # noqa: F401
from app.modules.groups.models import Group, GroupMember  # noqa: F401
from app.modules.messages.models import Message, MessageReceipt  # noqa: F401
from app.modules.presence.models import UserPresence  # noqa: F401
from app.modules.users.models import User  # noqa: F401
