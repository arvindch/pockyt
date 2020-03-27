from __future__ import absolute_import, print_function, unicode_literals, with_statement

import json
import os
import re
import sys
import traceback
import webbrowser
from collections import OrderedDict
from os.path import join, realpath

from .api import API
from .compat import urlparse, urlopen, Request, save_webpage


def print_bug_report(message=""):
    """
    Prints a usable bug report
    """

    separator = "\n" + ("-" * 69) + "\n"

    error_message = message or traceback.format_exc().strip()
    python_version = str(sys.version)
    command = " ".join(sys.argv[1:])

    try:
        import pkg_resources
    except ImportError:
        packages_message = "`pkg_resources` is not installed!"
    else:
        packages_message = "\n".join(
            "{0} - {1}".format(package.key, package.version)
            for package in pkg_resources.working_set)

    print("{0}Bug Report :\n"
          "`pockyt` has encountered an error! "
          "Please submit this bug report at \n` {1} `.{0}"
          "Python Version:\n{2}{0}"
          "Installed Packages:\n{3}{0}"
          "Commmand:\n{4}{0}"
          "Error Message:\n{5}{0}".format(
              separator,
              API.ISSUE_URL,
              python_version,
              packages_message,
              command,
              error_message,
          ))


class SuppressedStdout(object):
    """
    Suppresses STDOUT, utilize with the `with` keyword
    """
    def __init__(self):
        self.orig_stdout = sys.stdout.fileno()
        self.copy_stdout = os.dup(self.orig_stdout)
        self.devnull = None

    def __enter__(self):
        self.devnull = open(os.devnull, "w")
        os.dup2(self.devnull.fileno(), self.orig_stdout)

    def __exit__(self, *args):
        os.dup2(self.copy_stdout, self.orig_stdout)
        self.devnull.close()


class Response(object):
    """
    Wraps a urllib request to provide a common python 2/3 API
    """
    def __init__(self, response):
        self._response = response

        self.code = self._get_code()
        self.info = response.info()
        self.encoding = self.get_param("charset") or API.ENCODING
        self.text = response.read().decode(self.encoding)
        self.data = self._get_data()

    def _get_code(self):
        try:  # python 3
            code = self._response._get_code()
        except AttributeError:  # python 2
            code = self._response.getcode()
        return code

    def _get_data(self):
        try:
            data = json.loads(self.text, object_pairs_hook=OrderedDict)
        except ValueError:
            data = {}
        return data

    def get_header(self, key):
        try:  # python 3
            value = self._response.getheader(key)
        except AttributeError:  # python 2
            value = self.info.getheader(key)
        return value

    def get_param(self, key):
        try:  # python 3
            value = self.info.get_param(key)
        except AttributeError:  # python 2
            value = self.info.getparam(key)
        return value

    def get_query(self):
        return urlparse.parse_query(self.text)


class Network(object):
    """
    Safe POST Request, with error-handling
    """
    @staticmethod
    def post_request(link, payload):
        request_data = json.dumps(payload).encode(API.ENCODING)
        headers = {
            "Content-Type": API.CONTENT_TYPE,
            "Content-Length": len(request_data),
        }
        request = Request(link, request_data, headers)
        response = Response(urlopen(request))

        if response.code != 200:
            print_bug_report("API Error {0} ! : {1}".format(
                response.get_header("X-Error-Code"),
                response.get_header("X-Error"),
            ))
            sys.exit(1)
        else:
            return response


class Browser(object):
    """
    Silently open browser windows/tabs
    """
    @staticmethod
    def open(link, new=0, autoraise=True):
        with SuppressedStdout():
            webbrowser.open(
                url=link,
                new=new,
                autoraise=autoraise,
            )

    @classmethod
    def open_new_window(cls, link):
        cls.open(link, new=1)

    @classmethod
    def open_new_tab(cls, link):
        cls.open(link, new=2)


class FileSystem(object):
    """
    Safe filesystem handling
    """
    CLEAN_CHARS = re.compile('[^\w\-_\. ]')

    @classmethod
    def resolve_path(cls, path):
        return realpath(path)

    @classmethod
    def get_safe_path(cls, path, name):
        return join(path, cls.CLEAN_CHARS.sub('_', name))

    @classmethod
    def write_to_file(cls, file, lines):
        with open(realpath(file), "w+") as outfile:
            for line in lines:
                try:
                    outfile.write(line)
                except UnicodeEncodeError:
                    outfile.write(line.encode(API.ENCODING))
