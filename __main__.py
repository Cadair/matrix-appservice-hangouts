"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import asyncio
import aiohttp
from aiohttp import web

from appservice import AppService

access_token = "wfghWEGh3wgWHEf3478sHFWE"

loop = asyncio.get_event_loop()

apps = AppService(matrix_server="http://localhost:8008",
                    access_token=access_token,
                    loop=loop)

# Do some setup
loop.run_until_complete(apps.register_user("hangouts_test1"))
loop.run_until_complete(apps.matrix_client.join_room("#hangouts_test1:localhost",
                                                     user_id="@hangouts_test1:localhost"))

web.run_app(apps.app, host='127.0.0.1', port=5000)

apps.client_session.close()
