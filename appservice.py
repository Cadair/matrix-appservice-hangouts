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
        self.conversation_mapping = {}
        self._matrix_event_dispatch = {}
        self._matrix_event_dispatch['m.room.message'] = self.matrix_room_message
        self._matrix_event_dispatch['m.room.member'] = self.matrix_room_member


        self.app = web.Application(loop=self.loop)
        self.routes()

        # TODO: These need to be dynamic
        self.conversation_id = conversation_id

        self.loop.run_until_complete(self.join_hangouts_conversation(self.conversation_id))

    def routes(self):
        self.app.router.add_route('PUT', "/transactions/{transaction}",
                                  self.recieve_matrix_transaction)
        self.app.router.add_route('GET', "/rooms/{alias}", self.room_alias)
        self.app.router.add_route('GET', "/users/{userid}", self.query_userid)

    async def join_hangouts_conversation(self, conversation_id):
        """
        Given a hangouts conversation, perform joining operations.
        """
        # Join the hangouts conversation
        conv = self.hangouts_client.get_conversation(conversation_id)
        conv.on_event.add_observer(self.hangouts_client.on_event)

        # Create the room based on conversation ID
        room_alias = f"#hangouts_{conv.id_}:localhost"
        log.info(f"Creating room: {room_alias}")
        room_id = await self.matrix_client.get_room_id(room_alias)
        await self.matrix_client.create_room(room_alias)

        # Add this conversation to the mapping.
        self.conversation_mapping[room_id] = conv

        # Set the conversation name
        name = None
        if conv.name:
            name = conv.name
        elif len(conv.users) == 2:
            for user in conv.users:
                if not user.is_self:
                    name = user.full_name
        if name:
            resp = await self.matrix_client.set_room_name(room_alias,
                                                          name,
                                                          user_id="@hangouts:localhost")

        # Register Users
        for user in conv.users:
            if not user.is_self:
                user_id = f"hangouts_{user.id_.gaia_id}"
                resp = await self.register_user(user_id)
                # user_id for join is different to register!
                user_id = f"@{user_id}:localhost"
                log.info(f"Creating user: {user_id}")

                # Set the matrix users display name
                await self.matrix_client.set_display_name(user_id, user.full_name)

                # Set the matrix users profile picture (if needed)
                await self.set_matrix_profile_image(user_id, user.photo_url)

                # Join the matrix user to the room
                await self.matrix_client.join_room(room_alias,
                                                   user_id=user_id)

    async def set_matrix_profile_image(self, user_id, image_url, force=False):
        """
        Given a matrix user id and a remote image, download the image from the
        remote source, and upload it to the media store on the homeserver and
        set it as the users avatar url.
        """
        # If we don't have a profile picture already set one
        if force or not await self.matrix_client.get_avatar_url(user_id) and image_url:
            # Download Hangouts profile picture
            async with self.client_session.request("GET", f"https:{image_url}") as resp:
                log.info(resp)
                data = await resp.read()

            # Upload to homeserver
            resp = await self.matrix_client.media_upload(data, resp.content_type,
                                                         user_id=user_id)
            json = await resp.json()
            avatar_url = json['content_uri']

            # Set profile picture
            resp = await self.matrix_client.set_avatar_url(user_id, avatar_url)

            return resp

    async def recieve_matrix_transaction(self, request):
        """
        Receive an Appservice push matrix event.
        """
        json = await request.json()
        log.info(json)
        events = json["events"]
        for event in events:
            log.info("User: %s Room: %s" % (event["user_id"], event["room_id"]))
            log.info("Event Type: %s" % event["type"])
            log.info("Content: %s" % event["content"])

            meth = self._matrix_event_dispatch.get(event['type'], None)
            if meth:
                resp = await meth(event)

        return web.Response(body=b"{}")

    async def matrix_room_message(self, event):
        """
        Handle 'm.room.message' events.
        """
        # Handle messages
        if "hangouts" not in event['user_id'] and event['room_id'] in self.conversation_mapping:
            resp = await self.hangouts_client.send_message(self.conversation_mapping[event['room_id']],
                                                           event['content']['body'])

            return resp

    async def matrix_room_member(self, event):
        """
        Handle 'm.room.member' events.
        """
        content = event['content']
        if content['membership'] == "invite" and content['is_direct']:
            # We have been invited to a private chat. Join it.
            resp = await self.matrix_client.join_room(event['room_id'])

            return resp

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
