import asyncio
import time
from typing import Dict

import aiohttp
from aiohttp import web
from loguru import logger

endpoints = {
    "viacep":           "https://viacep.com.br/ws/{cep}/json/",
    "postmon":          "https://api.postmon.com.br/v1/cep/{cep}",
    "republicavirtual": "https://republicavirtual.com.br/web_cep.php?cep={cep}&formato=json",  # noqa
}


async def handler(request):
    cep_requested = request.match_info.get("cep")

    tasks = [
        get(name, code.format(cep=cep_requested))
        for name, code in endpoints.items()
    ]

    for task_completed in asyncio.as_completed(tasks):
        cep_info = await task_completed

        if cep_info is None:
            return web.json_response({}, status=404)

        return web.json_response(cep_info)


async def get(service_name: str, endpoint: str) -> Dict:
    """Requests the data from given endpoint"""
    start = time.monotonic()
    async with aiohttp.ClientSession() as session:
        response = await session.get(endpoint)

        if response.status == 200:
            json_response = await response.json()
            json_response.update({'source': service_name})

            logger.info("{source} is done in {time}s".format(
                source=service_name,
                time=format(time.monotonic() - start, '.3f')
            ))

            return response_parsed(json_response)


def response_parsed(content: Dict) -> Dict:
    """Normalize the response content"""
    return {
        'cidade': content.get('localidade', content.get('cidade')),
        'estado': content.get('estado', content.get('uf')),
        'bairro': content.get('bairro'),
        'logradouro': content.get('logradouro'),
        'source': content.get('source')
    }


if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.get('/{cep}', handler)])
    web.run_app(app)
