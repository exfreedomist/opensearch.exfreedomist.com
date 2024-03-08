import argparse
import logging
import sys

import uvicorn
from decouple import config
from fastapi import (
    FastAPI,
    Request,
)
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from core.open_search import router as search_router


arg_parser = argparse.ArgumentParser(
    description="opensearch.exfreedomist.com engine",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
arg_parser.add_argument("-p", "--port", dest="port", default="31337", help="Port.")
arg_parser.add_argument("-l", "--listen", dest="listen_host", default="127.0.0.1", help="Listen host.")
arg_parser.add_argument("-g", "--debug", dest="debug", action="store_true", help="Debug mode.")
ARGS = arg_parser.parse_args()


if ARGS.debug:
    app = FastAPI()
else:
    app = FastAPI(docs_url=None, redoc_url=None)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)
app.include_router(search_router)


templates = Jinja2Templates(directory="templates")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


@app.exception_handler(405)
async def not_allowed_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse('https://search.exfreedomist.com')


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse('https://search.exfreedomist.com')


@app.exception_handler(500)
async def internal_error_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("search/search_error.html", {
        'request': request,
        'order_by': 'd',
        'static_prefix': config('static_prefix'),
    }, status_code=500)


@app.exception_handler(422)
async def unprocessable_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("search/search_error.html", {
        'request': request,
        'order_by': 'd',
        'static_prefix': config('static_prefix'),
    }, status_code=422)


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=ARGS.listen_host,
        port=int(ARGS.port)
    )
