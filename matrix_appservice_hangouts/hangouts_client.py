import asyncio
import logging

import hangups


log = logging.getLogger("hangouts_as")


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
        client = cls(cookies, recieve_event_handler, loop=loop)
        await client.setup()
        return client

    def __init__(self, cookies, recieve_event_handler, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.cookies = cookies
        self.client = hangups.Client(cookies)

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
        # self.conversation_list.on_event.add_observer(self.on_event)

    async def close(self):
        await self.client.disconnect()

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
        return self.conversation_list.get(conversation_id)

    async def send_message(self, conversation, message):
        """
        Send a message to a conversation.
        """

        cms = hangups.ChatMessageSegment.from_str(message)
        await conversation.send_message(cms)

    async def on_event(self, conv_event):
        """
        Recieve an event.
        """
        conv = self.conversation_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        if not user.is_self:
            await self.recieve_event_handler(conv, user, conv_event)
