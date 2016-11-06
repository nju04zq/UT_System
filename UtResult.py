#!/usr/bin/env python
# encoding: utf-8

import datetime
from UtScript import UtCmd

class UtResult(object):
    def __init__(self):
        self.start_ts = None
        self.end_ts = None
        self.total = 0
        self.success = 0
        self.rc = None
        self.result = ""

    def set_total(self, total):
        self.total = total

    def inc_success(self):
        self.success += 1

    def record_start_ts(self):
        self.start_ts = datetime.datetime.now()

    def record_end_ts(self):
        self.end_ts = datetime.datetime.now()

    def set_result(self, rc):
        self.rc = rc
        if rc == UtCmd.RC_OK:
            self.result = True
            self.result_str = "succeeded"
        else:
            self.result = False
            self.result_str = "failed"

    def set_run_report(self, report):
        self.run_report = report

    def success_percent(self):
        if self.total == 0:
            return "0%"

        percent = float(self.success)/self.total*100
        return "{0:.1f}%".format(percent)

    def format_interval(self):
        interval = self.end_ts - self.start_ts
        days, seconds = interval.days, interval.seconds
        vals = [days, 0, 0, 0]
        weights = [24, 60, 60]
        total_weight = reduce(lambda x1,x2:x1*x2, weights)
        i = 0
        for w in weights:
            vals[i] += seconds / total_weight
            seconds %= total_weight
            i += 1
            total_weight /= w
        vals[-1] += seconds
        if vals[0] > 0:
            s = "{0}-{1:02d}:{2:02d}:{3:02d}".format(*vals)
        elif vals[1] > 0:
            s = "{0:02d}:{1:02d}:{2:02d}".format(*vals[1:])
        elif vals[2] > 0:
            s = "{0:02d}:{1:02d}".format(*vals[2:])
        elif vals[3] > 10:
            s = "{0:02d} seconds".format(*vals[3:])
        elif vals[3] > 1:
            s = "{0:d} seconds".format(*vals[3:])
        else:
            s = "{0:d} second".format(*vals[3:])
        return s

    def summary(self):
        s = self.result_str
        if self.result == False:
            s += ", {0} passed".format(self.success_percent())
        return s

    def detail(self):
        start_ts = self.start_ts.strftime("%Y-%m-%d %H:%M:%S")
        interval = self.format_interval()
        percent = self.success_percent()
        s = "UT started on {0}, lasted for {1}, {2} passed.\n\n".format(\
            start_ts, interval, percent)
        s += self.run_report
        return s

