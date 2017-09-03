import os.path
import asyncio
import logging
from functools import partial
from urllib.parse import quote

import aiohttp
from aiohttp import web
from bidict import bidict
from ruamel.yaml import YAML

from .matrix_client import MatrixClient
from .hangouts_client import HangoutsClient

log = logging.getLogger("hangouts_as")


__all__ = ['AppService']


class AppService:
    """
    Run the Matrix Appservice
    """

    def __init__(self, *, matrix_server, server_domain, access_token,
                 cache_path=None, loop=None):
        # Set up a async loop
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        # Load Cache
        self.cache_path = cache_path
        self.cache = self.setup_cache()

        # Setup clients
        self.client_session = aiohttp.ClientSession(loop=self.loop)
        self.matrix_client = MatrixClient(matrix_server, access_token, self.client_session)
        self.access_token = access_token
        self.server_name = server_domain
        self.hangouts_clients = {}
        self.login_existing_clients()

        # Keep a list of valid matrix channels and be able to map room_id to alias.
        self.joined_conversations = bidict(self.cache['joined_conversations'])
        # Keep a mapping of matrix users to admin channels
        self.admin_channels = self.cache['admin_channels']

        # Event types mapped to methods
        self._matrix_event_dispatch = {}
        self._matrix_event_dispatch['m.room.message'] = self.matrix_room_message
        self._matrix_event_dispatch['m.room.member'] = self.matrix_room_member

        # Setup web server to listen for appservice calls
        self.app = web.Application(loop=self.loop)
        self.routes()

    async def login_hangouts(self, mxid, refresh_token=None):
        if not refresh_token:
            if mxid in self.cache['ho_tokens']:
                refresh_token = self.cache['ho_tokens'][mxid]
            else:
                raise ValueError("Login Failed, cookies not in cache and no token provided.")

        hangouts_client = await HangoutsClient.init_from_refresh_token(refresh_token,
                                                                       self.recieve_hangouts_event,
                                                                       self.loop,
                                                                       self.client_session)
        self.cache['ho_tokens'][mxid] = hangouts_client.cookies

        self.hangouts_clients[mxid] = hangouts_client

    def login_existing_clients(self):
        for mxid, cookies in self.cache['ho_tokens'].items():
            hangouts_client = HangoutsClient(cookies, self.recieve_hangouts_event)
            # TODO: run this async style
            self.loop.run_until_complete(hangouts_client.setup())
            self.hangouts_clients[mxid] = hangouts_client

    def setup_cache(self):
        if not self.cache_path or not os.path.isfile(self.cache_path):
            cache = {}
        else:
            yaml = YAML()
            cache = yaml.load(open(self.cache_path, 'r'))

        if 'ho_tokens' not in cache:
            cache['ho_tokens'] = {}
        if 'admin_channels' not in cache:
            cache['admin_channels'] = {}
        if 'joined_conversations' not in cache:
            cache['joined_conversations'] = {}

        return cache

    def save_cache(self):
        if self.cache_path:
            self.cache['joined_conversations'] = dict(self.joined_conversations)
            yaml = YAML()
            yaml.dump(self.cache, open(self.cache_path, 'w'))

    def routes(self):
        self.app.router.add_route('PUT', "/transactions/{transaction}",
                                  self.recieve_matrix_transaction)
        self.app.router.add_route('GET', "/rooms/{alias}", self.room_alias)
        self.app.router.add_route('GET', "/users/{userid}", self.query_userid)

    async def join_hangouts_conversation(self, mxid, conversation_id):
        """
        Given a hangouts conversation, perform joining operations.
        """
        log.debug(f"Joining Hangouts Conversation: {conversation_id}")
        # Join the hangouts conversation
        conv = self.hangouts_clients[mxid].get_conversation(conversation_id)

        # Create the room based on conversation ID
        room_alias = f"#hangouts_{conv.id_}:{self.server_name}"
        log.info(f"Creating room: {room_alias}")
        await self.matrix_client.create_room(room_alias)

        room_id = await self.matrix_client.get_room_id(room_alias)

        # Add this conversation to the list
        self.joined_conversations[room_alias] = room_id

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
                                                          user_id=f"@hangouts:{self.server_name}")

        # Register Users
        for user in conv.users:
            if not user.is_self:
                user_id = f"hangouts_{user.id_.gaia_id}"
                resp = await self.register_user(user_id)
                # user_id for join is different to register!
                user_id = f"@{user_id}:{self.server_name}"
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
        events = json["events"]
        for event in events:
            if "hangouts" not in event['user_id']:
                log.debug(
f"""
Received Matrix Transaction:
\t Event: {event['type']},
\t User: {event['user_id']},
\t Room: {event['room_id']},
\t Content: {event['content']}
""")

            meth = self._matrix_event_dispatch.get(event['type'], None)
            if meth:
                try:
                    await meth(event)
                except Exception as e:
                    log.error(str(e))
                    return web.Response(staus=500)

        return web.Response(body=b"{}")

    async def matrix_room_message(self, event):
        """
        Handle 'm.room.message' events.
        """
        # Handle messages
        if "hangouts" not in event['user_id']:
            if event['room_id'] in self.joined_conversations.values():
                ralias = self.joined_conversations.inv[event['room_id']]
                conv_id = ralias[ralias.find("_")+1:ralias.find(':')]
                hangouts_client = self.hangouts_clients[event['user_id']]
                conv = hangouts_client.conversation_list.get(conv_id)
                resp = await hangouts_client.send_message(conv,
                                                          event['content']['body'])
                return resp

            elif event['room_id'] in self.admin_channels.values():
                # Handle admin channel messages
                user_id = event['user_id']
                # Process message
                resp = await self.handle_admin_message(event)

                return resp

    async def matrix_room_member(self, event):
        """
        Handle 'm.room.member' events.
        """
        log.debug("m.room.member")
        content = event['content']
        if content['membership'] == "invite" and content['is_direct']:
            # If we already have an active admin channel with this user, don't
            # join another.
            user_id = event['user_id']
            if user_id not in self.admin_channels.keys():
                self.admin_channels[user_id] = event['room_id']
                resp = await self.matrix_client.join_room(event['room_id'])
            # TODO: test this code path.
            elif user_id not in self.admin_channels.keys() and self.admin_channels[user_id] != event['room_id']:
                resp = await self.matrix_client.join_room(self.admin_channels[user_id])
                resp = await self.matrix_client.invite_user(self.admin_channels[user_id], user_id)
            else:
                resp = await self.matrix_client.send_message(self.admin_channels[user_id], "Hello")

            return resp

    async def handle_admin_message(self, event):
        """
        Process an admin channel message.
        """
        output = "Sorry, I did not understand your message: commands are 'login', 'token:' and 'list conversations'"
        respond = partial(self.matrix_client.send_message, event['room_id'])

        message = event['content']['body']
        if "list conversations" in message:
            if event['user_id'] in self.hangouts_clients:
                convs = self.hangouts_clients[event['user_id']].conversation_list.get_all()
                line_template = "{name}, {uri}\n"
                output = ""
                for conv in convs:
                    name = ''
                    if conv.name:
                        name = conv.name
                    elif len(conv.users) == 2:
                        for user in conv.users:
                            if not user.is_self:
                                name = user.full_name
                    log.info(f"{conv.id_}: {name}")
                    uri = f"#hangouts_{conv.id_}:{self.server_name}"

                    output += line_template.format(name=name, uri=uri)
            else:
                output = "You are not logged in."

        elif "login" in message:
            await respond("Please provide login token by following this: https://www.youtube.com/watch?v=hlDhp-eNLMU video.")
            await respond("Type 'token:' followed by the token to login with the token.")
            output = None
        elif message.startswith("token:"):
            token = message.split("token:")[1]
            refresh_token = token.strip()
            try:
                await self.login_hangouts(event['user_id'], refresh_token=refresh_token)
                output = "Login Successful. Type 'list conversations' to see your conversation list."
            except Exception as e:
                output = "Login failed with error: {}".format(str(e))

        if output:
            await respond(output)

    async def recieve_hangouts_event(self, conv, user, event):
        log.debug(
f"""
Received Hangouts Event:
\t Conversation: {conv.id_},
\t User: {user.full_name} ({user.id_.gaia_id}),
\t Message: {event.text}
""")
        room_alias = f"#hangouts_{conv.id_}:{self.server_name}"
        user_id = f"@hangouts_{user.id_.gaia_id}:{self.server_name}"
        if room_alias in self.joined_conversations:
            resp = await self.matrix_client.send_message(room_alias,
                                                         event.text,
                                                         user_id=user_id)
            return resp
        else:
            log.error("No Room found")

    async def room_alias(self, request):
        alias = request.match_info["alias"]

        conversation_id = alias[alias.find('_')+1:alias.find(':')]
        log.info(f"Room join Request for {conversation_id}")

        for mxid, client in self.hangouts_clients.items():
            try:
                client.conversation_list.get(conversation_id)
                await self.join_hangouts_conversation(mxid, conversation_id)
                break
            except:
                return web.Response(status=404)

        return web.Response(body=b"{}")

        # return web.Response(status=404)

    async def query_userid(self, request):
        return web.Response(status=404)

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
