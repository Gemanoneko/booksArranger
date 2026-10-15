"""Prepared in-memory fixtures; not executed or enrolled in application tests."""
import struct
import unittest
from fractions import Fraction

from mp4_preservation import Refused, atom, inspect, prove, retag


def fixture(wide=False, composition=False):
    def table(kind, values):
        return atom(kind, b'\0' * 4 + struct.pack('>I', len(values)) + b''.join(values))

    mvhd = bytearray(100)
    struct.pack_into('>II', mvhd, 12, 600, 36)
    tkhd = bytearray(84)
    tkhd[:4] = b'\0\0\0\3'
    struct.pack_into('>I', tkhd, 12, 1)
    struct.pack_into('>I', tkhd, 20, 36)
    mdhd = bytearray(24)
    struct.pack_into('>II', mdhd, 12, 44100, 3072)
    edits = table(b'elst', [struct.pack('>Iihh', 6, -1, 1, 0), struct.pack('>Iihh', 30, 128, 1, 0)])
    handler = atom(b'hdlr', b'\0' * 8 + b'soun' + b'\0' * 12)
    metadata = atom(b'udta', atom(b'meta', b'\0' * 4 +
                    atom(b'hdlr', b'\0' * 8 + b'mdir' + b'\0' * 12) +
                    atom(b'ilst', atom(b'sonm', atom(b'data', b'\0\0\0\1' + b'\0' * 4 + b'old')))))
    entry = b'\0' * 6 + b'\0\1' + b'\0' * 8 + struct.pack('>HHHHI', 2, 16, 0, 0, 44100 << 16)
    stsd = table(b'stsd', [atom(b'mp4a', entry + atom(b'esds', b'\0' * 4 + b'opaque-descriptor'))])
    stts = table(b'stts', [struct.pack('>II', 3, 1024)])
    ctts = table(b'ctts', [struct.pack('>II', 3, 7)]) if composition else b''
    stsc = table(b'stsc', [struct.pack('>III', 1, 1, 1)])
    stsz = atom(b'stsz', b'\0' * 4 + struct.pack('>II', 0, 3) + struct.pack('>III', 3, 4, 5))
    dinf = atom(b'dinf', table(b'dref', [atom(b'url ', b'\0\0\0\1')]))
    ftyp = atom(b'ftyp', b'M4A ' + b'\0' * 4 + b'isom')

    def movie(offsets):
        chunks = table(b'co64' if wide else b'stco', [v.to_bytes(8 if wide else 4, 'big') for v in offsets])
        stbl = atom(b'stbl', stsd + stts + ctts + stsc + stsz + chunks)
        minf = atom(b'minf', atom(b'smhd', b'\0' * 8) + dinf + stbl)
        mdia = atom(b'mdia', atom(b'mdhd', bytes(mdhd)) + handler + minf)
        trak = atom(b'trak', atom(b'tkhd', bytes(tkhd)) + atom(b'edts', edits) + mdia)
        return atom(b'moov', atom(b'mvhd', bytes(mvhd)) + trak + metadata)

    moov = movie([0, 0, 0])
    start = len(ftyp) + len(moov) + 8
    return ftyp + movie([start, start + 3, start + 7]) + atom(b'mdat', b'abcDEFG12345')


class PreservationTests(unittest.TestCase):
    def test_nonzero_edit_non1000_clock_growth(self):
        source = fixture()
        before = inspect(source)
        candidate, receipt = retag(source, 'A longer approved title')
        after = inspect(candidate)
        self.assertEqual(before['edits'], ((Fraction(1, 100), None), (Fraction(1, 20), Fraction(128, 44100))))
        self.assertEqual(after['edits'], before['edits'])
        self.assertEqual(after['offsets'], tuple(o + receipt['metadata_delta'] for o in before['offsets']))
        self.assertEqual(source, fixture())
        self.assertFalse(receipt['pcm_verified'])

    def test_co64_shrink(self):
        source = fixture(wide=True)
        candidate, receipt = retag(source, 'x')
        self.assertEqual(receipt['metadata_delta'], -2)
        self.assertEqual(inspect(candidate)['packets'], inspect(source)['packets'])

    def test_composition_offsets_preserved(self):
        source = fixture(composition=True)
        candidate, _ = retag(source, 'Unicode \u041a\u043d\u0438\u0433\u0430')
        self.assertEqual(inspect(candidate)['composition_offsets'], (Fraction(7, 44100),) * 3)

    def test_altered_edit_detected(self):
        source = fixture()
        candidate, _ = retag(source, 'new')
        changed = bytearray(candidate)
        at = candidate.index(b'elst') + 4 + 8 + 12 + 4
        struct.pack_into('>i', changed, at, 129)
        with self.assertRaises(Refused):
            prove(source, bytes(changed), 'new')

    def test_payload_change_detected(self):
        source = fixture()
        candidate, _ = retag(source, 'new')
        with self.assertRaises(Refused):
            prove(source, candidate[:-1] + b'!', 'new')

    def test_unknown_top_level_refused(self):
        with self.assertRaises(Refused):
            retag(fixture() + atom(b'free', b''), 'new')

    def test_fragment_refused(self):
        with self.assertRaises(Refused):
            retag(fixture().replace(b'moov', b'moof', 1), 'new')

    def test_external_reference_refused(self):
        source = fixture().replace(b'url \0\0\0\1', b'url \0\0\0\0', 1)
        with self.assertRaises(Refused):
            retag(source, 'new')

    def test_video_track_refused(self):
        with self.assertRaises(Refused):
            retag(fixture().replace(b'soun', b'vide', 1), 'new')

    def test_overlapping_chunk_refused(self):
        changed = bytearray(fixture())
        at = changed.index(b'stco') + 4 + 8
        struct.pack_into('>I', changed, at + 4, struct.unpack_from('>I', changed, at)[0])
        with self.assertRaises(Refused):
            retag(bytes(changed), 'new')

    def test_truncation_and_extended_size_refused(self):
        with self.assertRaises(Refused):
            retag(fixture()[:-1], 'new')
        with self.assertRaises(Refused):
            retag(b'\0\0\0\1' + fixture()[4:], 'new')

    def test_empty_oversized_unapproved_tag_refused(self):
        source = fixture()
        for tag in ('', 'x' * 8001):
            with self.assertRaises(Refused):
                retag(source, tag)
        candidate, _ = retag(source, 'approved')
        with self.assertRaises(Refused):
            prove(source, candidate, 'different')
