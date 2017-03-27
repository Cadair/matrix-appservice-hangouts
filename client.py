import json
from urllib.parse import urljoin, quote


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

        async with self.session.request(method, url, **kwargs) as resp:
            await resp.read()
            return resp

    def _get_text_body(self, text, msgtype="m.text"):
        data = {"msgtype": msgtype,
                "body": text}
        return self._jsonify(data)

    def _as_uid(self, uid):
        return {'user_id': quote(uid)}

    def _token_params(self):
        return {"access_token": self.access_token}

    async def send_message(self, room_id, message, user_id=None):
        """
        Send message
        """
        room_id = quote(room_id)
        event_type = quote("m.room.message")

        path = f"rooms/{room_id}/send/{event_type}"
        message = self._get_text_body(message)

        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))

        resp = await self._send("POST", path, api_path=self.room_endpoint,
                                data=message, params=p)
        return resp

    async def get_room_id(self, room_alias):
        room_alias = quote(room_alias)
        resp = self._send("GET", f"directory/room/{room_alias}",
                          api_path=self.room_endpoint)
        return resp

    async def join_room(self, room_alias, user_id=None):
        room_alias = quote(room_alias)
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))

        resp = await self._send("POST", f"join/{room_alias}",
                                api_path=self.room_endpoint,
                                params=p)
        print(resp, await resp.read())
        return resp

    async def create_room(self, alias_name):
        """
        """
        alias_localpart = alias_name.split(":")[0][1:]
        endpoint = f"createRoom"

        content = self._jsonify({"room_alias_name": alias_localpart})
        print(type(content), content)

        resp = await self._send("POST", endpoint,
                                api_path=self.room_endpoint,
                                data=content, params=self._token_params())
        return resp
