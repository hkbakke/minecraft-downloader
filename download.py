#!/usr/bin/env python3

import argparse
from urllib.request import Request, urlopen
import json
import logging
import hashlib
import os
import sys


MANIFEST_URL = 'https://launchermeta.mojang.com/mc/game/version_manifest.json'
LOGGER = logging.getLogger()


class Release:
    def __init__(self, manifest_url):
        self.manifest_url = manifest_url
        self._manifest = None

    @property
    def version(self):
        return self.manifest['id']

    @property
    def manifest(self):
        if self._manifest is None:
            request = Request(self.manifest_url)
            response = urlopen(request)
            self._manifest = json.loads(response.read().decode())
        return self._manifest

    @property
    def url(self):
        return self.manifest['downloads']['server']['url']

    @property
    def checksum(self):
        return self.manifest['downloads']['server']['sha1']


class Manifest:
    def __init__(self, url=MANIFEST_URL):
        self.url = url
        self._content = None

    @property
    def content(self):
        if self._content is None:
            request = Request(self.url)
            response = urlopen(request)
            self._content = json.loads(response.read().decode())
        return self._content

    def get_release(self, version=None):
        if version is None:
            version = self.content['latest']['release']

        for i in self.content['versions']:
            if i['id'] == version:
                return Release(i['url'])


def download_file(url, filename):
    request = Request(url)
    response = urlopen(request)

    with open(filename, 'wb') as f:
        f.write(response.read())

def get_checksum(filename):
    h = hashlib.sha1()
    with open(filename, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def verify(filename, checksum):
    return get_checksum(filename) == checksum

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='only output warnings and errors')
    parser.add_argument('--filename', metavar='FILENAME', help='set output filename')
    parser.add_argument('--version', metavar='VERSION', help='specify version if latest is not wanted')
    parser.add_argument('--versioned-filename', action='store_true', help='put version in filename')
    parser.add_argument('--is-updated', action='store_true', help='only check if file is updated')
    args = parser.parse_args()

    if args.verbose:
        log_level = 'DEBUG'
    elif args.quiet:
        log_level = 'WARNING'
    else:
        log_level = 'INFO'

    LOGGER.setLevel(log_level)
    console = logging.StreamHandler()
    LOGGER.addHandler(console)

    manifest = Manifest()
    release = manifest.get_release(args.version)
    filename = None

    if args.versioned_filename:
        filename = 'server-%s.jar' % release.version
    elif args.filename:
        filename = args.filename
    else:
        filename = release.url.rsplit('/', 1)[1]

    if os.path.isfile(filename) and get_checksum(filename) == release.checksum:
        LOGGER.info("'%s' already exists and is the correct version", filename)
        return 0

    if args.is_updated:
        LOGGER.info("'%s' either do no exist or is not the correct version", filename)
        return 1

    tmpfile = '%s.tmp' % filename

    try:
        download_file(release.url, tmpfile)

        if verify(tmpfile, release.checksum):
            os.rename(tmpfile, filename)
        else:
            LOGGER.error("Invalid checksum. Removing...")
    finally:
        try:
            os.unlink(tmpfile)
        except FileNotFoundError:
            pass

    LOGGER.info("Downloaded '%s'", filename)


if __name__ == '__main__':
    sys.exit(main())
