# app_service.py:

import json
from functools import partial
from urllib.parse import urljoin
import asyncio
import aiohttp
from aiohttp import web

from client import MatrixClient

ACCESS_TOKEN = "wfghWEGh3wgWHEf3478sHFWE"


async def recieve_transaction(request, *, matrix_client):
    transaction = request.match_info["transaction"]
    print(f"got request {request}")
    json = await request.json()
    events = json["events"]
    for event in events:
        print("User: %s Room: %s" % (event["user_id"], event["room_id"]))
        print("Event Type: %s" % event["type"])
        print("Content: %s" % event["content"])
        if "logging" not in event['user_id'] and "m.room.message" in event["type"]:
            resp = await client.send_message(event["room_id"], "Hello World")
            print(resp)

    return web.Response(body=b"{}")


async def room_alias(request):
    alias = request.match_info["alias"]
    print(f"Recieved request {alias}")

    rep = await client.create_room(alias)

    return web.Response(body=b"{}")


async def query_userid(request, *, matrix_client):
    userid = request.match_info["userid"]
    print(f"Revieved {userid}")

    resp = await register_user(userid, matrix_client)

    return web.Response(body=b"{}")


async def register_user(localpart, matrix_client):
    """
    Register the user using the AS
    """
    params = {"access_token": ACCESS_TOKEN}
    data = matrix_client._jsonify({'type': "m.login.application_service", 'username':localpart})

    resp = await matrix_client._send("POST", "register", api_path=matrix_client.room_endpoint,
                                     params=params, data=data)
    async with resp as r:
        return r



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    client = MatrixClient("http://localhost:8008", ACCESS_TOKEN, session)

    app = web.Application(loop=loop)
    app.router.add_route('PUT', "/transactions/{transaction}",
                         partial(recieve_transaction, matrix_client=client))
    app.router.add_route('GET', "/rooms/{alias}", room_alias)
    app.router.add_route('GET', "/users/{userid}",
                         partial(query_userid, matrix_client=client))


    # TODO: These need to be fed though the event loop:
    asyncio.ensure_future(register_user("hangouts_test1", matrix_client=client))
    client.join_room("#hangouts_test1:localhost")

    web.run_app(app, host='127.0.0.1', port=5000)

