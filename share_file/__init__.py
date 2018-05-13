# -*- coding: utf-8 -*-
import threading

from os import path
from mimetypes import types_map
from urllib import request
from urllib.error import URLError
from urllib.parse import quote

from fman import (
    DirectoryPaneCommand, 
    show_alert, 
    show_status_message, 
    clear_status_message,
    YES,
    NO,
)

__author__     = "Usman Mahmood"
__license__    = "MIT"
__version__    = "1.0.1"
__maintainer__ = "Usman Mahmood"

template = "ShareFile\n\n{0}\n\n{1}"

class ShareFile(DirectoryPaneCommand):
    def __call__(self):       
        filepath = self.pane.get_file_under_cursor()
        if not filepath:
            return        
        filepath = filepath.replace('file://', '')
        filename = path.basename(filepath)
        if not path.isfile(filepath):
            msg = "ShareFile: '{0}' is not a file, please select a file.".format(filename) 
            show_status_message(msg, timeout_secs=3)        
            return

        msg = template.format("Share file '{0}'?".format(filename), "")
        response = show_alert(msg, buttons=NO|YES, default_button=YES)

        if response == YES:
            # upload in separate thread so we don't block UI, especially when
            # uploading large (MB) files.
            t = UploadThread(1, filepath, filename)
            t.start()

class UploadThread(threading.Thread):
    def __init__(self, tid, filepath, filename):
        threading.Thread.__init__(self)
        self.thread_id = tid
        self.filepath = filepath
        self.filename = quote(filename)

    def run(self):        
        _, ext = path.splitext(self.filename)

        try:
            mime_type = types_map[ext]
        except KeyError:
            mime_type = "application/octet-stream"

        with open(self.filepath, 'rb') as f:
            data = f.read()

        headers = {
            "Accept"            : "*/*",
            "Accept-Encoding"   : "gzip,deflate",
            "Accept-Language"   : "en-US,en;q=0.8",
            "Connection"        : "keep-alive",
            "Content-Length"    : len(data),
            "Content-Type"      : mime_type,
            "Host"              : "transfer.sh",
            "Origin"            : "https://transfer.sh",
            "Referer"           : "https://transfer.sh/",
            "User-Agent"        : "Mozilla/5.0",
            "X_FILENAME"        : self.filename
        }

        url = "https://transfer.sh/" + self.filename

        req = request.Request(url, data=data, headers=headers, method="PUT")

        try:
            show_status_message("ShareFile: uploading file...")
            with request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    body       = resp.read()
                    share_link = body.decode('utf-8').strip('\n')
                    msg        = template.format(share_link, "")
                else:
                    msg = template.format("Could not upload file",
                                          str(resp.status) + " " + resp.reason)
                clear_status_message()
                show_alert(msg)
        except URLError as e:
            msg = template.format(e.reason, "")
            show_alert(msg)
