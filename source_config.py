"""Validated source identity separate from the audiobook output location.

Legacy scalar roots remain unchanged: durable scanner/catalog keys are the exact
configured path strings, not a newly generated library id. Loading never writes
settings or activates a scan.
"""
from dataclasses import dataclass
import os


def _key(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def contains(path, root):
    try:
        return os.path.commonpath((_key(path), _key(root))) == _key(root)
    except ValueError:
        return False


def _path(value):
    if not isinstance(value, str) or not value.strip() or '\x00' in value or not os.path.isabs(value):
        raise ValueError('Source and output paths must be nonempty absolute paths')
    return value


@dataclass(frozen=True)
class SourceConfig:
    audiobook_sources: tuple
    audiobook_output_root: str | None = None

    def to_fields(self):
        return {'audiobook_sources': list(self.audiobook_sources),
                'audiobook_output_root': self.audiobook_output_root}


def normalize_sources(roots, audiobook_sources=None, output_root=None):
    primary = _path(roots['Audiobooks'])
    sources = (primary,) if audiobook_sources is None else audiobook_sources
    if not isinstance(sources, (list, tuple)) or not sources or len(sources) > 32:
        raise ValueError('Expected an ordered list of 1 to 32 audiobook sources')
    sources = tuple(_path(value) for value in sources)
    if sources[0] != primary:
        raise ValueError('Preserve the exact existing Audiobooks root as Source 1')
    for index, source in enumerate(sources):
        for other in sources[:index]:
            if contains(source, other) or contains(other, source):
                raise ValueError('Audiobook source roots overlap or alias one another')
        for label in ('Podcasts', 'Ebooks'):
            other = roots.get(label)
            # The existing nested Podcasts boundary is intentional, never a source.
            if other and (contains(source, other) or
                          (label != 'Podcasts' and contains(other, source))):
                raise ValueError('Audiobook source overlaps another library')
    if output_root is not None:
        output_root = _path(output_root)
        if any(contains(source, output_root) for source in sources):
            raise ValueError('Output must not contain or alias an audiobook source')
        if any(contains(output_root, roots[label]) or contains(roots[label], output_root)
               for label in ('Podcasts', 'Ebooks') if roots.get(label)):
            raise ValueError('Output overlaps another library')
    return SourceConfig(sources, output_root)


def load_source_config(mapping, legacy_roots):
    """Read additive settings fields; caller preserves all other settings keys."""
    if not isinstance(mapping, dict):
        raise ValueError('Expected source settings object')
    return normalize_sources(legacy_roots, mapping.get('audiobook_sources'),
                             mapping.get('audiobook_output_root'))
