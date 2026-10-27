# SPDX-License-Identifier: Apache-2.0
"""Bounded signed application messages using libsodium primitives, not audited MLS."""
import base64
import hashlib
import json
import re
import secrets
import time
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey, VerifyKey

MAX_BYTES = 65536
MAX_MEMBERS = 8
MAX_EVENTS = 2000
TTL = 30
DOMAIN = b'FLOCKOFF-COLLAB-V1\x00'


class Rejected(ValueError):
    pass


def canonical(value):
    def bound(item, depth=0):
        if depth > 10: raise Rejected('nesting limit')
        if isinstance(item, dict):
            if len(item) > 32 or any(not isinstance(k, str) for k in item): raise Rejected('object limit')
            for v in item.values(): bound(v, depth+1)
        elif isinstance(item, list):
            if len(item) > MAX_MEMBERS * 4: raise Rejected('list limit')
            for v in item: bound(v, depth+1)
        elif not isinstance(item, (str, int, bool, type(None))): raise Rejected('unsupported value')
    bound(value)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_BYTES: raise Rejected('message limit')
    return raw


def parse(raw):
    if len(raw) > MAX_BYTES: raise Rejected('message limit')
    def pairs(values):
        result = {}
        for k,v in values:
            if k in result: raise Rejected('duplicate key')
            result[k] = v
        return result
    try: value = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, RecursionError, UnicodeError) as exc: raise Rejected('invalid JSON') from exc
    canonical(value)
    return value


def exact(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()): raise Rejected('unexpected fields')


def ident(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value): raise Rejected('invalid identifier')
    return value


def b64(value): return base64.b64encode(value).decode()
def un64(value):
    try: return base64.b64decode(value, validate=True)
    except Exception as exc: raise Rejected('invalid encoding') from exc
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def uid(): return secrets.token_hex(16)


def signed(body, key, purpose):
    return {'body': body, 'signature': b64(key.sign(DOMAIN + purpose.encode() + b'\x00' + canonical(body)).signature)}


def verify(document, public, purpose):
    exact(document, 'body signature')
    try: VerifyKey(un64(public)).verify(DOMAIN + purpose.encode() + b'\x00' + canonical(document['body']), un64(document['signature']))
    except Exception as exc: raise Rejected('signature rejected') from exc
    return document['body']


def new_identity():
    sign, enc = SigningKey.generate(), PrivateKey.generate()
    return {'sign_secret': b64(bytes(sign)), 'enc_secret': b64(bytes(enc)),
            'sign_public': b64(bytes(sign.verify_key)), 'enc_public': b64(bytes(enc.public_key)),
            'alias': 'member-' + secrets.token_hex(4)}


def public_identity(identity):
    return {k: identity[k] for k in ('sign_public', 'enc_public', 'alias')}


def member(value):
    exact(value, 'sign_public enc_public alias')
    if len(un64(value['sign_public'])) != 32 or len(un64(value['enc_public'])) != 32: raise Rejected('invalid member key')
    if not re.fullmatch('member-[a-f0-9]{8}', value['alias']): raise Rejected('invalid room alias')


def projection(value):
    # Deliberately no arbitrary vault map, original files, URLs, author names or locations.
    exact(value, 'category title text')
    if value['category'] not in ('question', 'comment', 'action', 'summary'): raise Rejected('invalid card category')
    for key, limit in [('title', 120), ('text', 3000)]:
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= limit: raise Rejected('card text limit')
        if any(ord(c) < 32 and c not in '\n\t' for c in value[key]): raise Rejected('control characters')
    return dict(value)
