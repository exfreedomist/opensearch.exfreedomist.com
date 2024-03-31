import logging
import json
import httpx

from decouple import Config, RepositoryEnv
from fastapi.responses import HTMLResponse
from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi import Form
from user_agents import parse

from core.utils import REDIS


router = APIRouter(tags=["search"])
templates = Jinja2Templates(directory="templates")

DOTENV_FILE = '.env'
ENV_CONFIG = Config(RepositoryEnv(DOTENV_FILE))
TOKEN = ENV_CONFIG("token")
REDIS_EX = int(ENV_CONFIG("redis_ex_sec"))
REDIS_EX_CACHE = int(ENV_CONFIG("redis_ex_cache_sec"))

# API:
API_SEARCH_POST = ENV_CONFIG("search_post")
API_SEARCH_COUNT = ENV_CONFIG("search_count")
API_BOARD = ENV_CONFIG("board")
API_MAGNET = ENV_CONFIG("magnet")

# Status map:
STATUS_TRANSLATE_MAP = {
    '√': '✅ (проверено)',
    '#': '⚠️ (сомнительно)',
    '*': '*️⃣ (не проверено)',
    'T': '🕠 (временная)',
    '?': '❓ (недооформлено)',
    '∑': '✝️ (поглощено)',
    '!': '❗️(не оформлено)',
    'D': '🔘 (повтор)',
    'x': '❌️ (закрыто)',
    '∏': '♿️ (проверяется)',
}


def is_restricted(user_agent: str) -> bool:
    parsed_ua = parse(user_agent)
    return parsed_ua.is_bot


def is_mobile(user_agent: str) -> bool:
    parsed_ua = parse(user_agent)
    return parsed_ua.is_mobile or parsed_ua.is_tablet


@router.post("/", response_class=HTMLResponse)
async def search_do(
    request: Request,
    query: str = Form(None),
    offset: int = Form(0),
    order_by: str = Form(None)
):
    if order_by is None:
        order_by = 'd'

    if query is None:
        return templates.TemplateResponse("search/search.html", {
            'request': request,
            'is_mobile': 'user-agent' in request.headers and is_mobile(request.headers['user-agent']),
            'order_by': order_by,
            'static_prefix': ENV_CONFIG('static_prefix'),
        }, status_code=200)

    logging.info("Query: %s", query)

    if 'user-agent' in request.headers and is_restricted(request.headers['user-agent']):
        return templates.TemplateResponse("search/dummy.html", {
            'request': request,
            'static_prefix': ENV_CONFIG('static_prefix'),
        }, status_code=403)

    if offset < 0:
        offset = 0

    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.post(
                API_SEARCH_POST,
                content=json.dumps({
                    'query': query,
                    'offset': offset,
                    'order_by': order_by,
                    'token': TOKEN
                })
            )
            resp.raise_for_status()

            resp_count = await client.post(
                API_SEARCH_COUNT,
                content=json.dumps({
                    'query': query,
                    'offset': offset,
                    'order_by': order_by,
                    'token': TOKEN
                })
            )
            resp_count.raise_for_status()

        except Exception as e:
            print(f'[Search do] Error: {str(e)}')
            return templates.TemplateResponse("search/search.html", {
                'request': request,
                'order_by': order_by,
                'has_error': True,
                'static_prefix': ENV_CONFIG('static_prefix'),
            }, status_code=200)

    __resp_json, __resp_count_json = resp.json(), resp_count.json()
    data, stats = __resp_json['data'], __resp_count_json['size']
    logging.info("Query response size: %d", stats)

    tmpl = "search/search_res.html"
    if 'user-agent' in request.headers and is_mobile(request.headers['user-agent']):
        tmpl = "search/search_res_m.html"

    response_code = 200 if data is not None and len(data) > 0 else 404

    async with httpx.AsyncClient(verify=False) as client:
        for item in data:
            item["status"] = STATUS_TRANSLATE_MAP.get(item["status"], "")
            item['query'] = query

            # fetch label board for all items:
            label_key = f'open_search_board_{item["board_id"]}_{item["tracker"]}'
            label = REDIS.get(label_key)
            if label is None:
                try:
                    resp = await client.get(
                        f'{API_BOARD}/{item["board_id"]}?tracker={item["tracker"]}'
                    )
                    resp.raise_for_status()
                except:
                    label = 'Неизвестная категория'
                else:
                    _data = resp.json()
                    REDIS.set(
                        label_key,
                        json.dumps(
                            {
                                "label": _data["board_label"]
                            }
                        ),
                        ex=REDIS_EX
                    )
                    label = _data["board_label"]
            else:
                label = json.loads(label)["label"]

            item['board_label'] = label
            REDIS.set(
                f'open_search_m{item["magnet_key"]}',
                json.dumps(item),
                ex=REDIS_EX_CACHE
            )

    return templates.TemplateResponse(tmpl, {
        'request': request,
        'status_code': response_code,
        'query': query,
        'stats': stats,
        'offset': offset,
        'order_by': order_by,
        'data': data,
        'int': int,
        'referer': '/search',
        'static_prefix': ENV_CONFIG('static_prefix'),
    }, status_code=response_code)


