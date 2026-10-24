#!/bin/sh
# NeoBoot - Ibrahem Hamdan | Version 10
set -e
NEO_PYTHON=''
for candidate in python python3 python2; do
    if command -v "$candidate" >/dev/null 2>&1; then
        NEO_PYTHON=$candidate
        break
    fi
done
[ -n "$NEO_PYTHON" ] || { echo 'A working Python installation is required.'; exit 1; }
exec "$NEO_PYTHON" - --install --reinstall <<'NEOBOOT_INSTALLER_PY'
# -*- coding: utf-8 -*-
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
import time
try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

REPOSITORY = 'xximhxx/Neoboot'
PACKAGE = 'enigma2-plugin-extensions-neoboot-ibrahem-hamdan'
ASSET = 'NeoBoot-Ibrahem-Hamdan.ipk'
CONFIG = '/nonexistent/neoboot-standalone-release.json'
MAX_SIZE = 64 * 1024 * 1024


def version_key(value):
    if not re.match(r'^\d+(?:\.\d+)*$', str(value)):
        raise ValueError('Invalid version')
    parts = [int(p) for p in str(value).split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def local_release():
    try:
        with open(CONFIG, 'r') as handle:
            item = json.load(handle)
            return str(item['version']), int(item['release'])
    except (IOError, OSError, ValueError, KeyError):
        # The standalone installer has no adjacent release.json.
        try:
            process = subprocess.Popen(['opkg', 'status', PACKAGE], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, unused = process.communicate()
            if not isinstance(output, str):
                output = output.decode('utf-8', 'replace')
            match = re.search(r'^Version:\s*(\d+(?:\.\d+)*)(?:-r(\d+))?\s*$', output, re.M)
            if process.returncode == 0 and match:
                return match.group(1), int(match.group(2) or 0)
        except OSError:
            pass
    return '0', 0


def read_url(url, limit):
    request = Request(url, headers={'User-Agent': 'NeoBoot-Ibrahem-Hamdan/10', 'Cache-Control': 'no-cache'})
    response = urlopen(request, timeout=30)
    try:
        result = response.read(limit + 1)
    finally:
        response.close()
    if len(result) > limit:
        raise ValueError('Download too large')
    return result


def fetch_manifest():
    base = 'https://raw.githubusercontent.com/' + REPOSITORY + '/main/'
    item = json.loads(read_url(base + 'update.json?ts=' + str(int(time.time())), 65536).decode('utf-8'))
    if item.get('package') != PACKAGE or item.get('url') != base + ASSET:
        raise ValueError('Update must belong to this package and GitHub repository')
    version_key(item.get('version'))
    if not isinstance(item.get('release'), int) or item['release'] < 1:
        raise ValueError('Invalid build number')
    if item.get('package_version') != str(item['version']) + '.0-r' + str(item['release']):
        raise ValueError('Package version does not match update metadata')
    if not re.match(r'^[0-9a-f]{64}$', item.get('sha256', '')):
        raise ValueError('Missing checksum')
    return item


def install(reinstall=False):
    if os.path.exists('/.multinfo'):
        raise RuntimeError('Please boot Internal Flash before updating NeoBoot or all images.')
    item = fetch_manifest()
    current, build = local_release()
    latest = version_key(item['version']), item['release']
    installed = version_key(current), build
    print('NeoBoot - Ibrahem Hamdan | Version %s Build %s' % (item['version'], item['release']))
    if latest < installed:
        raise RuntimeError('Downgrade blocked')
    if latest == installed and not reinstall:
        print('You already have the latest build.')
        return 0
    data = read_url(item['url'] + '?build=' + str(item['release']), MAX_SIZE)
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Checksum mismatch. Wait for GitHub uploads to finish, then retry.')
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('Downloaded file is not an IPK package')
    folder = tempfile.mkdtemp(prefix='neoboot-10-', dir='/tmp')
    try:
        path = os.path.join(folder, ASSET)
        with open(path, 'wb') as handle:
            handle.write(data)
        status = subprocess.call(['opkg', 'install', path])
        if status:
            raise RuntimeError('opkg failed (exit %s). Read the messages above.' % status)
        print('Installed. Open NeoBoot > Update all images from Internal Flash, then restart the GUI.')
    finally:
        shutil.rmtree(folder)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='NeoBoot - Ibrahem Hamdan GitHub updater')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--reinstall', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.install:
            return install(args.reinstall)
        item = fetch_manifest()
        current, build = local_release()
        print('Installed: Version %s Build %s | Available: Version %s Build %s' % (current, build, item['version'], item['release']))
        return 0
    except Exception as error:
        sys.stderr.write('NeoBoot update failed: %s\n' % error)
        return 1


if __name__ == '__main__':
    sys.exit(main())

NEOBOOT_INSTALLER_PY
