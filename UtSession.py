#!/usr/bin/env python
# encoding: utf-8

import os
import datetime
from UtLog import UtLog
from UtSSH import UtSSH
from UtScript import UtScript
from UtResult import UtResult
from UtNotify import UtNotify
from UtConfig import _UT_CONFIG_

class UtSession(object):
    def __init__(self, ssh_config_fpath, script_fpath, notify_fpath):
        self.ses_id = self.init_ses_id()
        self.ses_path = self.init_ses_path()
        self.ssh = UtSSH(ssh_config_fpath)
        self.script = UtScript(script_fpath)
        self.notify = UtNotify(notify_fpath)
        self.log = UtLog(self)
        self.result = UtResult()

    def init_ses_id(self):
        ts_fmt = "%Y%m%d%H%M%S"
        ts = datetime.datetime.now().strftime(ts_fmt)
        pid = os.getpid()
        ses_id = "SES{0}_{1}".format(ts, pid)
        return ses_id

    def init_ses_path(self):
        path = os.path.join(_UT_CONFIG_.root_path, \
                            _UT_CONFIG_.session_dir, self.ses_id)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def prepare(self):
        self.log.init_log_file()
        self.result.set_total(self.script.total_cmd())

    def go(self):
        self.ssh.connect()
        self.result.record_start_ts()
        rc = self.script.run(self)
        self.result.record_end_ts()
        self.result.set_result(rc)
        self.result.set_run_report(self.script.generate_report())
        self.ssh.close()

    def send_notify(self):
        subject = "UTS#{0}, {1}".format(self.ses_id, self.result.summary())
        msg_body = self.result.detail()
        self.notify.sendmail(subject, msg_body)

