from urllib.parse import urlparse
import logging
from json import JSONDecodeError
from aiohttp import ClientSession
from extruct.jsonld import JsonLdExtractor  # type: ignore  # noqa: PGH003

logger = logging.getLogger(__name__)



def parse_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def get_json_ld(html: str) -> list:
    jslde = JsonLdExtractor()
    try:
        return jslde.extract(html)
    except (JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Не удалось распарсить JSON-LD из HTML: %s", exc)
        return []


async def get_llms_data(url: str) -> str:
    url = parse_url(url)
    async with (
        ClientSession() as session,
        session.get(f"{url}/llms.txt", ssl=False) as data,
    ):
        try:
            result = await data.text()
            return result if "html" not in result else ""  # noqa: TRY300
        except:  # noqa: E722
            return ""


async def get_robots_data(url: str) -> str:
    url = parse_url(url)
    async with (
        ClientSession() as session,
        session.get(f"{url}/robots.txt", ssl=False) as data,
    ):
        try:
            result = await data.text()
            return result if "html" not in result else ""  # noqa: TRY300
        except:  # noqa: E722
            return ""
