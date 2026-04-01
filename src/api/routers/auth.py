from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ...schemas import TokensPair, UserCreateForm
from ...services.auth import AuthService
from ..dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    path="/register/{token}",
    status_code=status.HTTP_201_CREATED,
    response_model=TokensPair,
    summary="Регистрация пользователя по приглашению",
)
async def register(
    token: str,
    data: UserCreateForm,
    service: AuthService = Depends(get_auth_service),
) -> TokensPair:
    return await service.register(token, data)


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=TokensPair,
    summary="Войти в учётную запись",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthService = Depends(get_auth_service),
) -> TokensPair:
    return await service.authenticate(form_data.username, form_data.password)
