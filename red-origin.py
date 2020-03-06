#!/usr/bin/env python3
import argparse
import html
import io
import json
import os
import requests
import shutil
import stat
import sys
import subprocess
import tempfile
import time
import urllib.parse

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'red-origin',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'}

class RequestException(Exception):
    pass

class RedactedAPI:
    def __init__(self, session_cookie=None):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session_cookie = session_cookie
        self.authkey = None
        self.last_request = time.time()
        self._login()

    def _login(self):
        mainpage = 'https://redacted.ch/';
        cookiedict = {"session": self.session_cookie}
        cookies = requests.utils.cookiejar_from_dict(cookiedict)

        self.session.cookies.update(cookies)
        r = self.session.get(mainpage)
        accountinfo = self.request('index')
        self.authkey = accountinfo['authkey']

    def request(self, action, **kwargs):
        ajaxpage = 'https://redacted.ch/ajax.php'
        params = {'action': action}
        if self.authkey:
            params['auth'] = self.authkey
        params.update(kwargs)
        r = self.session.get(ajaxpage, params=params, allow_redirects=False)
        self.last_request = time.time()
        try:
            parsed = json.loads(r.content)
            if parsed['status'] != 'success':
                raise RequestException
            return parsed['response']
        except ValueError:
            raise RequestException

    def get_torrent_info(self, info_hash):
        info = self.request('torrent', hash=info_hash)
        group = info['group']
        torrent = info['torrent']

        if group['categoryName'] != 'Music':
            return None

        # remastered is always True
        artists = group['musicInfo']['artists']
        if len(artists) == 1:
            artists = artists[0]['name']
        elif len(artists) == 2:
            artists = '%s & %s' % (artists[0]['name'], artists[1]['name'])
        else:
            artists = 'Various Artists'

        out = [
            ('Artist',         artists),
            ('Name',           group['name']),
            ('Edition',        torrent['remasterTitle']),
            ('Edition year',   torrent['remasterYear']),
            ('Media',          torrent['media']),
            ('Catalog number', torrent['remasterCatalogueNumber']),
            ('Record label',   torrent['remasterRecordLabel']),
            ('Original year',  group['year']),
            ('Log',            '%s%%' % torrent['logScore'] if torrent['hasLog'] else ''),
            ('File count',     torrent['fileCount']),
            ('Size',           torrent['size']),
            ('Info hash',      torrent['infoHash']),
            ('Uploaded by',    '%s (%s)' % (torrent['username'], torrent['time'])),
            ('Permalink',      'https://redacted.ch/torrents.php?torrentid=%s' % torrent['id']),
        ]

        files = list((a,b) for b,a in (word.split('{{{') for word in torrent['fileList'].replace('}}}', '').split('|||')))

        result = make_table(out, True)
        result += '\n{0}/\n'.format(html.unescape(torrent['filePath']))
        result += make_table(files, False)
        comment = html.unescape(torrent['description']).strip('\r\n')
        if comment:
            result += '\n{0}\n'.format(comment)

        return result

def make_table(arr, ljust):
    k_width = max(len(html.unescape(k)) for k,v in arr) + (2 if ljust else 0)
    result = ''
    for k,v in arr:
        just = k.ljust if ljust else k.rjust
        result += "".join((html.unescape(just(k_width)), ('    ' if not ljust else ''), html.unescape(str(v) or '-'))) + '\n'
    return result


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='red-origin')
parser.add_argument('info_hash', help='info hash of the torrent')
parser.add_argument('cookie', help='cookie for logging in to RED')
parser.add_argument('--out', '-o', help='path to write origin file (defaults to stdout)')
parser.add_argument('--redconfig', help='the location of the REDbetter configuration file', \
        default=os.path.expanduser('~/.redactedbetter/config'))

args = parser.parse_args()
api = RedactedAPI(args.cookie)
info = api.get_torrent_info(args.info_hash)

if not info:
    print('Not a music torrent', file=sys.stderr)
    sys.exit(4)
if args.out:
    with io.open(args.out, 'w', encoding='utf-8') as f:
        f.write(info)
else:
    print(info, end="")
