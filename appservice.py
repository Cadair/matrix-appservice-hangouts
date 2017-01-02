# app_service.py:

import json
from urllib.parse import quote
import asyncio
import aiohttp
from aiohttp import web

from client import MatrixClient


class AppService:
    """
    Run the Matrix Appservice
    """

    def __init__(self, *, matrix_server, access_token, loop=None):
        # Set up a async loop
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.client_session = aiohttp.ClientSession(loop=self.loop)
        self.matrix_client = MatrixClient(matrix_server, access_token, self.client_session)
        self.access_token = access_token

        self.app = web.Application(loop=self.loop)
        self.routes()

    def routes(self):
        self.app.router.add_route('PUT', "/transactions/{transaction}",
                                  self.recieve_transaction)
        self.app.router.add_route('GET', "/rooms/{alias}", self.room_alias)
        self.app.router.add_route('GET', "/users/{userid}", self.query_userid)

    async def recieve_transaction(self, request):
        transaction = request.match_info["transaction"]
        json = await request.json()
        events = json["events"]
        for event in events:
            print("User: %s Room: %s" % (event["user_id"], event["room_id"]))
            print("Event Type: %s" % event["type"])
            print("Content: %s" % event["content"])
            if "hangouts" not in event['user_id'] and "m.room.message" in event["type"]:
                resp = await self.matrix_client.send_message(event["room_id"],
                                                             "Hello {user_id}".format(user_id=event['user_id']))

        return web.Response(body=b"{}")

    async def room_alias(self, request):
        alias = request.match_info["alias"]

        rep = await self.matrix_client.create_room(alias)

        return web.Response(body=b"{}")

    async def query_userid(self, request):
        userid = request.match_info["userid"]

        resp = await register_user(userid)

        return web.Response(body=b"{}")

    async def register_user(self, localpart):
        """
        Register the user using the AS
        """
        data = self.matrix_client._jsonify({'type': "m.login.application_service",
                                            'username':quote(localpart)})
        print(data)

        resp = await self.matrix_client._send("POST", "register",
                                              api_path=self.matrix_client.room_endpoint,
                                              params=self.matrix_client._token_params(),
                                              data=data)
        print(resp)
        return resp



if __name__ == "__main__":
    access_token = "wfghWEGh3wgWHEf3478sHFWE"

    loop = asyncio.get_event_loop()

    apps = AppService(matrix_server="http://localhost:8008",
                      access_token=access_token,
                      loop=loop)

    # Do some setup
    loop.run_until_complete(apps.register_user("hangouts_test1"))
    loop.run_until_complete(apps.matrix_client.join_room("#hangouts_test1:localhost",
                                                         user_id="@hangouts_test1"))

    web.run_app(apps.app, host='127.0.0.1', port=5000)

    apps.client_session.close()
