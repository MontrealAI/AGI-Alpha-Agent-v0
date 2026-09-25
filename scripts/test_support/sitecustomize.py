# SPDX-License-Identifier: Apache-2.0
"""Deny external Python network traffic during the explicitly offline test run."""

import os
import socket

if os.environ.get("ALPHA_TEST_OFFLINE") == "1":
    _connect = socket.socket.connect
    _connect_ex = socket.socket.connect_ex
    _getaddrinfo = socket.getaddrinfo
    _allowed = {"localhost", "127.0.0.1", "::1", b"localhost", b"127.0.0.1", b"::1", None}

    def _check(address):
        if isinstance(address, tuple) and address[0] not in _allowed:
            raise OSError("external network disabled by offline test runner")

    def _offline_connect(self, address):
        _check(address)
        return _connect(self, address)

    def _offline_connect_ex(self, address):
        _check(address)
        return _connect_ex(self, address)

    def _offline_getaddrinfo(host, *args, **kwargs):
        if host not in _allowed:
            raise OSError("external DNS disabled by offline test runner")
        return _getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = _offline_connect
    socket.socket.connect_ex = _offline_connect_ex
    socket.getaddrinfo = _offline_getaddrinfo
