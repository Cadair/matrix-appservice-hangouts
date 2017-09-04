matrix-appservice-hangouts
==========================

.. image:: https://img.shields.io/pypi/v/matrix-appservice-hangouts.svg
    :target: https://pypi.python.org/pypi/matrix-appservice-hangouts
    :alt: Latest PyPI version

.. image:: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal.png
   :target: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal
   :alt: Latest Travis CI build status

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
  Usage: hangoutsas [OPTIONS] [MATRIX_SERVER] [SERVER_DOMAIN] [ACCESS_TOKEN]
                    [CACHE_PATH]

  Options:
    --debug / --no-debug
    --help                Show this message and exit.

Installation
------------

Install using pip:

.. code-block:: none

   pip install git+https://github.com/Cadair/matrix-appservice-hangouts


Requirements
^^^^^^^^^^^^

* aiohttp
* hangups
* ruamel.yaml
* bidict


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


Licence
-------

MIT

Authors
-------

`matrix_appservice_hangouts` was written by `Stuart Mumford <http://stuartmumford.uk>`_.
