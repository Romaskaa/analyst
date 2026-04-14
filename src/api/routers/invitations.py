import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status

from ...schemas import InvitationCreate
from ...services.invitation import InvitationService
from ..dependencies import get_invitation_service

router = APIRouter(prefix="/invitations", tags=["Приглашения"])
logger = logging.getLogger(__name__)


async def _send_invitation_with_logging(service: InvitationService, email: str) -> None:
    try:
        await service.invite(email=email)
    except Exception:
        logger.exception("Background invitation task failed for email=%s", email)


@router.post(path="", status_code=status.HTTP_202_ACCEPTED, summary="Отправка приглашения")
async def send_invitation(
    data: InvitationCreate,
    background_tasks: BackgroundTasks,
    service: InvitationService = Depends(get_invitation_service),
) -> dict[str, str]:
    background_tasks.add_task(
        _send_invitation_with_logging,
        service=service,
        email=data.email,
    )
    return {"message": "Приглашение будет отправлено в ближайшее время"}
