#!/usr/bin/env python3
"""Build IPK, update manifest and installer using only Python's standard library."""
import argparse
import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent
PLUGIN_REL = Path('usr/lib/enigma2/python/Plugins/Extensions/NeoBoot')
ASSET = 'NeoBoot-Ibrahem-Hamdan.ipk'
PACKAGE = 'enigma2-plugin-extensions-neoboot-ibrahem-hamdan'


def write_tar(tree, version):
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.GNU_FORMAT) as archive:
            for path in sorted(tree.rglob('*')):
                if '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
                    continue
                entry = archive.gettarinfo(str(path), arcname='./' + path.relative_to(tree).as_posix())
                entry.uid = entry.gid = 0
                entry.uname = entry.gname = 'root'
                entry.mtime = 0
                if entry.isfile():
                    # GitHub ZIP uploads may lose Unix execute permission bits.
                    payload = path.read_bytes()
                    if payload.startswith(b'#!') or payload.startswith(b'\x7fELF') or path.name in ('preinst', 'postinst', 'prerm', 'postrm'):
                        entry.mode = 0o755
                    else:
                        entry.mode = 0o644
                    with path.open('rb') as handle:
                        archive.addfile(entry, handle)
                else:
                    entry.mode = 0o755 if entry.isdir() else entry.mode
                    archive.addfile(entry)
    return raw.getvalue()


def ar_member(name, payload):
    header = (f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(payload):<10}`\n').encode('ascii')
    assert len(header) == 60
    return header + payload + (b'\n' if len(payload) % 2 else b'')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY') or (ROOT / 'REPOSITORY').read_text().strip())
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    repository = args.repository.strip()
    if repository and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*', repository):
        parser.error('repository must be OWNER/REPO')
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+(?:\.\d+)*', version):
        parser.error('VERSION must contain a numeric version, for example 10.1')
    for path in (ROOT / 'package/data').rglob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        staging = Path(directory)
        shutil.copytree(ROOT / 'package', staging / 'package')
        data = staging / 'package/data'
        control = staging / 'package/control'
        plugin = data / PLUGIN_REL
        metadata = json.loads((plugin / 'branding.json').read_text())
        metadata.update(version=version, repository=repository)
        (plugin / 'branding.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        text = (control / 'control').read_text()
        text = re.sub(r'^Version: .*$', 'Version: ' + version + '-r1', text, flags=re.M)
        text = re.sub(r'^Description: .*$', 'Description: NeoBoot - Ibrahem Hamdan ' + version, text, flags=re.M)
        (control / 'control').write_text(text)
        # Version literals in legacy skin and boot paths are synchronized at build time.
        original = json.loads((ROOT / 'package/data' / PLUGIN_REL / 'branding.json').read_text())['version']
        for path in list(plugin.rglob('*')) + list(control.iterdir()):
            if not path.is_file() or path.suffix in ('.mo', '.ttf', '.png', '.mvi'):
                continue
            payload = path.read_bytes()
            if payload.startswith(b'\x7fELF'):
                old = ('NeoBoot ' + original).encode('ascii')
                new = ('NeoBoot ' + version).encode('ascii')
                if old in payload:
                    if len(old) != len(new):
                        raise ValueError('The boot-menu binary display version must have the same length as ' + original + '. Rebuild native menus to change its length.')
                    path.write_bytes(payload.replace(old, new))
                continue
            try:
                value = payload.decode('utf-8')
            except UnicodeDecodeError:
                continue
            # Replace standalone version numbers in runtime source/scripts, preserve copyright comments.
            lines=[]
            for line in value.splitlines(True):
                if not line.lstrip().startswith('#'):
                    line = re.sub(r'(?<![\d.])' + re.escape(original) + r'(?![\d.])', version, line)
                lines.append(line)
            path.write_text(''.join(lines))
        archive = b'!<arch>\n' + ar_member('debian-binary', b'2.0\n') + ar_member('control.tar.gz', write_tar(control, version)) + ar_member('data.tar.gz', write_tar(data, version))
        (args.output / ASSET).write_bytes(archive)
        digest = hashlib.sha256(archive).hexdigest()
        manifest = {'package': PACKAGE, 'name': 'NeoBoot - Ibrahem Hamdan', 'author': 'Ibrahem Hamdan', 'version': version, 'tag': 'v' + version, 'sha256': digest, 'url': ('https://github.com/' + repository + '/releases/download/v' + version + '/' + ASSET) if repository else '', 'hardware': ['ARMv7-hard-float-32bit', 'MIPSEL-32bit']}
        (args.output / 'update.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (args.output / 'ver.txt').write_text(version + '\n')
        (args.output / 'SHA256SUMS').write_text(digest + '  ' + ASSET + '\n')
        shutil.copyfile(plugin / 'github_update.py', args.output / 'install.py')
        print('Built:', args.output / ASSET)
        print('Version:', version, '| GitHub:', repository or 'not configured; configure in the plugin Update button')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
