from api import AsyncAPI


import asyncio
import aiohttp


loop = asyncio.get_event_loop()


client_session = aiohttp.ClientSession(loop=loop)
api = AsyncAPI("http://localhost:8008", client_session)


async def run():
    resp = await api.login("m.login.password", user="apebot", password="apebot")
    r = await resp.json()
    api.token = r['access_token']

    resp = await api.join_room("#apebot2:localhost")
    room_id = await resp.json()
    room_id = room_id['room_id']
    print(room_id)
    resp = await api.send_message(room_id, "hello")

try:
    loop.run_until_complete(run())
finally:
    client_session.close()
