# SPDX-License-Identifier: Apache-2.0
"""Owner-selected document variants; renaming is not anonymization."""
import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from cryptography.fernet import Fernet
from .ledger import private_write
from .model import Invalid

DISCLOSURE = ('Prepared by a participant; not an official agency document. '
              'Renaming does not make this document anonymous or unlinkable. '
              'Statements and source attributions require human verification.')
TITLES = {
    'meeting': ('Meeting Preparation Brief', 'Meeting Questions and Notes', 'Meeting Discussion Brief'),
    'request': ('Records Request Draft', 'Draft Request for Records', 'Public Records Request Draft'),
    'personal': ('Personal Record Summary', 'Personal Notes Summary', 'Personal Record Brief'),
}


@dataclass(frozen=True)
class Preview:
    reference: str
    title: str
    data: bytes
    sha256: str


class VariantStore:
    """Private encrypted custody separate from any generated/exported artifact.

    The caller retains the external Fernet key and must show Preview.data before
    approving Preview.sha256. No source records or collaboration state are read.
    """
    def __init__(self, directory, key):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key)

    def _path(self, reference, suffix='variant'):
        if not isinstance(reference,str) or len(reference)!=32 or any(c not in '0123456789abcdef' for c in reference):
            raise Invalid('invalid variant reference')
        return self.directory / (reference + '.' + suffix)

    def _write(self, path, value):
        private_write(path, self.cipher.encrypt(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()))

    def _read(self, reference):
        return json.loads(self.cipher.decrypt(self._path(reference).read_bytes()))

    def create(self, category, selected_text, source_reference, *, unbranded=False,
               presenter=None, disclose_presenter=False):
        if category not in TITLES: raise Invalid('unsupported document category')
        if not isinstance(selected_text,str) or not selected_text.strip() or len(selected_text)>100000:
            raise Invalid('select bounded document text')
        if not isinstance(source_reference,str) or not source_reference or len(source_reference)>1000:
            raise Invalid('private source reference required')
        if presenter is not None and (disclose_presenter is not True or not isinstance(presenter,str) or not presenter.strip() or len(presenter)>200 or '\n' in presenter or '\r' in presenter):
            raise Invalid('explicit selected presenter disclosure required')
        # Collision refusal is enforced by private_write(O_EXCL), not probability alone.
        for _ in range(8):
            reference=secrets.token_hex(16)
            title=secrets.choice(TITLES[category])
            parts=[title,'Reference: '+reference]
            if not unbranded: parts.append('Prepared with FLOCK OFF')
            if presenter is not None:parts.append('Presenter: '+presenter)
            parts.extend(['',selected_text,'',DISCLOSURE,''])
            data='\n'.join(parts).encode('utf-8')
            value={'reference':reference,'title':title,'source_reference':source_reference,
                   'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
            try:self._write(self._path(reference),value)
            except FileExistsError:continue
            return Preview(reference,title,data,value['sha256'])
        raise Invalid('could not allocate unique variant reference')

    def preview(self, reference):
        value=self._read(reference);data=base64.b64decode(value['data'])
        if hashlib.sha256(data).hexdigest()!=value['sha256']:raise Invalid('variant custody mismatch')
        return Preview(reference,value['title'],data,value['sha256'])

    def recover_source(self, reference):
        return self._read(reference)['source_reference']

    def approve(self, reference, preview_sha256, *, reviewer, consent=False):
        preview=self.preview(reference)
        if consent is not True or preview.sha256!=preview_sha256 or not isinstance(reviewer,str) or not reviewer.strip():
            raise Invalid('review these exact bytes and explicitly approve disclosure')
        self._write(self._path(reference,'approval'),{'sha256':preview.sha256,'reviewer':reviewer})

    def export(self, reference, preview_sha256, output):
        preview=self.preview(reference)
        path=self._path(reference,'approval')
        if not path.exists():raise Invalid('variant requires its own exact-byte approval')
        approval=json.loads(self.cipher.decrypt(path.read_bytes()))
        if preview.sha256!=preview_sha256 or approval['sha256']!=preview.sha256:raise Invalid('approved bytes changed')
        output=Path(output)
        if output.resolve().is_relative_to(self.directory.resolve()):raise Invalid('export outside private custody directory')
        private_write(output,preview.data)
        return {'sha256':preview.sha256,'published':False}
