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
"""See docstring for CurlCookieJar class"""

import os
import subprocess
import tempfile

from autopkglib import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["CurlCookieJar"]


class CurlCookieJar(Processor):
    """Creates a temporary CookieJar file and returns its path as a variable."""
    description = __doc__
    input_variables = {
        'cookiejar_var_name': {
            'description': ('The name of the output variable that will contain '
                            'the path of the jar file. If not specified then '
                            'a default of "cookiejar" will be used.'),
            'required': False,
            'default': 'cookiejar',
        },
        'destination_path': {
            'description': ('Directory where the cookie file will be created. '
                            'Defaults to RECIPE_CACHE_DIR.'),
            'required': False,
        },
        'url': {
            'description': 'URL to download',
            'required': True,
        },
        'request_headers': {
            'description': ('Optional dictionary of headers to include with '
                            'the download request.'),
            'required': False,
        },
        'curl_opts': {
            'description': ('Optional array of curl options to include with '
                            'the download request.'),
            'required': False,
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        'result_output_var_name': {
            'description': (
                'First matched sub-pattern from input found on the fetched '
                'URL. Note the actual name of variable depends on the input '
                'variable "cookiejar_var_name" or is assigned a default of '
                '"cookiejar."')
        },
    }

    def getAuthCookie(self, url, cookiePath, headers=None, opts=None):

        try:
            cmd = [self.env['CURL_PATH'], '--location', '-b', cookiePath, '-c', cookiePath]
            if headers:
                for header, value in headers.items():
                    cmd.extend(['--header', '%s: %s' % (header, value)])
            if opts:
                for item in opts:
                    cmd.extend([item])
            cmd.append(url)
            self.output(cmd)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            self.output(content)
            if proc.returncode:
                raise ProcessorError(
                    'Could not retrieve URL %s: %s' % (url, stderr))
        except OSError:
            raise ProcessorError('Could not retrieve URL: %s' % url)

        return None

    def main(self):

        headers = self.env.get('request_headers', {})
        opts = self.env.get('curl_opts', [])

        cookiejar_var_name = self.env['cookiejar_var_name']
        destination_path = self.env.get(
            'destination_path',
            self.env['RECIPE_CACHE_DIR'])

        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError("Can't create %s: %s"
                                     % (destination_path, err.strerror))

        temporary_cookie_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=destination_path)
        cookiePath = temporary_cookie_file.name

        self.getAuthCookie(self.env['url'], cookiePath, headers, opts)

        self.env[cookiejar_var_name] = cookiePath
        self.output_variables[cookiejar_var_name] = {
            'description': 'Variable to path containing cookiejar file'}


if __name__ == "__main__":
    PROCESSOR = CurlCookieJar()
    PROCESSOR.execute_shell()
