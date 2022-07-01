import asyncio
import time
from http import HTTPStatus
from typing import Dict, Union

import aiohttp
from aiohttp import web
from loguru import logger

from .middlewares import request_validation

endpoints = {
    "viacep":           "https://viacep.com.br/ws/{cep}/json/",
    "postmon":          "https://api.postmon.com.br/v1/cep/{cep}",
    "republicavirtual": "https://republicavirtual.com.br/web_cep.php?cep={cep}&formato=json",  # noqa
}


async def handler(request) -> web.Response:
    cep_requested = request.match_info.get("cep")

    tasks = [
        get(name, code.format(cep=cep_requested))
        for name, code in endpoints.items()
    ]

    for task_completed in asyncio.as_completed(tasks):
        cep_info = await task_completed

        # if the first returned value is None
        # continues until get a valid information
        if cep_info is None:
            continue

        return web.json_response(cep_info)

    raise web.HTTPNotFound()


async def get(service_name: str, endpoint: str) -> Dict:
    """Requests the data from given endpoint"""
    start = time.monotonic()
    async with aiohttp.ClientSession() as session:
        response = await session.get(endpoint)

        if response.status == HTTPStatus.OK:
            response_content = await response.json()
            if not false_positive_response(response_content):

                logger.info("{source} took {time}s".format(
                    source=service_name,
                    time=format(time.monotonic() - start, '.3f')
                ))

                return response_parsed(response_content)


def false_positive_response(content: Dict) -> bool:
    """
    Checks if the response is a false positive.
    Some services return a 200 status code with a json with empty values,
    this is a false positive.
    """
    return content.get('uf') is None or len(content.get('uf')) == 0


def response_parsed(content: Dict) -> Union[Dict, None]:
    """Normalize the response content"""
    payload_parsed = {
        'cidade': content.get('localidade', content.get('cidade')),
        'estado': content.get('estado', content.get('uf')),
        'bairro': content.get('bairro'),
        'logradouro': content.get('logradouro'),
        'source': content.get('source')
    }

    # all zip codes have at minimum "state" information
    # if this information is not present on the parsed payload
    # then the zip code requested doesn't exist
    return payload_parsed if payload_parsed.get('estado') else None


server = aiohttp.web.Application(middlewares=[request_validation])
server.add_routes([web.get('/{cep}', handler)])
