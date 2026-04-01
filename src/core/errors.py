from fastapi import status


class AppError(Exception):
    """Базовая ошибка приложения - от него наследуются все доменные исключения"""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    public_message: str = "Внутренняя ошибка сервера"

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict | list | None = None,
    ):
        self.message = message or self.public_message
        self.status_code = status_code or self.status_code
        self.error_code = error_code or self.error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    public_message = "Ресурс не найден"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    public_message = "Недостаточно прав"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    public_message = "Требуется авторизация"


class EmailSendingFailedError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EMAIL_SENDING_FAILED"
    public_message = "Не удалось отправить письмо. Попробуйте позже."


class InvitationExpiredError(AppError):
    status_code = status.HTTP_410_GONE
    error_code = "INVITATION_EXPIRED"
    public_message = "Приглашение было использовано или его срок действия истёк"


class UserAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "USER_ALREADY_EXISTS"
    public_message = "Пользователь с таким email уже существует"


class InvariantViolationError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "INVARIANT_VIOLATION"
    public_message = "Нарушены условия существования объекта"


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    error_code = "FILE_TOO_LARGE"
    public_message = "Размер файла превышает установленное ограничение на сервере"


class DBError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DB_SERVER_ERROR"
    public_message = "Произошла ошибка на сервере с базой данных"
