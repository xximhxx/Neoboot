# -*- coding: utf-8 -*-
"""GitHub Releases updater for NeoBoot - Ibrahem Hamdan.
No import-time network requests. Python 2.7 / 3 compatible.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, 'branding.json')
REPOSITORY_CONFIG = '/etc/enigma2/neoboot-ibrahem-repository'
PACKAGE = 'enigma2-plugin-extensions-neoboot-ibrahem-hamdan'
ASSET = 'NeoBoot-Ibrahem-Hamdan.ipk'
MAX_PACKAGE_SIZE = 64 * 1024 * 1024


def valid_repository(value):
    value = (value or '').strip().rstrip('/')
    prefix = 'https://github.com/'
    if value.startswith(prefix):
        value = value[len(prefix):]
    if value.endswith('.git'):
        value = value[:-4]
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*$', value):
        raise ValueError('Enter a GitHub repository as OWNER/REPO or its https://github.com/OWNER/REPO URL.')
    if any(part in ('.', '..') for part in value.split('/')):
        raise ValueError('Invalid repository.')
    return value


def read_metadata():
    try:
        with open(CONFIG, 'r') as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return {'version': '0', 'repository': ''}


def read_repository():
    try:
        with open(REPOSITORY_CONFIG, 'r') as handle:
            return valid_repository(handle.read())
    except (IOError, OSError, ValueError):
        value = read_metadata().get('repository', '')
        return valid_repository(value) if value else ''


def save_repository(value):
    value = valid_repository(value)
    folder = os.path.dirname(REPOSITORY_CONFIG)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(REPOSITORY_CONFIG + '.new', 'w') as handle:
        handle.write(value + '\n')
    os.rename(REPOSITORY_CONFIG + '.new', REPOSITORY_CONFIG)
    return value


def version_key(value):
    if not re.match(r'^\d+(?:\.\d+)*$', str(value)):
        raise ValueError('Invalid release version: ' + str(value))
    parts = [int(part) for part in str(value).split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def read_url(url, max_size):
    request = Request(url, headers={'User-Agent': 'NeoBoot-Ibrahem-Hamdan-Updater', 'Accept': 'application/octet-stream'})
    response = urlopen(request, timeout=30)
    try:
        data = response.read(max_size + 1)
    finally:
        response.close()
    if len(data) > max_size:
        raise ValueError('Download exceeds permitted size.')
    return data


def fetch_manifest(repository):
    url = 'https://github.com/' + repository + '/releases/latest/download/update.json'
    manifest = json.loads(read_url(url, 64 * 1024).decode('utf-8'))
    if manifest.get('package') != PACKAGE:
        raise ValueError('The release belongs to a different package.')
    version_key(manifest.get('version'))
    if not re.match(r'^[0-9a-f]{64}$', manifest.get('sha256', '')):
        raise ValueError('The release checksum is missing or invalid.')
    # Bind the package URL to the requested repo and a numbered release.
    tag = manifest.get('tag', '')
    if not re.match(r'^v\d+(?:\.\d+)*$', tag) or tag != 'v' + manifest['version']:
        raise ValueError('The release tag does not match its version.')
    expected = 'https://github.com/' + repository + '/releases/download/' + tag + '/' + ASSET
    if manifest.get('url') != expected:
        raise ValueError('The package URL must belong to this repository and release.')
    return manifest


def check(repository):
    manifest = fetch_manifest(repository)
    current = read_metadata().get('version', '0')
    return manifest, current, version_key(manifest['version']) > version_key(current)


def install(repository, reinstall=False):
    if os.path.exists('/.multinfo'):
        raise RuntimeError('Run the update from the internal Flash image.')
    manifest, current, newer = check(repository)
    print('NeoBoot - Ibrahem Hamdan | Installed: %s | Available: %s' % (current, manifest['version']))
    if version_key(manifest['version']) < version_key(current):
        raise RuntimeError('Downgrades are blocked.')
    if not newer and not reinstall:
        print('You already have the latest version.')
        return 0
    data = read_url(manifest['url'], MAX_PACKAGE_SIZE)
    if hashlib.sha256(data).hexdigest() != manifest['sha256']:
        raise ValueError('Checksum mismatch. Installation cancelled.')
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('The downloaded file is not an IPK package.')
    directory = tempfile.mkdtemp(prefix='neoboot-ibrahem-', dir='/tmp')
    try:
        filename = os.path.join(directory, ASSET)
        with open(filename, 'wb') as handle:
            handle.write(data)
        status = subprocess.call(['opkg', 'install', filename])
        if status:
            raise RuntimeError('opkg installation failed (exit %s). Review its output above.' % status)
        print('Update installed. Restart the Enigma2 GUI manually. No automatic reboot.')
    finally:
        shutil.rmtree(directory)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='NeoBoot - Ibrahem Hamdan GitHub updater')
    parser.add_argument('--repository', help='GitHub OWNER/REPO')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--reinstall', action='store_true')
    args = parser.parse_args(argv)
    try:
        repository = valid_repository(args.repository) if args.repository else read_repository()
        if not repository:
            raise ValueError('No repository configured. Use --repository OWNER/REPO or configure it from the plugin Update button.')
        if args.install:
            return install(repository, args.reinstall)
        manifest, current, newer = check(repository)
        print('NeoBoot - Ibrahem Hamdan | Installed: %s | Available: %s' % (current, manifest['version']))
        print('Update available.' if newer else 'No newer version available.')
        return 0
    except Exception as error:
        sys.stderr.write('NeoBoot update failed: %s\n' % error)
        return 1


if __name__ == '__main__':
    sys.exit(main())
