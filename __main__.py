"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import asyncio
from aiohttp import web
import hangups
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

cookies = hangups.auth.get_auth_stdin('/home/stuart/.cache/hangups/refresh_token.txt')

access_token = "wfghWEGh3wgWHEf3478sHFWE"

loop = asyncio.get_event_loop()

apps = AppService(matrix_server="http://localhost:8008",
                  access_token=access_token,
                  cookies=cookies,
                  conversation_id="UgyuLgNUD268Sv0Si5p4AaABAagBvtJg",
                  loop=loop)

# Do some setup
loop.run_until_complete(apps.hangouts_client.setup())
loop.run_until_complete(apps.register_user("hangouts_test1"))
loop.run_until_complete(apps.matrix_client.create_room("#appservice_hangouts:localhost"))
loop.run_until_complete(apps.matrix_client.join_room("#appservice_hangouts:localhost",
                                                     user_id="@hangouts_test1:localhost"))

loop.run_until_complete(apps.matrix_client.create_room("#hangouts_test1:localhost"))
loop.run_until_complete(apps.matrix_client.join_room("#hangouts_test1:localhost",
                                                     user_id="@hangouts_test1:localhost"))

web.run_app(apps.app, host='127.0.0.1', port=5000)

apps.client_session.close()
