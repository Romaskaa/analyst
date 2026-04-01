import aiohttp

STATUS_OK = 200
BATCH_SIZE = 3
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}