def _infohash_from_magnet(magnet_link: str) -> str:
    try:
        return magnet_link.split(':btih:')[-1].split('&')[0]
    except IndexError:
        return ''


@router.get("/magnet", response_class=HTMLResponse)
async def magnet(request: Request, key: str):
    if 'user-agent' in request.headers and is_restricted(request.headers['user-agent']):
        return templates.TemplateResponse("search/dummy.html", {
            'request': request,
            'static_prefix': ENV_CONFIG('static_prefix'),
        }, status_code=403)

    cached_info = REDIS.get(
        f'open_search_m{key}',
    )
    if cached_info is None:
        return templates.TemplateResponse("search/search.html", {
            'request': request,
            'has_error': True,
            'order_by': 'd',
            'static_prefix': ENV_CONFIG('static_prefix'),
        }, status_code=200)

    cached_info_d = json.loads(cached_info)

    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.get(
                f'{API_MAGNET}/{key}?token={TOKEN}',
            )
            resp.raise_for_status()
        except Exception as e:
            logging.warning('Failure for magnet %s: %s', key, str(e))
            return templates.TemplateResponse("search/search.html", {
                'request': request,
                'has_error': True,
                'order_by': 'd',
                'static_prefix': ENV_CONFIG('static_prefix'),
            }, status_code=200)

        if resp.status_code != 200 or len(resp.json()['data']['magnet_link']) == 0:
            logging.warning('Empty for magnet %s.', key)
            return templates.TemplateResponse("search/search.html", {
                'request': request,
                'has_error': True,
                'order_by': 'd',
                'static_prefix': ENV_CONFIG('static_prefix'),
            }, status_code=200)

    data = resp.json()['data']
    query, tracker_id, topic_id = cached_info_d['query'], '', 0

    return templates.TemplateResponse("search/magnet.html", {
        'request': request,
        'is_mobile': 'user-agent' in request.headers and is_mobile(request.headers['user-agent']),
        'data': data,
        'cached': cached_info_d,
        'len': len,
        'magnet_click': '',
        'tracker_id': tracker_id,
        'referer': '/magnet',
        'static_prefix': ENV_CONFIG('static_prefix'),
    }, status_code=200)


@router.get("/", response_class=HTMLResponse)
async def search(request: Request):
    if 'user-agent' in request.headers and is_restricted(request.headers['user-agent']):
        return templates.TemplateResponse("search/dummy.html", {
            'request': request,
            'static_prefix': ENV_CONFIG('static_prefix'),
        }, status_code=403)

    return templates.TemplateResponse("search/search.html", {
        'request': request,
        'is_mobile': 'user-agent' in request.headers and is_mobile(request.headers['user-agent']),
        'order_by': 'd',
        'static_prefix': ENV_CONFIG('static_prefix'),
    }, status_code=200)
