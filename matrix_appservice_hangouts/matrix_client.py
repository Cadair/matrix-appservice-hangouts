import json
import logging
from urllib.parse import urljoin, quote


log = logging.getLogger("hangouts_as")
BASE_URL = "http://localhost:8008"


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

        if resp.status != 200:
            log.error(resp)
            log.error(await resp.json())

        return resp

    async def send_state_event(self, room_id, event_type, content, state_key="",
                               timestamp=None, params=None, **kwargs):
        """Perform PUT /rooms/$room_id/state/$event_type
        Args:
            room_id(str): The room ID to send the state event in.
            event_type(str): The state event type to send.
            content(dict): The JSON content to send.
            state_key(str): Optional. The state key for the event.
            timestamp(int): Optional. Set origin_server_ts (For application services only)
        """
        path = "rooms/%s/state/%s" % (
            quote(room_id), quote(event_type),
        )
        if state_key:
            path += "/%s" % (quote(state_key))

        if not params:
            params = {}

        if timestamp:
            params["ts"] = timestamp

        resp = await self._send("PUT", path, data=content, params=params, **kwargs)
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
        if room_id.startswith('#'):
            room_id = await self.get_room_id(room_id)
        else:
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
        resp = await self._send("GET", f"directory/room/{room_alias}",
                                api_path=self.room_endpoint)
        json = await resp.json()
        if 'room_id' in json:
            return json['room_id']

    async def join_room(self, room_alias, user_id=None, access_token=True):
        room_alias = quote(room_alias)
        if access_token:
            p = self._token_params()
        else:
            p = {}
        if user_id:
            p.update(self._as_uid(user_id))


        resp = await self._send("POST", f"join/{room_alias}",
                                api_path=self.room_endpoint,
                                params=p)
        return resp

    async def create_room(self, alias_name, invitees=None):
        """
        """
        alias_localpart = alias_name.split(":")[0][1:]
        endpoint = f"createRoom"

        content = {"room_alias_name": alias_localpart}
        if invitees:
            content["invite"] = invitees
        content = self._jsonify(content)

        resp = await self._send("POST", endpoint,
                                api_path=self.room_endpoint,
                                data=content, params=self._token_params())
        return resp

    async def invite_user(self, room_id, user_id):
        """Perform POST /rooms/$room_id/invite
        Args:
            room_id(str): The room ID
            user_id(str): The user ID of the invitee
        """
        body = {
            "user_id": user_id
        }
        resp = await self._send("POST", f"rooms/{room_id}/invite", data=body)
        return resp

    async def set_display_name(self, user_id, display_name):
        user_id = quote(user_id)
        content = self._jsonify({"displayname": display_name})

        p = self._token_params()
        p.update(self._as_uid(user_id))

        resp = await self._send("PUT",
                                f"profile/{user_id}/displayname",
                                data=content,
                                params=p)
        return resp

    async def set_avatar_url(self, user_id, avatar_url):
        user_id = quote(user_id)
        content = self._jsonify({"avatar_url": avatar_url})

        p = self._token_params()
        p.update(self._as_uid(user_id))

        resp = await self._send("PUT",
                                f"profile/{user_id}/avatar_url",
                                data=content,
                                params=p)
        return resp

    async def get_avatar_url(self, user_id):
        user_id = quote(user_id)
        resp = await self._send("GET", f"profile/{user_id}/avatar_url")
        content = await resp.json()
        return content.get('avatar_url', None)

    def media_upload(self, content, content_type, user_id=None):
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))
        return self._send(
            "POST", "",
            data=content,
            headers={"Content-Type": content_type},
            params=p,
            api_path="/_matrix/media/r0/upload"
        )

    async def set_room_name(self, room_id, name, user_id):
        """Perform PUT /rooms/$room_id/state/m.room.name
        Args:
            room_id(str): The room ID
            name(str): The new room name
            timestamp(int): Optional. Set origin_server_ts (For application services only)
        """
        if room_id.startswith('#'):
            room_id = await self.get_room_id(room_id)
        body = self._jsonify({
            "name": name
        })
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))
        resp = await self.send_state_event(room_id, "m.room.name", body, params=p)
        return resp

    async def get_room_members(self, room_id, user_id=None):
        """Get the list of members for this room.
        Args:
            room_id (str): The room to get the member events for.
        """
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))
        resp  = await self._send("GET", "rooms/{}/members".format(quote(room_id)), params=p)
        return await resp.json()

    async def get_room_members(self, room_id, user_id=None):
        """Get the list of members for this room.
        Args:
            room_id (str): The room to get the member events for.
        """
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))
        resp  = await self._send("GET", "rooms/{}/members".format(quote(room_id)), params=p)
        return await resp.json()

    async def joined_rooms(self, user_id):
        p = self._token_params()
        if user_id:
            p.update(self._as_uid(user_id))
        resp  = await self._send("GET", "joined_rooms", params=p)
        return await resp.json()
