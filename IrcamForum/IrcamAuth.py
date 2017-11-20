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
"""See docstring for IrcamAuth class"""

import os.path
import re
import subprocess
import time
import tempfile

from autopkglib import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["IrcamAuth"]


class IrcamAuth(Processor):
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
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
        'cookie_output_var_name': {
            "required": False,
            "default": "cookieString",
            "description": "Variable name containing the resultant cookie string. Defaults to cookieString.",
        },
        'cookie_input_string': {
            "required": False,
            "default": "",
            "description": "Cookie string to input.",
        },
    }
    output_variables = {
        'cookie_output_var_name': {
            "description": "Variable name containing the resultant cookie string.",
        },
    }

    def main(self):
        cookie_var_name = self.env['cookie_output_var_name']
        cookie_input = self.env['cookie_input_string']

        headers = self.env.get('request_headers', {})

        authURL = self.env['url']

        dataString = "username={}&password={}&rememberme=forever".format(self.env['ircam_username'], self.env['ircam_password'])

        temporary_cookie_file = tempfile.NamedTemporaryFile(delete=False)
        cookiePath = temporary_cookie_file.name

        if 'cookie_input_string' in self.env:
            with open(cookiePath, 'w') as file:
                file.write(cookie_input)

        try:
            cmd = [self.env['CURL_PATH'], '--location', '--silent', '-c', '-', '-d', dataString, '--output', '/dev/null']
            self.output(cmd)
            if headers:
                for header, value in headers.items():
                    cmd.extend(['--header', '%s: %s' % (header, value)])
            if 'cookie_input_string' in self.env:
                cmd.extend(['--cookie', cookiePath])
            cmd.append(authURL)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            if proc.returncode:
                raise ProcessorError(
                    'Could not retrieve URL %s: %s' % (authURL, stderr))
        except OSError:
            raise ProcessorError('Could not retrieve URL: %s when attempting to get auth cookie' % authURL)

        self.output(content)

        # Check returned content doesn't indicate auth failure
        re_pattern = re.compile("Incorrect\susername")
        match = re_pattern.search(content)
        if match:
            raise ProcessorError('Incorrect Ircam Forum authorisation credentials for user {}.'.format(self.env['ircam_username']))
        else:
            self.output('Ircam Forum authorisation successful.')

        # cookieMatch = re.search('Set-Cookie:\s(.*)', content)
        #
        # if cookieMatch:
        #     cookieString = cookieMatch.group(1).strip()
        # else:
        #     raise ProcessorError('No cookies found in headers.')

        self.output_variables = {}
        # self.env[cookie_var_name] = cookieString
        self.env[cookie_var_name] = content
        # self.output('Found cookie: {}'.format(cookieString))
        self.output('Found cookie.')
        self.output_variables[cookie_var_name] = {'description': 'Variable name containing found cookies.'}


if __name__ == "__main__":
    PROCESSOR = IrcamAuth()
    PROCESSOR.execute_shell()
