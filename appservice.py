# app_service.py:

import json
from functools import partial
from urllib.parse import urljoin
import asyncio
import aiohttp
from aiohttp import web

from client import MatrixClient

ACCESS_TOKEN = "wfghWEGh3wgWHEf3478sHFWE"



async def recieve_transaction(request, matrix_client=None):
    transaction = request.match_info["transaction"]
    print(f"got request {request}")
    json = await request.json()
    events = json["events"]
    for event in events:
        print("User: %s Room: %s" % (event["user_id"], event["room_id"]))
        print("Event Type: %s" % event["type"])
        print("Content: %s" % event["content"])
    if "logging" not in event['user_id']:
        client.send_message(event["room_id"], "Hello World")

    return web.Response(body=b"{}")


async def room_alias(request):
    alias = request.match_info["alias"]
    print(f"Recieved request {alias}")
    alias_localpart = alias.split(":")[0][1:]
    endpoint = f"/createRoom?access_token={ACCESS_TOKEN}"

    content = json.dumps({"room_alias_name": alias_localpart})

    rep = client._post(endpoint, content, client.v1_endpoint)

    return web.Response(body=b"{}")


def query_userid(request):
    userid = request.match_info["userid"]
    print(f"Revieved {userid}")

    return web.Response(body=b"{}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    client = MatrixClient("http://localhost:8008", ACCESS_TOKEN, session)

    app = web.Application(loop=loop)
    app.router.add_route('PUT', "/transactions/{transaction}",
                         partial(recieve_transaction, matrix_client=client))
    app.router.add_route('GET', "/rooms/{alias}", room_alias)
    app.router.add_route('GET', "/users/{userid}", query_userid)


    client.join_room("#logged_test1:localhost")
    web.run_app(app, host='127.0.0.1', port=5000)

