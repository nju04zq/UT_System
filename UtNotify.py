#!/usr/bin/env python
# encoding: utf-8

import os
import json
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

class UtNotify(object):
    RECIPIENT = "recipient"

    def __init__(self, json_notify_fpath):
        with open(json_notify_fpath, "r") as f:
            notify_str = f.read().rstrip()

        notify_data = json.loads(notify_str)
        self.validate_notify_data(notify_data, notify_str)
        self.recipient = notify_data[self.RECIPIENT]

    def validate_notify_data(self, notify_data, notify_str):
        result = ""
        names = [self.RECIPIENT]
        for name in names:
            if name not in notify_data:
                result += "Missing {0},\n".format(name)

        if result != "":
            result += "Notify config:\n{0}".format(notify_str)
            err = "Fail to read in Notify config:\n" + result
            raise Exception(err)

    def sendmail(self, subject, msg_body):
        msg = MIMEText(msg_body)
        msg["From"] = "notify@uts.com"
        msg["To"] = self.recipient
        msg["Subject"] = subject
        p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
        p.communicate(msg.as_string())

