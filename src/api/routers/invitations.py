from fastapi import APIRouter, BackgroundTasks, Depends, status

from ...schemas import InvitationCreate
from ...services.invitation import InvitationService
from ..dependencies import get_invitation_service

router = APIRouter(prefix="/invitations", tags=["Приглашения"])


@router.post(path="", status_code=status.HTTP_202_ACCEPTED, summary="Отправка приглашения")
async def send_invitation(
    data: InvitationCreate,
    background_tasks: BackgroundTasks,
    service: InvitationService = Depends(get_invitation_service),
) -> dict[str, str]:
    background_tasks.add_task(
        service.invite,
        email=data.email,
    )
    return {"message": "Приглашение будет отправлено в ближайшее время"}
