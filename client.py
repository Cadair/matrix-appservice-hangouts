import json
import os.path
from time import time
from urllib.parse import urljoin, quote

import requests
import aiohttp



BASE_URL = "http://localhost:8008"
API_ENDPOINT = "_matrix/client/api/v1/"


class MatrixClient:
    """
    A client to talk to a matrix server.
    """
    def __init__(self, base_url, access_token, client_session):
        self.access_token = access_token
        self.base_url = base_url
        self.session = client_session

        self.v1_endpoint = "_matrix/client/api/v1/"
        self.room_endpoint = "_matrix/client/r0/"


    def _get_url(self, endpoint, api_endpoint):
        end = urljoin(api_endpoint, endpoint)
        target = urljoin(BASE_URL, end)
        return target

    def _jsonify(self, adict):
        return json.dumps(adict).encode()

    async def _send(self, method, endpoint, *, api_path=None, **kwargs):
        """
        Send a HTTP Request

        Parameters
        ----------

        method : `str`
            The HTTP method.

        endpoint : `str`
            Endpoint

        api_path : `str` (optional)
            Endpoint, defaults to `MatrixClient.v1_endpoint`.
        """
        if not api_path:
            api_path = self.v1_endpoint

        url = self._get_url(endpoint, api_path)

        return self.session.request(method, url, **kwargs)

    def _get_text_body(self, text, msgtype="m.text"):
        data = {"msgtype": msgtype,
                "body": text}
        return self._jsonify(data)

    async def send_message(self, room_id, message):
        """
        Send message
        """
        transaction = quote(str(int(time() * 1000)))
        room_id = quote(room_id)
        event_type = quote("m.room.message")

        path = f"rooms/{room_id}/send/{event_type}?access_token={self.access_token}"
        message = self._get_text_body(message)

        resp = await self._send("POST", path, api_path=self.room_endpoint, data=message)
        async with resp as r:
            return r

    async def get_room_id(self, room_alias):
        room_alias = quote(room_alias)
        resp = self._send("GET", f"directory/room/{room_alias}", api_path=self.room_endpoint)
        async with resp as r:
            return r

    async def join_room(self, room_alias):
        room_alias = quote(room_alias)
        resp = await self._send("POST", f"join/{room_alias}?access_token={self.access_token}",
                                api_path=self.room_endpoint)
        async with resp as r:
            return r

    async def create_room(self, alias_name):
        """
        """
        alias_localpart = alias_name.split(":")[0][1:]
        endpoint = f"createRoom?access_token={self.access_token}"

        content = self._jsonify({"room_alias_name": alias_localpart})
        print(type(content), content)

        resp = await self._send("POST", endpoint,
                                api_path=self.room_endpoint, data=content)
        with resp as r:
            return r
