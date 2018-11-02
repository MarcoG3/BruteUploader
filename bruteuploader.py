#!/usr/bin/python

'''
CHANGELOG:
    [2018-11-02] initial release
'''

__author__ = '@MarcoG3'

import argparse
import requests
import time
import sys
import os
import urlparse
import hashlib
import datetime


class InvalidStatusCode(Exception):
    def __init__(self, code):
        self.code = code


def parse_args():
    parser = argparse.ArgumentParser(
        description='Web File Upload location brute-forcer',
        epilog='BruteUploader is designed to find real location of newly uploaded file when it is not given by the website'
    )

    parser.add_argument('-u', '--url', help='URL of the upload POST endpoint', type=str)
    parser.add_argument('-d', '--post-data', help='Additional POST data to submit along with file', type=str)
    parser.add_argument('-f', '--file-param', help='POST name of the file parameter', type=str)
    parser.add_argument('-p', '--file-path', default='file.txt', help='Path of the file to upload on current machine', type=str)
    parser.add_argument('-x', '--uploads-path', help='Base URL where uploaded files are stored', type=str)
    parser.add_argument('-c', '--cookies', type=str)
    parser.add_argument('-H', '--headers', action='append', nargs='*')
    parser.add_argument('-A', '--user-agent',
                        default='Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36',
                        type=str)

    args = parser.parse_args()

    if not args.url:
        parser.error('No URL specified (-u)')

    if not args.file_param:
        parser.error('No file POST parameter name given (-f)')

    if not args.uploads_path:
        parser.error('No uploads path given (-x)')

    return args


def get_hash(cipher, plaintext):
    c = cipher()
    c.update(plaintext)
    return c.hexdigest()


def filepath_bruteforce(s, t1, t2, tz, filename, base_url):
    names = []
    paths = []
    i = 0
    extension = None
    date = tz if tz else datetime.datetime.now()
    path_split = os.path.splitext(filename)
    ciphers = [hashlib.md5, hashlib.sha1, hashlib.sha256]

    # set extension variable if filename has an extension
    if len(path_split) > 1:
        filename = path_split[0]
        extension = path_split[1]

    # easy to predict names
    if extension: names.append(filename + extension)
    names.append(filename)

    for t in (t1, t2+1):
        for c in ciphers:
            names.append(get_hash(c, str(t)))
            names.append(get_hash(c, str(t) + filename))
            names.append(get_hash(c, filename + str(t)))

            if extension:
                names.append(get_hash(c, str(t)) + extension)
                names.append(get_hash(c, str(t) + filename))
                names.append(get_hash(c, filename + str(t)))
                names.append(get_hash(c, filename + str(t) + extension))

    for c in ciphers:
        names.append(get_hash(c, filename))
        if extension: names.append(get_hash(c, filename + extension))

    # Search in plausible folders too
    folders = [
        '{y}/{m}/',
        '{d}/{m}/{y}/',
        '{y}/{m}/{d}/',
        '{y}/{d}/{m}/',
        '{y}{m}{d}/',
        '{y}{m}/',
        '{y}/'
    ]

    for name in names:
        paths.append(name)

        for folder in folders:
            paths.append(folder.format(y=date.year, m=date.month, d=date.day) + name)

            # if month/day has only one digit, try double digit aswell
            if date.month < 10 or date.day < 10:
                paths.append(folder.format(y=date.year, m='%02d' % date.month, d='%02d' % date.day) + name)

                # try one digit d/m only too
                paths.append(folder.format(y=date.year, m=date.month, d=date.day) + name)
            else:
                # try only one digit d/m
                paths.append(folder.format(y=date.year, m=date.month, d=date.day) + name)

    # Date could be inside filename
    date_formats = [
        '{y}-{m}_{name}{ext}',
        '{d}-{m}-{y}_{name}{ext}',
        '{y}-{m}-{d}_{name}{ext}',
        '{y}-{d}-{m}_{name}{ext}',
        '{y}{m}{d}_{name}{ext}',
        '{y}{m}_{name}{ext}',
        '{y}_{name}{ext}',
    ]

    for date_name in date_formats:
        # 2018-02-01_file
        paths.append(date_name.format(y=date.year, m=date.month, d=date.day, name=filename, ext=''))

        if extension:
            # 2018-02-01_file.jpg
            paths.append(date_name.format(y=date.year, m=date.month, d=date.day, name=filename, ext=extension))

    print '[+] Total paths to check: %d' % len(paths)

    # make requests
    for path in paths:
        url = base_url + '/' + path
        r = s.get(url)
        i += 1

        if r.status_code == 200:
            return url, i
        #else:
            #print '[*] Filename %s does not exist' % path

    return False, i


def http_upload(s, url, data, file_path, file_param, valid_codes):
    tz = None
    t1 = int(time.time())

    r = s.post(url,
               files={file_param: open(file_path, 'rb')},
               data=dict(urlparse.parse_qsl(data)))

    if r.status_code not in valid_codes:
        raise InvalidStatusCode(r.status_code)

    t2 = int(time.time())

    print(r.text)

    # check if response headers contain "Date" header
    # a little bit of hack because some webservers (php built-in one for instance) won't follow rfc2616
    if 'Date' in r.headers:
        split = r.headers['Date'].split(' ')
        newdate = ' '.join(split[:-1]) + ' GMT'

        tz = datetime.datetime.strptime(newdate, '%a, %d %b %Y %H:%M:%S %Z')

    return t1, t2, tz


def run(args):
    s = requests.Session()

    print '[*] File POST parameter name: %s' % (args.file_param)
    print '[*] Local file to upload: %s' % (args.file_path)
    print '[*] Additional POST data: %s' % (args.post_data if args.post_data else 'N/A')

    # Add headers to HTTP session
    s.headers = {'User-Agent': args.user_agent}

    if args.headers:
        for header in args.headers:
            name, val = header[0].split(':')
            s.headers.update({name: val.lstrip()})

    if args.cookies:
        s.headers.update({'Cookie': args.cookies})

    # Try to upload file
    try:
        # save timestamp interval because it might be used to generate a ""random"" filename
        # TODO: make valid status codes customizable in args
        filename = os.path.basename(args.file_path)
        t1, t2, tz = http_upload(s, args.url, args.post_data, args.file_path,
                                 args.file_param, [200, 201, 202, 204])
    except requests.exceptions.RequestException as e:
        print '[-] HTTP exception while trying to upload a file: %s' % str(e)
        sys.exit(1)
    except InvalidStatusCode as e:
        print '[-] Invalid HTTP status code while trying to upload a file: %d' % e.code
        sys.exit(1)

    # Bruteforce path of newly uploaded file
    url, attempts = filepath_bruteforce(s, t1, t2, tz, filename, args.uploads_path)

    if url:
        print '[++] Found location of newly uploaded file [%s] after %d attempts >> %s' % (filename, attempts, url)
    else:
        print '[-] Cannot find uploaded file (%d attempts)' % attempts

    s.close()

if __name__ == '__main__':
    args = parse_args()

    run(args)