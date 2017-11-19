#!/usr/bin/python
#
# Copyright 2015 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for IrcamFindAndDownload class"""

import os.path
import re
import subprocess
import time
import xattr
import tempfile

from autopkglib import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["IrcamFindAndDownload"]

# XATTR names for Etag and Last-Modified headers
XATTR_ETAG = "%s.etag" % BUNDLE_ID
XATTR_LAST_MODIFIED = "%s.last-modified" % BUNDLE_ID


def getxattr(pathname, attr):
    """Get a named xattr from a file. Return None if not present"""
    if attr in xattr.listxattr(pathname):
        return xattr.getxattr(pathname, attr)
    else:
        return None


class IrcamFindAndDownload(Processor):
    """Downloads a URL to the specified download_dir using curl."""
    description = __doc__
    input_variables = {
        'ircam_username': {
            'description': 'Ircam Forum username.',
            'required': True,
        },
        'ircam_password': {
            'description': 'Ircam Forum password.',
            'required': True,
        },
        're_pattern': {
            'description': 'Regular expression (Python) to match against page.',
            'required': True,
        },
        're_flags': {
            'description': ('Optional array of strings of Python regular '
                            'expression flags. E.g. IGNORECASE.'),
            'required': False,
        },
        'result_output_var_name': {
            'description': ('The name of the output variable that is returned '
                            'by the match. If not specified then a default of '
                            '"match" will be used.'),
            'required': False,
            'default': 'match',
        },
        "url": {
            "required": True,
            "description": "The URL to search.",
        },
        "request_headers": {
            "required": False,
            "description":
                ("Optional dictionary of headers to include with the download "
                 "request.")
        },
        "download_dir": {
            "required": False,
            "description":
                ("The directory where the file will be downloaded to. Defaults "
                 "to RECIPE_CACHE_DIR/downloads."),
        },
        "filename": {
            "required": False,
            "description": "Filename to override the URL's tail.",
        },
        "CHECK_FILESIZE_ONLY": {
            "default": False,
            "required": False,
            "description": ("If True, a server's ETag and Last-Modified "
                            "headers will not be checked to verify whether "
                            "a download is newer than a cached item, and only "
                            "Content-Length (filesize) will be used. This "
                            "is useful for cases where a download always "
                            "redirects to different mirrors, which could "
                            "cause items to be needlessly re-downloaded. "
                            "Defaults to False."),
        },
        "PKG": {
            "required": False,
            "description":
                ("Local path to the pkg/dmg we'd otherwise download. "
                 "If provided, the download is skipped and we just use "
                 "this package or disk image."),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "pathname": {
            "description": "Path to the downloaded file.",
        },
        "last_modified": {
            "description": "last-modified header for the downloaded item.",
        },
        "etag": {
            "description": "etag header for the downloaded item.",
        },
        "download_changed": {
            "description":
                ("Boolean indicating if the download has changed since the "
                 "last time it was downloaded."),
        },
        "url_downloader_summary_result": {
            "description": "Description of interesting results."
        },
        'result_output_var_name': {
            'description': (
                'First matched sub-pattern from input found on the fetched '
                'URL. Note the actual name of variable depends on the input '
                'variable "result_output_var_name" or is assigned a default of '
                '"match."')
        },
    }

    def download_found(self, foundURL, cookiePath):
        # clear any pre-exising summary result
        if 'url_downloader_summary_result' in self.env:
            del self.env['url_downloader_summary_result']

        self.env["last_modified"] = ""
        self.env["etag"] = ""
        existing_file_size = None

        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output("Given %s, no download needed." % self.env["pathname"])
            return

        if not "filename" in self.env:
            # Generate filename.
            filename = foundURL.rpartition("/")[2]
        else:
            filename = self.env["filename"]
        download_dir = (self.env.get("download_dir") or
                        os.path.join(self.env["RECIPE_CACHE_DIR"], "downloads"))
        pathname = os.path.join(download_dir, filename)
        # Save pathname to environment
        self.env["pathname"] = pathname

        # create download_dir if needed
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError, err:
                raise ProcessorError(
                    "Can't create %s: %s" % (download_dir, err.strerror))

        # Create a temp file
        temporary_file = tempfile.NamedTemporaryFile(dir=download_dir,
                                                     delete=False)
        pathname_temporary = temporary_file.name
        # Set permissions on the temp file as curl would set for a newly-downloaded
        # file. NamedTemporaryFile uses mkstemp(), which sets a mode of 0600, and
        # this can cause issues if this item is eventually copied to a Munki repo
        # with the same permissions and the file is inaccessible by (for example)
        # the webserver.
        os.chmod(pathname_temporary, 0644)

        # construct curl command.
        curl_cmd = [self.env['CURL_PATH'],
                    '--silent', '--show-error', '--no-buffer', '--fail',
                    '--dump-header', '-',
                    '--speed-time', '30',
                    '--location',
                    '-b', cookiePath,
                    '--url', foundURL,
                    '--output', pathname_temporary]

        if "request_headers" in self.env:
            headers = self.env["request_headers"]
            for header, value in headers.items():
                curl_cmd.extend(['--header', '%s: %s' % (header, value)])

        # if file already exists and the size is 0, discard it and download
        # again
        if os.path.exists(pathname) and os.path.getsize(pathname) == 0:
            os.remove(pathname)

        # if file already exists, add some headers to the request
        # so we don't retrieve the content if it hasn't changed
        if os.path.exists(pathname):
            existing_file_size = os.path.getsize(pathname)
            etag = getxattr(pathname, XATTR_ETAG)
            last_modified = getxattr(pathname, XATTR_LAST_MODIFIED)
            if etag:
                curl_cmd.extend(['--header', 'If-None-Match: %s' % etag])
            if last_modified:
                curl_cmd.extend(
                    ['--header', 'If-Modified-Since: %s' % last_modified])

        # Open URL.
        proc = subprocess.Popen(curl_cmd, shell=False, bufsize=1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        donewithheaders = False
        maxheaders = 15
        header = {}
        header['http_result_code'] = '000'
        header['http_result_description'] = ''
        while True:
            if not donewithheaders:
                info = proc.stdout.readline().strip('\r\n')
                if info.startswith('HTTP/'):
                    try:
                        header['http_result_code'] = info.split(None, 2)[1]
                        header['http_result_description'] = (
                            info.split(None, 2)[2])
                    except IndexError:
                        pass
                elif ': ' in info:
                    # got a header line
                    part = info.split(None, 1)
                    fieldname = part[0].rstrip(':').lower()
                    try:
                        header[fieldname] = part[1]
                    except IndexError:
                        header[fieldname] = ''
                elif foundURL.startswith('ftp://'):
                    part = info.split(None, 1)
                    responsecode = part[0]
                    if responsecode == '213':
                        # This is the reply to curl's SIZE command on the file
                        # We can map it to the HTTP content-length header
                        try:
                            header['content-length'] = part[1]
                        except IndexError:
                            pass
                    elif responsecode.startswith('55'):
                        header['http_result_code'] = '404'
                        header['http_result_description'] = info
                    elif responsecode == '150' or responsecode == '125':
                        header['http_result_code'] = '200'
                        header['http_result_description'] = info
                        donewithheaders = True
                elif info == '':
                    # we got an empty line; end of headers (or curl exited)
                    if header.get('http_result_code') in [
                            '301', '302', '303']:
                        # redirect, so more headers are coming.
                        # Throw away the headers we've received so far
                        header = {}
                        header['http_result_code'] = '000'
                        header['http_result_description'] = ''
                    else:
                        donewithheaders = True
            else:
                time.sleep(0.1)

            if proc.poll() != None:
                # For small download files curl may exit before all headers
                # have been parsed, don't immediately exit.
                maxheaders -= 1
                if donewithheaders or maxheaders <= 0:
                    break

        retcode = proc.poll()
        if retcode: # Non-zero exit code from curl => problem with download
            curlerr = ''
            try:
                curlerr = proc.stderr.read().rstrip('\n')
                curlerr = curlerr.split(None, 2)[2]
            except IndexError:
                pass

            raise ProcessorError( "Curl failure: %s (exit code %s)" % (curlerr, retcode) )

        # If Content-Length header is present and we had a cached
        # file, see if it matches the size of the cached file.
        # Useful for webservers that don't provide Last-Modified
        # and ETag headers.
        if (not header.get("etag") and \
           not header.get("last-modified")) or \
            self.env["CHECK_FILESIZE_ONLY"]:
            size_header = header.get("content-length")
            if size_header and int(size_header) == existing_file_size:
                self.env["download_changed"] = False
                self.output("File size returned by webserver matches that "
                            "of the cached file: %s bytes" % size_header)
                self.output("WARNING: Matching a download by filesize is a "
                            "fallback mechanism that does not guarantee "
                            "that a build is unchanged.")
                self.output("Using existing %s" % pathname)

                # Discard the temp file
                os.remove(pathname_temporary)

                return

        if header['http_result_code'] == '304':
            # resource not modified
            self.env["download_changed"] = False
            self.output("Item at URL is unchanged.")
            self.output("Using existing %s" % pathname)

            # Discard the temp file
            os.remove(pathname_temporary)

            return

        self.env["download_changed"] = True

        # New resource was downloaded. Move the temporary download file
        # to the pathname
        if os.path.exists(pathname):
            os.remove(pathname)
        try:
            os.rename(pathname_temporary, pathname)
        except OSError:
            raise ProcessorError(
                "Can't move %s to %s" % (pathname_temporary, pathname))

        # save last-modified header if it exists
        if header.get("last-modified"):
            self.env["last_modified"] = (
                header.get("last-modified"))
            xattr.setxattr(
                pathname, XATTR_LAST_MODIFIED,
                header.get("last-modified"))
            self.output(
                "Storing new Last-Modified header: %s"
                % header.get("last-modified"))

        # save etag if it exists
        self.env["etag"] = ""
        if header.get("etag"):
            self.env["etag"] = header.get("etag")
            xattr.setxattr(
                pathname, XATTR_ETAG, header.get("etag"))
            self.output("Storing new ETag header: %s"
                        % header.get("etag"))

        self.output("Downloaded %s" % pathname)
        self.env['url_downloader_summary_result'] = {
            'summary_text': 'The following new items were downloaded:',
            'data': {
                'download_path': pathname,
            }
        }

    def get_url_and_search(self, url, re_pattern, cookiePath, headers=None, flags=None):
        '''Get data from url and search for re_pattern'''
        # pylint: disable=no-self-use
        flag_accumulator = 0
        if flags:
            for flag in flags:
                if flag in re.__dict__:
                    flag_accumulator += re.__dict__[flag]

        re_pattern = re.compile(re_pattern, flags=flag_accumulator)

        try:
            cmd = [self.env['CURL_PATH'], '--location', '-b', cookiePath]
            if headers:
                for header, value in headers.items():
                    cmd.extend(['--header', '%s: %s' % (header, value)])
            cmd.append(url)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            if proc.returncode:
                raise ProcessorError(
                    'Could not retrieve URL %s: %s' % (url, stderr))
        except OSError:
            raise ProcessorError('Could not retrieve URL: %s' % url)

        match = re_pattern.search(content)

        if not match:
            raise ProcessorError('No match found on URL: %s' % url)

        # return the last matched group with the dict of named groups
        return (match.group(match.lastindex or 0), match.groupdict(), )

    def getIrcamAuthCookie(self, cookiePath, headers):
        authURL = 'https://forumnet.ircam.fr:3443//login'

        username = self.env['ircam_username']
        password = self.env['ircam_password']

        dataString = "username={}&password={}&rememberme=forever".format(username, password)

        try:
            cmd = [self.env['CURL_PATH'], '--location', '-b', cookiePath, '-c', cookiePath, '-d', dataString]
            if headers:
                for header, value in headers.items():
                    cmd.extend(['--header', '%s: %s' % (header, value)])
            cmd.append(authURL)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            if proc.returncode:
                raise ProcessorError(
                    'Could not retrieve URL %s: %s' % (authURL, stderr))
        except OSError:
            raise ProcessorError('Could not retrieve URL: %s when attempting to get auth cookie' % authURL)

    def main(self):
        output_var_name = self.env['result_output_var_name']

        headers = self.env.get('request_headers', {})

        flags = self.env.get('re_flags', {})

        temporary_cookie_file = tempfile.NamedTemporaryFile(delete=False)
        cookiePath = temporary_cookie_file.name

        self.getIrcamAuthCookie(cookiePath, headers)

        groupmatch, groupdict = self.get_url_and_search(
            self.env['url'], self.env['re_pattern'], cookiePath, headers, flags)

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        self.output_variables = {}
        for key in groupdict.keys():
            self.env[key] = groupdict[key]
            self.output('Found matching text (%s): %s' % (key, self.env[key], ))
            self.output_variables[key] = {
                'description': 'Matched regular expression group'}

        # Use download_found method to
        self.download_found(self.env[key], cookiePath)

        os.remove(cookiePath)


if __name__ == "__main__":
    PROCESSOR = IrcamFindAndDownload()
    PROCESSOR.execute_shell()
