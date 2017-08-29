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
        self.access_token = access_token

        self.app = web.Application(loop=self.loop)
        self.routes()

        # TODO: These need to be dynamic
        self.conversation_id = conversation_id
        self.matrix_room_alias = "#hangouts_test1:localhost"

        self.loop.run_until_complete(self.join_hangouts_conversation(self.conversation_id, self.matrix_room_alias))

    def routes(self):
        self.app.router.add_route('PUT', "/transactions/{transaction}",
                                  self.recieve_matrix_transaction)
        self.app.router.add_route('GET', "/rooms/{alias}", self.room_alias)
        self.app.router.add_route('GET', "/users/{userid}", self.query_userid)

    async def join_hangouts_conversation(self, conversation_id, matrix_room_alias):
        """
        Given a hangouts conversation and a matrix room, perform joining operations.
        """
        # Ensure given matrix room exists.
        await self.matrix_client.create_room(matrix_room_alias)

        # Join the hangouts conversation
        self.hangouts_conversation = self.hangouts_client.get_conversation(conversation_id)
        conv = self.hangouts_conversation
        conv.on_event.add_observer(self.hangouts_client.on_event)

        log.info(dir(conv))
        log.info(conv.name)

        name = None
        if conv.name:
            name = conv.name
        elif len(conv.users) == 2:
            for user in conv.users:
                if not user.is_self:
                    name = user.full_name

        room_alias = f"#hangouts_{conv.id_}:localhost"
        log.info(f"Creating room: {room_alias}")
        await self.matrix_client.create_room(room_alias)
        if name:
            resp = await self.matrix_client.set_room_name(room_alias, name, user_id="@hangouts:localhost")
            log.info(resp)
            log.info(await resp.json())

        for user in conv.users:
            if not user.is_self:
                user_id = f"hangouts_{user.id_.gaia_id}"
                resp = await self.register_user(user_id)
                # user_id for join is different to register!
                user_id = f"@{user_id}:localhost"
                log.info(f"Creating user: {user_id}")
                await self.matrix_client.set_display_name(user_id, user.full_name)

                # If we don't have a profile picture already set one
                if not await self.matrix_client.get_avatar_url(user_id):
                    # Download Hangouts profile picture
                    async with self.client_session.request("GET", f"https:{user.photo_url}") as resp:
                        log.info(resp)
                        data = await resp.read()

                    # Upload to homeserver
                    resp = await self.matrix_client.media_upload(data, resp.content_type,
                                                                 user_id=user_id)
                    json = await resp.json()
                    avatar_url = json['content_uri']

                    # Set profile picture
                    await self.matrix_client.set_avatar_url(user_id, avatar_url)

                await self.matrix_client.join_room(room_alias,
                                                   user_id=user_id)

    async def recieve_matrix_transaction(self, request):
        json = await request.json()
        # log.info("Received AS Transaction: \n{}\n".format(json))
        events = json["events"]
        for event in events:
            log.info("User: %s Room: %s" % (event["user_id"], event["room_id"]))
            log.info("Event Type: %s" % event["type"])
            log.info("Content: %s" % event["content"])
            if "hangouts" not in event['user_id'] and "m.room.message" in event["type"]:
                resp = await self.hangouts_client.send_message(self.hangouts_conversation,
                                                               event['content']['body'])

        return web.Response(body=b"{}")

    async def recieve_hangouts_event(self, conv, user, event):
        log.info("Received Message on Hangouts: '{}'".format(event.text))
        room_alias = f"#hangouts_{conv.id_}:localhost"
        user_id = f"@hangouts_{user.id_.gaia_id}:localhost"
        log.info(room_alias)
        log.info(user_id)
        room_id = await self.matrix_client.get_room_id(room_alias)
        resp = await self.matrix_client.send_message(room_id,
                                                     event.text,
                                                     user_id=user_id)

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
        data = self.matrix_client._jsonify({
            'type':
            "m.login.application_service",
            'username':
            quote(localpart)
        })

        resp = await self.matrix_client._send(
            "POST",
            "register",
            api_path=self.matrix_client.room_endpoint,
            params=self.matrix_client._token_params(),
            data=data)
        return resp
