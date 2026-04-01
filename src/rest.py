from aiohttp import ClientSession

YANDEX_BASE_URL = "https://api-metrika.yandex.net"


async def get_meter_number(oauth_token: str) -> str:
    async with (
        ClientSession(base_url=YANDEX_BASE_URL) as session,
        session.get(
            url="/management/v1/counters",
            headers={"Authorization": f"OAuth {oauth_token}"},
        ) as response,
    ):
        response.raise_for_status()
        result = await response.json()
        return result["counters"][0]["id"]


async def get_number_of_visits(
    oauth_token: str, meter_number: str, date_start: str, date_stop: str
) -> list:
    async with (
        ClientSession(base_url=YANDEX_BASE_URL) as session,
        session.get(
            url=f"/stat/v1/data?ids={meter_number}&metrics=ym:s:pageviews&dimensions=ym:s:pageUrl&date1={date_start}&date2={date_stop}&oauth_token={oauth_token}",
        ) as response,
    ):
        response.raise_for_status()
        result = await response.json()
        return result["data"]


async def get_search_queries(
    oauth_token: str, meter_number: str, date_start: str, date_stop: str
) -> list:
    async with (
        ClientSession(base_url=YANDEX_BASE_URL) as session,
        session.get(
            url=f"/stat/v1/data.get?id={meter_number}&metrics=ym:s:visits&dimensions=ym:s:search_phrase&date1={date_start}&date2={date_stop}&oauth_token={oauth_token}",
        ) as response,
    ):
        response.raise_for_status()
        result = await response.json()
        return result["data"]


async def get_embeddings(texts: list[str]):
    async with (
        ClientSession() as session,
        session.post("/embeddings", json={"texts": texts}) as response,
    ):
        response.raise_for_status()
        result = await response.json()
        return result["embeddings"]
