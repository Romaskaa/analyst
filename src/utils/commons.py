import asyncio
import logging
from datetime import datetime, timedelta

from ..settings import timezone

logger = logging.getLogger(__name__)


def current_datetime() -> datetime:
    """Получение текущего времени"""

    return datetime.now(timezone)


def get_expiration_timestamp(expires_in: timedelta) -> int:
    """Получение и расчёт Unix Timestamp для истечения времени"""

    return int((current_datetime() + expires_in).timestamp())


async def run_cli_command(*args):
    """Запускает CLI команду (в терминале)"""

    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    stdout_decoded = stdout.decode().strip()
    stderr_decoded = stderr.decode().strip()

    logger.info("[%s exited with %s]", args[0], process.returncode)
    if stdout_decoded:
        logger.info("[stdout]\n%s", stdout_decoded)
    if stderr_decoded:
        logger.error("[stderr]\n%s", stderr_decoded)

    return process.returncode, stdout_decoded, stderr_decoded
