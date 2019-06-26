import asyncio
import time
from typing import Dict

import requests
from flask import Flask, jsonify
from loguru import logger

application = Flask(__name__)
loop = asyncio.new_event_loop()

endpoints = {
    "viacep":           "https://viacep.com.br/ws/{cep}/json/",
    "postmon":          "https://api.postmon.com.br/v1/cep/{cep}",
    "republicavirtual": "https://republicavirtual.com.br/web_cep.php?cep={cep}&formato=json",  # noqa
}


@application.route("/<string:cep>")
def main(cep):
    tasks = [
        get(name, code.format(cep=cep))
        for name, code in endpoints.items()
    ]

    done, pendings = loop.run_until_complete(
        asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    )

    for completed in done:
        return jsonify(completed.result())


async def get(name: str, cep: str) -> Dict:
    """Requests the data from given endpoint"""
    start = time.monotonic()
    response = requests.get(cep)

    if response.status_code == 200:
        json_response = response.json()
        json_response.update({'source': name})

        logger.info("{source} is done in {time}s".format(
            source=name,
            time=format(time.monotonic() - start, '.3f')
        ))

        return parse(json_response)


def parse(content: Dict) -> Dict:
    """Normalize the response content"""
    return {
        'cidade': content.get('localidade', content.get('cidade')),
        'estado': content.get('estado', content.get('uf')),
        'bairro': content.get('bairro'),
        'logradouro': content.get('logradouro'),
        'source': content.get('source')
    }


if __name__ == "__main__":
    application.run(debug=False, use_reloader=False)
