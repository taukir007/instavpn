#!/usr/bin/python3
import http.client as httplib
import argparse
import os
import sys
import threading
import urllib
import urllib.parse as urlparse

__version__ = (0, 1, 0)

PASTEE_URL = "https://pastee.org"
DEFAULT_LEXER = "text"
DEFAULT_TTL = 30  # days

class Paste:
    """Class representing a paste that has been submitted."""

    def __init__(self, content, lexer, url):
        """Constructor.

        Args:
          content: paste content
          lexer: lexer used for this paste
          url: URL to access the paste
        """
        self.content = content
        self.lexer = lexer
        self.url = url

    def __str__(self):
        return self.url

class PasteClient:
    """Pasting client for a Pastee application.

    Instances of this class can be used to programmatically create new pastes on
    an installation of Pastee (https://pastee.org).

    This class is thread-safe.
    """

    def __init__(self, url=PASTEE_URL):
        """Constructor.

        Args:
          url: URL to Pastee installation (defaults to https://pastee.org)
        """
        parse = urlparse.urlsplit(url)
        self._scheme = parse.scheme
        self._netloc = parse.netloc
        self._lock = threading.Semaphore()

    def paste(self, content, lexer=None, ttl=None, key=None):
        """Create a new paste.

        Args:
          content: string of text to paste
          lexer: lexer to use (defaults to text)
          ttl: time-to-live in days (defaults to 30)
          key: encrypt paste with this key; if not specified, paste is not
               encrypted

        Returns:
          Paste object
        """
        if lexer is None:
            lexer = DEFAULT_LEXER
        if ttl is None:
            ttl = DEFAULT_TTL

        if self._scheme == "https":
            self._conn = httplib.HTTPSConnection(self._netloc)
        else:
            self._conn = httplib.HTTPConnection(self._netloc)

        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        params = {"lexer": lexer,
                  "content": content,
                  "ttl": int(ttl * 86400)}
        if key is not None:
            params["encrypt"] = "checked"
            params["key"] = key

        self._lock.acquire()
        self._conn.request("POST", "/submit", urllib.parse.urlencode(params), headers)
        response = self._conn.getresponse()
        self._lock.release()
        return self._make_paste(response, content, lexer)

    def paste_file(self, filename, lexer=None, ttl=None, key=None):
        """Create a new paste from a file.

        Args:
          filename: path to file
          lexer: lexer to use (defaults to extension of the file or text)
          ttl: time-to-live in days (defaults to 30)
          key: encrypt paste with this key; if not specified, paste is not
               encrypted

        Returns:
          Paste object
        """
        _, ext = os.path.splitext(filename)
        if lexer is None and ext:
            lexer = ext[1:]  # remove leading period first
        # TODO: need exception handling here
        with open(filename, "r") as fd:
            content = fd.read()
        return self.paste(content, lexer=lexer, ttl=ttl, key=key)

    def _make_paste(self, response, content, lexer):
        for (key, value) in response.getheaders():
            if key.lower() == "location":
                return self._clean_url(value)
        return Paste(content, lexer, self._clean_url(value))

    @staticmethod
    def _clean_url(url):
        p = urlparse.urlsplit(url)
        scheme = p.scheme
        netloc_split = p.netloc.split(":")
        hostname = netloc_split[0]
        if len(netloc_split) > 1:
            port = int(netloc_split[1])
        else:
            port = 443 if scheme == "https" else 80
        path = p.path
        port_str = ""
        if port != 80 and scheme == "http":
            port_str = ":%d" % port
        elif port != 443 and scheme == "https":
            port_str = ":%d" % port
        return "%s://%s%s%s" % (scheme, hostname, port_str, path)

def die_with_error(message):
    """Print a message and exit with exit code 1.

    Args:
      message: message to print before exiting
    """
    print("error: %s" % message)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Create a new paste on Pastee.")
    parser.add_argument("-l", "--lexer", dest="lexer", metavar="LEXERNAME",
                        help=("Force use of a particular lexer (i.e. c, py). "
                              "This defaults to the extension of the supplied "
                              "filenames, or 'text' if pasting from stdin."))
    parser.add_argument("-t", "--ttl", dest="ttl", metavar="DAYS",
                        help="Number of days before the paste will expire.")
    parser.add_argument("-k", "--key", dest="key", metavar="PASSPHRASE",
                        help="Encrypt pastes with this key.")
    parser.add_argument("filenames", metavar="FILE", nargs="*",
                        help="File(s) to paste. If empty, read from stdin.")
    args = parser.parse_args()
    lexer = args.lexer
    key = args.key
    try:
        ttl = float(args.ttl)
    except ValueError:
        die_with_error("floating point number must be passed for TTL")
    except TypeError:
        ttl = None

    client = PasteClient()

    if args.filenames:
        # paste from multiple files
        for filename in args.filenames:
            print(client.paste_file(filename, lexer=lexer, ttl=ttl, key=key))
    else:
        # paste from stdin
        print(client.paste(sys.stdin.read(), lexer=lexer, ttl=ttl, key=key))

if __name__ == "__main__":
    main()
