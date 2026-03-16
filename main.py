import logging

import uvicorn

from src.api.app import create_fastapi_app

app = create_fastapi_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")  # noqa: S104
