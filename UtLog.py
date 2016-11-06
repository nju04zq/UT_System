#!/usr/bin/env python
# encoding: utf-8

import json
import time
import datetime
from UtConfig import UtConfig, _UT_CONFIG_

class LogEntry(object):
    TYPE = "type"
    TS = "ts"

    def get_ts_now(self):
        return int(time.time())

    def to_json(self):
        return ""

    def from_json(self):
        pass

    def to_plain_text(self):
        return ""

    def get_plain_text_time(self):
        return datetime.datetime.fromtimestamp(self.ts).strftime("%H:%M")

class LogEntryAction(LogEntry):
    TYPE_ACTION = "action"
    DESC = "desc"

    def __init__(self, desc):
        self.ts = self.get_ts_now()
        self.desc = desc

    def to_json(self):
        x = {}
        x[self.TYPE] = self.TYPE_ACTION
        x[self.TS] = self.ts
        x[self.DESC] = self.desc
        s = json.dumps(x)
        return s

    def to_plain_text(self):
        ts = self.get_plain_text_time()
        s = "[{0}] ${1}\n".format(ts, self.desc)
        return s

class LogEntryResult(LogEntry):
    TYPE_RESULT = "result"
    RC = "rc"
    OUT = "out"
    ERR = "err"

    def __init__(self, rc=True, out="", err=""):
        self.ts = self.get_ts_now()
        self.rc = rc
        self.out = out.strip()
        self.err = err.strip()

    def to_json(self):
        x = {}
        x[self.TYPE] = self.TYPE_RESULT
        x[self.TS] = self.ts
        x[self.RC] = self.rc
        x[self.OUT] = self.out
        x[self.ERR] = self.err
        s = json.dumps(x)
        return s

    def to_plain_text(self):
        ts = self.get_plain_text_time()
        if self.out == "" and self.err == "":
            out = ""
        elif self.out == "":
            out = self.err
        elif self.err == "":
            out = self.out
        else:
            out = self.out + "\n" + self.err
        s = "[{0}] $".format(ts)
        if out != "":
            s += "\n{0}".format(out)
        s += "\n"
        return s

class UtLog(object):
    def __init__(self, ssh):
        self.fname = _UT_CONFIG_.log_fname
        self.entry_list = []
        self.ssh = ssh

    def init_log_file(self):
        with open(self.fname, "w") as f:
            f.write("[\n\n]\n")

    def add_action_entry(self, desc):
        entry = LogEntryAction(desc)
        self.entry_list.append(entry)
        self.flush_entry(entry.to_json())

    def add_result_entry(self, rc, out, err):
        entry = LogEntryResult(rc, out, err)
        self.entry_list.append(entry)
        self.flush_entry(entry.to_json())

    def flush_entry(self, entry_str):
        with open(self.fname, "a") as f:
            f.truncate(f.tell()-3) #remove the ending \n]\n
            f.seek(f.tell()-3)
            if f.tell() > 3: # 2 = len("\n[\n")
                f.write(",\n")
            f.write(entry_str+"\n]\n")

    def to_plain_text(self):
        s = ""
        for entry in self.entry_list:
            s += entry.to_plain_text()
        return s

