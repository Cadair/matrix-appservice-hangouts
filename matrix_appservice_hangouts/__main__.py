"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import asyncio
import logging
from tempfile import NamedTemporaryFile

import click
from aiohttp import web

from matrix_appservice_hangouts.appservice import AppService

logger = logging.getLogger("hangouts_as")
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@click.command()
@click.argument('matrix_server', default="http://localhost:8008")
@click.argument('server_domain', default="localhost")
@click.argument('access_token', default="wfghWEGh3wgWHEf3478sHFWE")
@click.argument('cache_path', default=False)
@click.option('--debug/--no-debug', default=False)
def main(matrix_server, server_domain,
         access_token, cache_path=None,
         debug=False):

    if debug:
        logger.setLevel(logging.DEBUG)

    if not cache_path:
        cache_path = NamedTemporaryFile(delete=True).name

    loop = asyncio.get_event_loop()

    apps = AppService(matrix_server=matrix_server,
                      server_domain=server_domain,
                      access_token=access_token,
                      cache_path=cache_path,
                      loop=loop)

    # Do some setup
    web.run_app(apps.app, host='127.0.0.1', port=5000)

    apps.client_session.close()
    apps.save_cache()
