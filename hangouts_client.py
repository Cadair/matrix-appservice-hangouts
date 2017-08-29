import asyncio
import logging

import hangups


log = logging.getLogger("hangouts_as")


class HangoutsClient:
    def __init__(self, cookies, recieve_event_handler, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.client = hangups.Client(cookies)

        self.loop.run_until_complete(self.setup())

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
