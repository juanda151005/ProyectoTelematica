class AppError(Exception):
    pass


class NotFoundError(AppError):
    pass


class PermissionDeniedError(AppError):
    pass


class ConflictError(AppError):
    pass
