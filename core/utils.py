from typing import Dict
from ipaddress import AddressValueError, IPv4Address
from decouple import Config, RepositoryEnv
from fastapi import (
    Request,
    APIRouter,
)
from redis import Redis


DOTENV_FILE = '.env'
ENV_CONFIG = Config(RepositoryEnv(DOTENV_FILE))


REDIS = Redis(
    host=ENV_CONFIG('redis_host'),
    port=int(ENV_CONFIG('redis_port')),
    password=ENV_CONFIG('redis_password'),
    db=int(ENV_CONFIG('redis_db'))
)


def fetch_request_info(request: Request) -> Dict:
    try:
        ip = IPv4Address(request.headers['x-real-ip'])
    except AddressValueError:
        ip = IPv4Address('127.0.0.1')
    except KeyError:
        ip = IPv4Address('0.0.0.0')

    try:
        http_user_agent = request.headers['user-agent']
    except KeyError:
        http_user_agent = ''

    try:
        request_id = request.headers['x-request-id']
    except KeyError:
        request_id = ''

    try:
        host = request.headers['x-host']
    except KeyError:
        host = ''

    return {
        'ip': ip,
        'http_user_agent': http_user_agent,
        'request_id': request_id,
        'host': host,
    }
