"""
Run the Application Service Hangouts <> Matrix bridge.
"""
import io
import os.path
import asyncio
import logging
from functools import partial
from tempfile import NamedTemporaryFile

import click
import aiohttp
from aiohttp import web
from hangups.hangouts_pb2 import ITEM_TYPE_PLUS_PHOTO

from appservice_framework import AppService, database as db

from .hangouts_client import HangoutsClient

loop = asyncio.get_event_loop()

# Logging
log = logging.getLogger("hangouts_appservice")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)


async def create_new_user(apps, client, hangouts_user):
    user_id = hangouts_user.id_.gaia_id
    user = apps.get_user(serviceid=user_id)

    if not user:
        user = await apps.create_matrix_user(user_id,
                                             nick=hangouts_user.full_name)

        if hangouts_user.photo_url:
            await apps.set_matrix_profile_image(user.matrixid, "https:"+hangouts_user.photo_url)

    return user


async def add_users_to_room(apps, client, conv, room):
    for user in conv.users:
        if not user.is_self:
            user = await create_new_user(apps, client, user)

            if not user in room.users:
                await apps.add_user_to_room(user.matrixid, room.matrixalias)


async def create_new_room(apps, client, auth_user, service_roomid):
    conv = client.get_conversation(service_roomid)
    # Set the conversation name
    convname = None
    if conv.name:
        convname = conv.name
    elif len(conv.users) == 2:
        for user in conv.users:
            if not user.is_self:
                convname = user.full_name

    room = await apps.create_linked_room(auth_user, service_roomid,
                                         matrix_roomname=convname)


    return room


async def handle_message_with_attachments(apps, event, service_userid, service_roomid, self_id):
    attachments_pb = event._event.chat_message.message_content.attachment

    if len(event.attachments) > 1:
        log.warning("Can't handle more that one attachment")
    attachment = event.attachments[0]
    attachment_pb = attachments_pb[0]

    embed_item = attachment_pb.embed_item

    # Get the filename from the headers
    async with apps.http_session.request("GET", attachment) as resp:
        filename = resp.headers['Content-Disposition'].split('"')[-2]

    if embed_item.type[0] == ITEM_TYPE_PLUS_PHOTO:
        return await apps.relay_service_image(service_userid, service_roomid,
                                              attachment, self_id, filename=filename)
    else:
        return await apps.relay_service_message(service_userid, service_roomid,
                                                event.text, self_id)


async def handle_hangouts_message(apps, client, conv, user, event):
    service_roomid = conv.id_
    service_userid = str(user.id_.gaia_id)
    message = event.text

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

    # Do this here to make sure new users are added after a restart or error
    conv = client.get_conversation(service_roomid)
    await add_users_to_room(apps, client, conv, room)

    try:
        if event.attachments:
            return await handle_message_with_attachments(apps, event, service_userid,
                                                         service_roomid, self_id)
    except Exception as e:
        log.exception("Failed to handle message attachments")

    return await apps.relay_service_message(service_userid, service_roomid,
                                            message, self_id)



@click.command()
@click.option("--mxid", "-m", multiple=True)
@click.option("--token", "-t", multiple=True)
@click.option('--matrix_server', default="http://localhost:8008")
@click.option('--server_domain', default="localhost")
@click.option('--database-uri', default="sqlite:///:memory:")
@click.option('--access_token', default="wfghWEGh3wgWHEf3478sHFWE")
@click.option('--debug/--no-debug', default=True)
def main(mxid, token, matrix_server, server_domain,
         access_token, database_uri,
         debug=False):

    if debug:
        log.setLevel(logging.DEBUG)

    if not len(mxid) == len(token):
        raise ValueError("you must specify equal numbers of tokens and mxids")
    if not mxid and token:
        raise ValueError("You must specify at least one mxid, token pair")

    apps = AppService(matrix_server=matrix_server,
                      server_domain=server_domain,
                      access_token=access_token,
                      user_namespace="@hangouts_.*",
                      sender_localpart="hangouts",
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


    @apps.matrix_recieve_image
    async def send_message(apps, auth_user, room, content):
        client, serviceid = await apps.service_connections[auth_user]
        conv = client.get_conversation(room.serviceid)

        # Get download URL from the matrix media store
        image_url = content['url']
        image_url = apps.api.get_download_url(image_url)

        resp = await client.send_image(conv, image_url, content['body'])
        return resp


    async def reconnect(apps, serviceid, auth_token):
        log.info("Reconnecting for user {}.".format(serviceid))
        auth_user = apps.get_user(serviceid=serviceid)

        future = asyncio.ensure_future(connect_hangouts(self, None, auth_token))
        future.add_done_callback(partial(apps._connection_successful, user=auth_user))

        if serviceid2 != serviceid:
            auth_user.serviceid = serviceid2
            apps.dbsession.commit()

        apps.service_connections[auth_user] = future


    @apps.service_connect
    async def connect_hangouts(apps, userid, auth_token):
        # Each auth needs it's own session.
        async with aiohttp.ClientSession() as session:
            client = await HangoutsClient.init_from_refresh_token(auth_token,
                                                                  partial(handle_hangouts_message, apps),
                                                                  loop=loop,
                                                                  client_session=session)

        # Once we have authed we want to use the open session
        client.http_session = apps.http_session
        user = await client.get_self()
        serviceid = str(user.id_.gaia_id)

        client.client.on_disconnect.add_observer(partial(reconnect, apps, serviceid, auth_token))

        return client, serviceid


    for mxid, token in zip(mxid, token):
        if not apps.get_user(matrixid=mxid):
            apps.add_authenticated_user(mxid, token)


    with apps.run() as run_forever:
        run_forever()
