matrix-appservice-hangouts
==========================

This is a `matrix appservice <https://matrix.org/docs/guides/application_services.html>`_
with the objective of being a fully featured puppeting multi-user hangouts bridge.

This bridge is implemented in Python 3.6+ using asyncio and the
`hangups <https://github.com/tdryer/hangups>`_ library. This library contains an
asyncio implementation of parts of the matrix client-server API and the
application service API.


Why Python 3.6
--------------

I wanted to implement this using asyncio and using the `async def` and `await`
syntax. Python 3.6 is because I am lazy and love 
`f-strings <https://www.python.org/dev/peps/pep-0498/)>`_.

Usage
-----

The appservice can be run with the `hangoutsas` command. The default options for
this command connect to the localhost testing homeserver.

.. code-block:: none

  $ hangoutsas --help
    Usage: hangoutsas [OPTIONS]

    Options:
      -m, --mxid TEXT
      -t, --token TEXT
      --matrix_server TEXT
      --server_domain TEXT
      --database-uri TEXT
      --access_token TEXT
      --debug / --no-debug
      --help                Show this message and exit.

You need to provide the matrix user id and hangouts authentication tokens for any users (technically only on first run, as they are then stored in the database). This may change in the future, but it is very hard to obtain hangouts tokens and there are security concerns over allowing people to login with the bridge. (Also I haven't implemented support for an admin chat channel yet!)

The best way to get your personal login token is to `follow these instructions <https://github.com/tdryer/hangups/issues/350#issuecomment-323553771>`_. When logged in, you can find the refresh token in `~/.cache/hangups/refresh_token.txt` and use it to log in with the bridge.

Installation
------------

**NOTE**: Currently the `appservice_framework` package requires a branch of the
 `matrix-python-sdk` so it's probably better if you clone both this repo and the
 `appservice-framework
 <https://github.com/Cadair/python-appservice-framework.git>`_ repo and install
 using `requirements.txt` in both.

..
   Install using pip:

   .. code-block:: none

      pip install git+https://github.com/Cadair/python-appservice-framework.git
      pip install git+https://github.com/Cadair/matrix-appservice-hangouts


Requirements
^^^^^^^^^^^^

* aiohttp
* hangups
* click
* https://github.com/Cadair/python-appservice-framework.git


Testing and Development
#######################

This repo also contains configuration for a vagrant VM running a matrix
homeserver, this can be used to develop or test the appservice. It can be run
with:

.. code-block:: none

   $ vagrant up --provision

You can then connect your matrix client to the address `http://localhost:8008`
with the username `@admin:localhost` and password `admin`.

TODO List
---------

* Handle hangouts events:
  - Join room
  - Part room
  - Typing
  - Online / Offline (bidirectional)

* Add some way of joining hangouts rooms before getting a message in the room. This might be made easier once communities are easily filterable on the matrix side.


Licence
-------

MIT

Authors
-------

`matrix_appservice_hangouts` was written by `Stuart Mumford <http://stuartmumford.uk>`_.
