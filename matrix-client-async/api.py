import json
from time import time

from urllib.parse import quote


class MatrixError(Exception):
    """A generic Matrix error. Specific errors will subclass this."""
    pass


class MatrixUnexpectedResponse(MatrixError):
    """The home server gave an unexpected response. """

    def __init__(self, content=""):
        super(MatrixError, self).__init__(content)
        self.content = content


class MatrixRequestError(MatrixError):
    """ The home server returned an error response. """

    def __init__(self, code=0, content=""):
        super(MatrixRequestError, self).__init__("%d: %s" % (code, content))
        self.code = code
        self.content = content


class AsyncAPI:
    """
    Raw matrix API layer.
    """

    def __init__(self, base_url, client_session, token=None):
        self.session = client_session
        self.token = token
        self.base_url = base_url
        self.txn_id = 0

    async def _send(self,
                    method,
                    path,
                    content=None,
                    query_params={},
                    headers={},
                    api_path="/_matrix/client/api/v1"):
        method = method.upper()
        if method not in ["GET", "PUT", "DELETE", "POST"]:
            raise ValueError("Unsupported HTTP method: %s" % method)

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if self.token:
            query_params["access_token"] = self.token

        endpoint = self.base_url + api_path + path

        if headers["Content-Type"] == "application/json":
            content = json.dumps(content)
        async with self.session.request(
                    method,
                    endpoint,
                    params=query_params,
                    data=content,
                    headers=headers) as resp:

            # if response.status_code == 429:
            #     sleep(response.json()['retry_after_ms'] / 1000)
            # else:
            #     break

            if resp.status < 200 or resp.status >= 300:
                raise MatrixRequestError(code=resp.status, content=await resp.text())

            await resp.read()
            return resp

    async def login(self, login_type, **kwargs):
        """Perform /login.

        Args:
            login_type(str): The value for the 'type' key.
            **kwargs: Additional key/values to add to the JSON submitted.
        """
        content = {"type": login_type, **kwargs}

        return await self._send("POST", "/login", content=content)

    async def join_room(self, room_id_or_alias):
        """Performs /join/$room_id

        Args:
            room_id_or_alias(str): The room ID or room alias to join.
        """
        if not room_id_or_alias:
            raise MatrixError("No alias or room ID to join.")

        path = "/join/%s" % quote(room_id_or_alias)

        return await self._send("POST", path)

    async def send_message_event(self, room_id, event_type, content, txn_id=None):
        """Perform /rooms/$room_id/send/$event_type

        Args:
            room_id(str): The room ID to send the message event in.
            event_type(str): The event type to send.
            content(dict): The JSON content to send.
            txn_id(int): Optional. The transaction ID to use.
        """
        if not txn_id:
            txn_id = str(self.txn_id) + str(int(time() * 1000))

        self.txn_id = self.txn_id + 1

        path = "/rooms/%s/send/%s/%s" % (
            quote(room_id), quote(event_type), quote(str(txn_id)),
        )
        return await self._send("PUT", path, content)

    def get_text_body(self, text, msgtype="m.text"):
        return {
            "msgtype": msgtype,
            "body": text
        }

    async def send_message(self, room_id, text_content, msgtype="m.text"):
        """Perform /rooms/$room_id/send/m.room.message

        Args:
            room_id(str): The room ID to send the event in.
            text_content(str): The m.text body to send.
        """
        return await self.send_message_event(
            room_id, "m.room.message",
            self.get_text_body(text_content, msgtype)
        )
