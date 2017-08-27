"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import asyncio
import aiohttp
from aiohttp import web
import hangups

from appservice import AppService

cookies = hangups.auth.get_auth_stdin('/home/stuart/.cache/hangups/refresh_token.txt')

access_token = "wfghWEGh3wgWHEf3478sHFWE"

loop = asyncio.get_event_loop()

apps = AppService(matrix_server="http://localhost:8008",
                  access_token=access_token,
                  cookies=cookies,
                  conversation_id="UgyuLgNUD268Sv0Si5p4AaABAagBvtJg",
                  loop=loop)


async def conv_list(client):
    user_list, conversation_list = (
        await hangups.build_user_conversation_list(client)
        )
    all_users = user_list.get_all()
    all_conversations = conversation_list.get_all(include_archived=True)

    print('{} known users'.format(len(all_users)))
    for user in all_users:
        print('    {}: {}'.format(user.full_name, user.id_.gaia_id))

    print('{} known conversations'.format(len(all_conversations)))
    for conversation in all_conversations:
        if conversation.name:
            name = conversation.name
        else:
            name = 'Unnamed conversation ({})'.format(conversation.id_)
    print('    {}'.format(name))

# loop.run_until_complete(conv_list(hang.client))

# loop.run_until_complete(hang.send_message("UgyuLgNUD268Sv0Si5p4AaABAagBvtJg", "hello"))
# Do some setup
loop.run_until_complete(apps.register_user("hangouts_test1"))
loop.run_until_complete(apps.matrix_client.create_room("#hangouts_test1:localhost"))
loop.run_until_complete(apps.matrix_client.join_room("#hangouts_test1:localhost",
                                                     user_id="@hangouts_test1:localhost"))

web.run_app(apps.app, host='127.0.0.1', port=5000)

apps.client_session.close()
