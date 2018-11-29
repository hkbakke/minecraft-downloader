#!/usr/bin/env python3

import argparse
from urllib.request import Request, urlopen
import json
import sys
import logging
import hashlib
import os


MANIFEST_URL = 'https://launchermeta.mojang.com/mc/game/version_manifest.json'
LOGGER = logging.getLogger()


class Package:
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
    def server_download_url(self):
        return self.manifest['downloads']['server']['url']

    @property
    def server_download_sha1(self):
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

    def get_package(self, version=None):
        if version is None:
            version = self.content['latest']['release']

        for i in self.content['versions']:
            if i['id'] == version:
                return Package(i['url'])


def download_file(url, filename=None):
    if filename is None:
        filename = url.rsplit('/', 1)[1]

    request = Request(url)
    response = urlopen(request)

    with open(filename, 'wb') as f:
        f.write(response.read())

    return filename

def get_checksum(filename):
    h = hashlib.sha1()
    with open(filename, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def verify(filename, checksum):
    if get_checksum(filename) == checksum:
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='only output warnings and errors')
    parser.add_argument('--filename', metavar='FILENAME', help='set output filename')
    parser.add_argument('--version', metavar='VERSION', help='specify version if latest is not wanted')
    parser.add_argument('--versioned-filename', action='store_true', help='put version in filename')
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
    package = manifest.get_package(args.version)
    filename = None

    if args.versioned_filename:
        filename = 'server-%s.jar' % package.version
    elif args.filename:
        filename = args.filename

    filename = download_file(package.server_download_url, filename)
    
    if not verify(filename, package.server_download_sha1):
        LOGGER.info("Invalid checksum for '%s'. Removing...", filename)
        os.unlink(filename)

    LOGGER.info("Downloaded '%s'", filename)


if __name__ == '__main__':
    sys.exit(main())
