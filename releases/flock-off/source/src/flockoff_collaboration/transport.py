# SPDX-License-Identifier: Apache-2.0
"""Single explicit networking boundary. No redirects, environment proxy or fallback."""
import base64
import hashlib
import re
from urllib.parse import urlsplit
import requests
from .protocol import canonical, parse, Rejected, MAX_BYTES


def endpoint(value, test_mode=False):
    parts=urlsplit(value)
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('','/'):raise Rejected('endpoint shape')
    if test_mode:
        if parts.scheme!='http' or parts.hostname!='127.0.0.1' or not parts.port:raise Rejected('isolated test endpoint required')
    else:
        if parts.scheme!='http' or parts.port not in (None,80) or not re.fullmatch(r'[a-z2-7]{56}\.onion',parts.hostname or ''):raise Rejected('Tor v3 onion required')
        decoded=base64.b32decode(parts.hostname[:-6].upper())
        if decoded[-1:]!=b'\x03' or decoded[32:34]!=hashlib.sha3_256(b'.onion checksum'+decoded[:32]+b'\x03').digest()[:2]:raise Rejected('invalid onion checksum')
    return value.rstrip('/')


class Transport:
    def __init__(self, url, proxy='socks5h://127.0.0.1:9050', *, test_mode=False):
        self.url=endpoint(url,test_mode);self.test_mode=test_mode
        if not re.fullmatch(r'socks5h://127\.0\.0\.1:[0-9]{1,5}',proxy):raise Rejected('local SOCKS5h proxy required')
        if not 1<=int(proxy.rsplit(':',1)[1])<=65535:raise Rejected('proxy port')
        self.proxy=proxy

    def rpc(self, document):
        with requests.Session() as session:
            session.trust_env=False
            session.headers.clear()
            proxies={} if self.test_mode else {'http':self.proxy,'https':self.proxy}
            try:
                with session.post(self.url+'/rpc',data=canonical(document),headers={'Content-Type':'application/json'},
                                  proxies=proxies,allow_redirects=False,timeout=(3,5),stream=True) as response:
                    if response.status_code!=200:raise Rejected('relay rejected request')
                    raw=bytearray()
                    for chunk in response.iter_content(4096):
                        raw.extend(chunk)
                        if len(raw)>MAX_BYTES:raise Rejected('response limit')
                    return parse(bytes(raw))
            except requests.RequestException as exc:
                # Never expose proxy addresses, secrets or raw requests in UI logs.
                raise ConnectionError('Transport unavailable; pending work remains local. No fallback attempted.') from None
