# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import hashlib
import re


def identifier(value):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid identifier')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid integer')
    return value


class ArtifactStore:
    def __init__(self):
        self.records = {}

    def _key(self, owner, upload):
        return identifier(owner), identifier(upload)

    def _get(self, owner, upload):
        key = self._key(owner, upload)
        if key not in self.records:
            raise ValueError('unknown upload')
        return self.records[key]

    def begin(self, owner, upload, size, digest):
        key = self._key(owner, upload)
        integer(size)
        if size > 65536 or not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None:
            raise ValueError('invalid upload declaration')
        if size == 0 and digest != hashlib.sha256(b'').hexdigest():
            raise ValueError('invalid empty artifact digest')
        if key in self.records:
            row = self.records[key]
            if (row['size'], row['digest']) != (size, digest):
                raise ValueError('upload conflict')
            return
        self.records[key] = dict(owner=owner, upload=upload, size=size, digest=digest,
                                 state='active', cells=[None] * size)

    def put(self, owner, upload, offset, data):
        row = self._get(owner, upload)
        integer(offset)
        if type(data) is not bytes or offset + len(data) > row['size'] or row['state'] == 'aborted':
            raise ValueError('invalid chunk')
        cells = row['cells']
        # Check the whole overlap before filling even one previously empty cell.
        if any(cells[index] is not None and cells[index] != value
               for index, value in enumerate(data, offset)):
            raise ValueError('conflicting overlap')
        cells[offset:offset + len(data)] = data

    def commit(self, owner, upload):
        row = self._get(owner, upload)
        if row['state'] == 'aborted' or any(value is None for value in row['cells']):
            raise ValueError('incomplete artifact')
        data = bytes(row['cells'])
        if hashlib.sha256(data).hexdigest() != row['digest']:
            raise ValueError('digest mismatch')
        row['state'] = 'committed'
        return data

    def abort(self, owner, upload):
        row = self._get(owner, upload)
        if row['state'] == 'committed':
            raise ValueError('committed artifact')
        row['cells'] = [None] * row['size']
        row['state'] = 'aborted'

    def snapshot(self):
        return deepcopy([self.records[key] for key in sorted(self.records)])

    @classmethod
    def restore(cls, checkpoint):
        if not isinstance(checkpoint, list):
            raise ValueError('invalid checkpoint')
        store = cls()
        required = {'owner', 'upload', 'size', 'digest', 'state', 'cells'}
        for source in checkpoint:
            if not isinstance(source, dict) or set(source) != required:
                raise ValueError('invalid checkpoint record')
            row = deepcopy(source)
            key = store._key(row['owner'], row['upload'])
            if key in store.records:
                raise ValueError('duplicate record')
            store.begin(row['owner'], row['upload'], row['size'], row['digest'])
            if not isinstance(row['state'], str) or row['state'] not in {'active', 'committed', 'aborted'}:
                raise ValueError('invalid state')
            cells = row['cells']
            if not isinstance(cells, list) or len(cells) != row['size']:
                raise ValueError('invalid cell array')
            if any(value is not None and (type(value) is not int or not 0 <= value <= 255)
                   for value in cells):
                raise ValueError('invalid byte')
            if row['state'] == 'aborted' and any(value is not None for value in cells):
                raise ValueError('aborted data')
            store.records[key] = row
            if row['state'] == 'committed':
                store.commit(row['owner'], row['upload'])
        return store
