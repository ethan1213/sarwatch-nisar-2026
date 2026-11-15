import hashlib
import tempfile
import unittest
from pathlib import Path
from sarwatch.acquisition import download_verified


class Response:
    def __init__(self, data, code=200, headers=None, fail=False):
        self.data, self.status_code, self.headers, self.fail = data, code, headers or {}, fail
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self): pass
    def iter_content(self, **kwargs):
        yield self.data
        if self.fail: raise OSError('network dropped')


class Session:
    def __init__(self, responses): self.responses, self.headers = iter(responses), []
    def get(self, url, **kwargs):
        self.headers.append(kwargs['headers'])
        return next(self.responses)


class AcquisitionTests(unittest.TestCase):
    def test_resume_after_network_drop_and_validate_official_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'scene.h5'
            session = Session([Response(b'abc', fail=True), Response(b'def', 206, {'Content-Range':'bytes 3-5/6'})])
            download_verified(session,'https://example.test/scene',path,6,hashlib.md5(b'abcdef').hexdigest(),retry_delay=0)
            self.assertEqual(path.read_bytes(),b'abcdef')
            self.assertEqual(session.headers[1]['Range'],'bytes=3-')
            self.assertFalse(path.with_suffix('.h5.part').exists())

    def test_ignored_range_overwrites_instead_of_concatenating(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'scene.h5'
            path.with_suffix('.h5.part').write_bytes(b'abc')
            download_verified(Session([Response(b'abcdef')]),'https://example.test/scene',path,6,hashlib.md5(b'abcdef').hexdigest())
            self.assertEqual(path.read_bytes(),b'abcdef')

    def test_wrong_checksum_never_publishes_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'scene.h5'
            with self.assertRaises(ValueError):
                download_verified(Session([Response(b'bad')]),'https://example.test/scene',path,3,'0'*32)
            self.assertFalse(path.exists())
            self.assertTrue(path.with_suffix('.h5.part').exists())

    def test_wrong_content_range_never_appends(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'scene.h5'
            part=path.with_suffix('.h5.part'); part.write_bytes(b'abc')
            with self.assertRaises(ValueError):
                download_verified(Session([Response(b'def',206,{'Content-Range':'bytes 0-2/6'})]),'https://example.test/scene',path,6,hashlib.md5(b'abcdef').hexdigest())
            self.assertEqual(part.read_bytes(),b'abc')
