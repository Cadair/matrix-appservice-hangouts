import asyncio
import logging

from urllib.parse import quote
import aiohttp
from aiohttp import web

from client import MatrixClient
from hangouts_client import HangoutsClient

log = logging.getLogger("hangouts_as")


__all__ = ['AppService']


class AppService:
    """
    Run the Matrix Appservice
    """

    def __init__(self, *, matrix_server, access_token, cookies, conversation_id, loop=None):
        # Set up a async loop
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.client_session = aiohttp.ClientSession(loop=self.loop)
        self.matrix_client = MatrixClient(matrix_server, access_token, self.client_session)
        self.hangouts_client = HangoutsClient(cookies, self.recieve_hangouts_event)
        self.conversation_id = conversation_id
        self.access_token = access_token

        self.app = web.Application(loop=self.loop)
        self.routes()

    def routes(self):
        self.app.router.add_route('PUT', "/transactions/{transaction}",
                                  self.recieve_matrix_transaction)
        self.app.router.add_route('GET', "/rooms/{alias}", self.room_alias)
        self.app.router.add_route('GET', "/users/{userid}", self.query_userid)

    async def recieve_matrix_transaction(self, request):
        json = await request.json()
        events = json["events"]
        for event in events:
            log.info("User: %s Room: %s" % (event["user_id"], event["room_id"]))
            log.info("Event Type: %s" % event["type"])
            log.info("Content: %s" % event["content"])
            if "hangouts" not in event['user_id'] and "m.room.message" in event["type"]:
                resp = await self.hangouts_client.send_message(self.conversation_id,
                                                               event['content']['body'])

        return web.Response(body=b"{}")

    async def recieve_hangouts_event(self, event):
        log.info("Received Message on Hangouts {}".format(event.text))
        resp = await self.matrix_client.send_message("!ItEGspVUZCZOwPiyZY:localhost",
                                                     event.text,
                                                     user_id="@hangouts_test1:localhost")

        return resp

    async def room_alias(self, request):
        alias = request.match_info["alias"]

        rep = await self.matrix_client.create_room(alias)

        return web.Response(body=b"{}")

    async def query_userid(self, request):
        userid = request.match_info["userid"]

        resp = await self.register_user(userid)

        return web.Response(body=b"{}")

    async def register_user(self, localpart):
        """
        Register the user using the AS
        """
        data = self.matrix_client._jsonify({'type': "m.login.application_service",
                                            'username': quote(localpart)})

        resp = await self.matrix_client._send("POST", "register",
                                              api_path=self.matrix_client.room_endpoint,
                                              params=self.matrix_client._token_params(),
                                              data=data)
        return resp
