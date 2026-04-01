from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, status

router_metrika = APIRouter()


@router_metrika.get("/least/visited", status_code=status.HTTP_200_OK)
async def get_least_visited() -> dict:
    today = datetime.now(UTC).date()
    one_month_ago = today - relativedelta(months=1)

    return {}
