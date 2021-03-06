import io
import asyncio
import logging

import hangups
from hangups import hangouts_pb2


log = logging.getLogger("hangouts_appservice")


class HangoutsLoginError(Exception):
    """ The home server returned an error response. """

    def __init__(self, message, code=0, content=""):
        super().__init__(f"{message} with code {code} {content}")
        self.code = code
        self.content = content


class HangoutsClient:
    @staticmethod
    async def login(refresh_token, client_session):
        token_request_data = {
            'client_id': hangups.auth.OAUTH2_CLIENT_ID,
            'client_secret': hangups.auth.OAUTH2_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        async with client_session.request("POST",
                                          hangups.auth.OAUTH2_TOKEN_REQUEST_URL,
                                          headers={'user-agent': hangups.auth.USER_AGENT},
                                          data=token_request_data) as resp:
            if not resp.status == 200:
                try:
                    json = await resp.json()
                except Exception:
                    json = ''

                raise HangoutsLoginError("Hangouts login failed.", resp.status, json)

            json = await resp.json()
            access_token = json['access_token']

        headers = {'Authorization': 'Bearer {}'.format(access_token)}
        async with client_session.request("GET",
                    'https://accounts.google.com/accounts/OAuthLogin?source=hangups&issueuberauth=1',
                    headers=headers) as resp:
            uberauth = await resp.text()

        async with client_session.request("GET", ('https://accounts.google.com/MergeSession?'
                                                  'service=mail&'
                                                  'continue=http://www.google.com&uberauth={}')
                                          .format(uberauth), headers=headers) as resp:
            await resp.read()

        # This is insane but it works
        cookies = {}
        for cookie in client_session.cookie_jar:
            cookies[cookie.key] = cookie.value
        filtered = client_session.cookie_jar.filter_cookies('https://google.com')
        cookies2 = {}
        for key in filtered:
            cookies2[key] = cookies[key]

        return cookies2

    @classmethod
    async def init_from_refresh_token(cls,
                                      refresh_token,
                                      recieve_event_handler,
                                      loop,
                                      client_session):
        """
        Login and make a thing
        """
        cookies = await cls.login(refresh_token, client_session)
        client = cls(cookies, recieve_event_handler, loop=loop, client_session=client_session)
        await client.setup()
        await client.get_self()
        return client

    def __init__(self, cookies, recieve_event_handler, loop=None, client_session=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.cookies = cookies
        self.client = hangups.Client(cookies)
        self.http_session = client_session

        self.recieve_event_handler = recieve_event_handler

    async def setup(self):
        """
        Setup stuff that's async
        """
        task = asyncio.ensure_future(self.client.connect())

        # Wait for hangups to either finish connecting or raise an exception.
        on_connect = asyncio.Future()
        self.client.on_connect.add_observer(lambda: on_connect.set_result(None))
        done, _ = await asyncio.wait(
            (on_connect, task), return_when=asyncio.FIRST_COMPLETED
        )
        await asyncio.gather(*done)
        await asyncio.ensure_future(self.get_users_conversations())
        self.conversation_list.on_event.add_observer(self.on_event)

    async def close(self):
        await self.client.disconnect()

    async def get_self(self):
        # Retrieve self entity.
        get_self_info_response = await self.client.get_self_info(
            hangouts_pb2.GetSelfInfoRequest(
                request_header=self.client.get_request_header(),
            )
        )
        user = get_self_info_response.self_entity
        return hangups.user.User.from_entity(user, None)

    async def get_users_conversations(self):
        """
        Get a list of all users and conversations
        """
        user_list, conversation_list = (
            await hangups.build_user_conversation_list(self.client)
            )

        self.user_list = user_list
        self.conversation_list = conversation_list

    def get_conversation(self, conversation_id):
        """
        Return a Conversation object from the list.
        """
        try:
            return self.conversation_list.get(conversation_id)
        except KeyError as e:
            log.debug(e, exc_info=True)
            return

    async def send_message(self, conversation, message):
        """
        Send a message to a conversation.
        """

        cms = hangups.ChatMessageSegment.from_str(message)
        await conversation.send_message(cms)

    async def send_image(self, conversation, image_url, filename):
        async with self.http_session.request("GET", image_url) as resp:
            data = await resp.read()

        image_data = io.BytesIO(data)
        image_id = await self.client.upload_image(image_data, filename=filename)
        return await conversation.send_message([], image_id=image_id)

    async def on_event(self, conv_event):
        """
        Recieve an event.
        """
        conv = self.conversation_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        await self.recieve_event_handler(self, conv, user, conv_event)
