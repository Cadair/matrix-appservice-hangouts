"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import os.path
import asyncio
import logging
from functools import partial
from tempfile import NamedTemporaryFile

import click
from aiohttp import web

from appservice_framework import AppService, database as db

from .hangouts_client import HangoutsClient

loop = asyncio.get_event_loop()

# Logging
log = logging.getLogger("hangouts_appservice")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)


async def create_new_user(apps, client, hangouts_user):
    user_id = hangouts_user.id_.gaia_id
    user = apps.get_user(serviceid=user_id)

    if not user:
        user = await apps.create_matrix_user(user_id,
                                             nick=hangouts_user.full_name)

        await apps.set_matrix_profile_image(user.matrixid, hangouts_user.photo_url)

    return user


async def create_new_room(apps, client, auth_user, service_roomid):
    room = await apps.create_linked_room(auth_user, service_roomid)
    conv = client.get_conversation(service_roomid)

    for user in conv.users:
        if not user.is_self:

            user = await create_new_user(apps, client, user)

            if not user in room.users:
                await apps.add_user_to_room(user.matrixid, room.matrixalias)

    return room


async def handle_hangouts_message(apps, client, conv, user, event):
    service_roomid = conv.id_
    service_userid = str(user.id_.gaia_id)
    message = event.text

    log.debug("Received message in hangouts room: %s from user %s",
              service_roomid, service_userid)

    self_id = await client.get_self()
    self_id = str(self_id.id_.gaia_id)

    # TODO: It would be nice if you didn't have to do this.
    if self_id == service_userid:
        return

    auth_user = apps.get_user(serviceid=self_id)
    assert isinstance(auth_user, db.AuthenticatedUser)

    room = apps.get_room(serviceid=service_roomid)
    if not room:
        room = await create_new_room(apps, client, auth_user, service_roomid)

    await apps.relay_service_message(service_userid, service_roomid,
                                     message, self_id)


@click.command()
@click.argument("hangouts_token")
@click.argument('matrix_server', default="http://localhost:8008")
@click.argument('server_domain', default="localhost")
@click.argument('database_uri', default="sqlite:///:memory:")
@click.argument('access_token', default="wfghWEGh3wgWHEf3478sHFWE")
@click.option('--debug/--no-debug', default=True)
def main(matrix_server, server_domain,
         access_token, database_uri,
         hangouts_token,
         debug=False):

    if debug:
        log.setLevel(logging.DEBUG)


    apps = AppService(matrix_server=matrix_server,
                      server_domain=server_domain,
                      access_token=access_token,
                      user_namespace="@hangouts_.*",
                      room_namespace="#hangouts_.*",
                      database_url=database_uri,
                      loop=loop,
                      invite_only_rooms=True)


    @apps.matrix_recieve_message
    async def send_message(apps, auth_user, room, content):
        client, serviceid = await apps.service_connections[auth_user]
        conv = client.get_conversation(room.serviceid)
        resp =  await client.send_message(conv,
                                          content['body'])
        return resp



    @apps.service_connect
    async def connect_hangouts(apps, userid, auth_token):
        client = await HangoutsClient.init_from_refresh_token(auth_token,
                                                              partial(handle_hangouts_message, apps),
                                                              loop,
                                                              apps.http_session)

        user = await client.get_self()


        return client, str(user.id_.gaia_id)

    user1 = apps.add_authenticated_user("@admin:localhost", hangouts_token)


    with apps.run() as run_forever:
        run_forever()
