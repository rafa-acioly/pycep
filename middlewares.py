from aiohttp.web import middleware
from aiohttp import web

MIN_CEP_LENGTH = 8


@middleware
async def request_validation(request, handler):
    cep_length = len(request.match_info.get("cep"))

    if not cep_length == MIN_CEP_LENGTH:
        error_message = 'cep length should be exactly 8, given {l}'.format(l=cep_length)  # noqa
        raise web.HTTPBadRequest(reason=error_message)

    return await handler(request)


@web.middleware
async def error_middleware(request, handler):
    try:
        await handler(request)
    except web.HTTPException as error:
        return web.json({'error': error.text}, status=error.status_code)
