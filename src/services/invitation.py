import logging
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.entities import Invitation
from ..core.errors import EmailSendingFailedError
from ..database.repos import InvitationRepository
from ..settings import INVITATION_EXPIRES_IN_DAYS, settings
from ..utils.commons import current_datetime
from ..utils.mail import send_mail

INVITATION_TEXT = (
    "Здравствуйте!\n\n"
    "Вас пригласили присоединиться к системе \n"
    "Перейдите по ссылке для завершения регистрации:\n{invite_url}\n\n"
    "Ссылка действительна {expires_in_days} дней.\n\n"
    "С уважением,\nКоманда {app_name}"
)

logger = logging.getLogger(__name__)


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invitation_repo = InvitationRepository(session)

    async def invite(
        self,
        email: str,
    ) -> Invitation:
        """Приглашает пользователя в систему через отправку письма"""

        invitation = await self.invitation_repo.find_active_by_email(email)
        if invitation is None:
            invitation = Invitation(
                email=email,
                expires_at=current_datetime() + timedelta(days=INVITATION_EXPIRES_IN_DAYS),
            )  # type: ignore  # noqa: PGH003
        invite_url = f"{settings.frontend_url}/auth/invite/accept?token={invitation.token}"
        context = {
            "email": email,
            "invite_url": invite_url,
            "expires_in_days": INVITATION_EXPIRES_IN_DAYS,
            "app_name": settings.app.name,
            "support_email": settings.mail.support_email,
        }
        try:
            await self.invitation_repo.create(invitation)
            await send_mail(
                to=invitation.email,
                subject="Приглашение в систему",
                plain_text=INVITATION_TEXT.format(**context),
                template_name="email/invitation.html",
                context=context,
            )
            await self.session.commit()
        except EmailSendingFailedError:
            logger.exception("Email sending failed")
            await self.session.rollback()
        logger.info("Invitation sent: %s", email)
        return invitation
