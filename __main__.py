"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import asyncio
from aiohttp import web
import logging

from appservice import AppService

print("Starting...")

logger = logging.getLogger("hangouts_as")
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

access_token = "wfghWEGh3wgWHEf3478sHFWE"

loop = asyncio.get_event_loop()

apps = AppService(matrix_server="http://localhost:8008",
                  server_name="localhost",
                  access_token=access_token,
                  cache_path='./.hangouts_cache.yml',
                  loop=loop)

# Do some setup
web.run_app(apps.app, host='127.0.0.1', port=5000)

apps.client_session.close()
apps.save_cache()
