"""Authentication error envelopes."""

from __future__ import annotations

from app.core.errors import ApiError

_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


class EmailAlreadyRegistered(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="email_already_registered",
            message="Этот email уже зарегистрирован.",
        )


class InvalidCredentials(ApiError):
    """Deliberately identical for unknown email and wrong password."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="invalid_credentials",
            message="Неверный email или пароль.",
            headers=_BEARER_CHALLENGE,
        )


class InvalidToken(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="invalid_token",
            message="Сессия недействительна или истекла.",
            headers=_BEARER_CHALLENGE,
        )


class AccountDisabled(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="account_disabled",
            message="Аккаунт отключён.",
        )


class TokenExpired(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="token_expired",
            message="Срок действия токена истёк.",
        )


class TokenAlreadyUsed(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="token_already_used",
            message="Токен уже был использован.",
        )
