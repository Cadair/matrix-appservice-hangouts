matrix-appservice-hangouts
==========================

.. image:: https://img.shields.io/pypi/v/matrix-appservice-hangouts.svg
    :target: https://pypi.python.org/pypi/matrix-appservice-hangouts
    :alt: Latest PyPI version

.. image:: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal.png
   :target: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal
   :alt: Latest Travis CI build status

This is a [matrix appservice](https://matrix.org/docs/guides/application_services.html)
with the objective of being a fully featured puppeting multi-user hangouts bridge.

This bridge is implemented in Python 3.6+ using asyncio and the
`hangups <https://github.com/tdryer/hangups>_ library. This library contains an
asyncio implementation of parts of the matrix client-server API and the
application service API.


Why Python 3.6
--------------

I wanted to implement this using asyncio and using the `async def` and `await`
syntax. Python 3.6 is because I am lazy and love 
`f-strings <https://www.python.org/dev/peps/pep-0498/)>_.

Usage
-----

Installation
------------

Requirements
^^^^^^^^^^^^

Compatibility
-------------

Licence
-------

Authors
-------

`matrix-appservice-hangouts` was written by `Stuart Mumford <http://stuartmumford.uk>`_.
