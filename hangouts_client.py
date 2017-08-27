import asyncio
import hangups


class HangoutsClient:
    def __init__(self, cookies, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.client = hangups.Client(cookies)
        task = asyncio.ensure_future(self.client.connect())

        asyncio.wait_for(task, 5)

    async def send_message(self, conversation_id, message):
        request = hangups.hangouts_pb2.SendChatMessageRequest(
            request_header=self.client.get_request_header(),
            event_request_header=hangups.hangouts_pb2.EventRequestHeader(
                conversation_id=hangups.hangouts_pb2.ConversationId(
                    id=conversation_id
                ),
                client_generated_id=self.client.get_client_generated_id(),
            ),
            message_content=hangups.hangouts_pb2.MessageContent(
                segment=[
                    hangups.ChatMessageSegment(message).serialize()
                ],
            ),
        )
        await self.client.send_chat_message(request)
