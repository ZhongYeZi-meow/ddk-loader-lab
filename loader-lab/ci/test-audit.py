import struct
import unittest
from audit import version_records


class Versions(unittest.TestCase):
    def test_basic(self):
        d, f = version_records(struct.pack('<Q56s', 7, b'module_layout'))
        self.assertEqual(d, {'module_layout': '0x00000007'})
        self.assertEqual(f, ['basic'])

    def test_extended(self):
        for tail in (b'', b'\0'):
            d, f = version_records(None, struct.pack('<II', 7, 8), b'a\0b\0' + tail)
            self.assertEqual(d, {'a': '0x00000007', 'b': '0x00000008'})
            self.assertEqual(f, ['extended'])

    def test_combined(self):
        d, f = version_records(struct.pack('<Q56s', 7, b'a'), struct.pack('<I', 7), b'a\0')
        self.assertEqual(d, {'a': '0x00000007'})
        self.assertEqual(f, ['basic', 'extended'])

    def test_invalid(self):
        for args in [(None, None, None), (b'',), (b'x',),
                     (struct.pack('<Q56s', 2**32, b'a'),),
                     (struct.pack('<Q56s', 7, b'a') * 2,),
                     (None, b'1234', None), (None, b'123', b'a\0'),
                     (None, b'1234', b'a'), (None, b'1234', b'\0'),
                     (None, b'12345678', b'a\0a\0'),
                     (None, b'1234', b'a\0b\0'),
                     (struct.pack('<Q56s', 7, b'a'), struct.pack('<I', 8), b'a\0')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                version_records(*args)


if __name__ == '__main__':
    unittest.main()
