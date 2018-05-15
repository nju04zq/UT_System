#!/usr/bin/env python

import os
import re
import sys
import time
import signal
import datetime
import traceback
import subprocess

DRYRUN = False

cur_test_block = None

# Ignore SIGTTOU
signal.signal(signal.SIGTTOU, signal.SIG_IGN)

class Colors(object):
    FG_RED_BG_BLACK = "\033[31;40m"
    FG_CYAN_BG_BLACK = "\033[36;40m"
    FG_WHITE_BG_BLACK = "\033[37;40m"
    COLORS_ALL_OFF = "\033[0m"

def format_pretty_timestamp(ts):
    return Colors.FG_WHITE_BG_BLACK + ts + Colors.COLORS_ALL_OFF

def print_pretty_note(msg):
    print Colors.FG_RED_BG_BLACK + msg + Colors.COLORS_ALL_OFF

def print_pretty_info(msg):
    print Colors.FG_CYAN_BG_BLACK + msg + Colors.COLORS_ALL_OFF

def format_pretty_error(msg):
    return Colors.FG_RED_BG_BLACK + msg + Colors.COLORS_ALL_OFF

def print_pretty_error(msg):
    print format_pretty_error(msg)

class PrettyTable(object):
    def __init__(self, header, lines):
        self.header = header
        self.lines = lines
        self.col_limit = self.get_table_col_limit()
        # pad the seperator between columns
        self.col_seperator = "  "

    # print the whole table
    def show(self):
        self.show_table_one_line(self.header)
        self.show_table_seperator()
        for oneline in self.lines:
            self.show_table_one_line(oneline)

    def dump(self, s):
        sys.stdout.write(s)

    # calculate the width limit for each column in table
    def get_table_col_limit(self):
        self.lines.append(self.header)
        col_cnt = len(self.header)
        col_limit = [0 for i in xrange(col_cnt)]
        for line in self.lines:
            if len(line) != col_cnt:
                raise Exception("Table line {0} not match header {1}".format(\
                                line, self.header))
            for i in xrange(len(col_limit)):
                col_limit[i] = max(col_limit[i], len(line[i]))
        self.lines.pop()
        return col_limit

    # print one line in the table, each line is defined by a tuple containing
    # column values. If column value string length is less than the column width
    # limit, extra spaces will be padded
    def show_table_one_line(self, line):
        cols = []
        for i in xrange(len(line)):
            s = ""
            s += line[i]
            s += (" " * (self.col_limit[i]-len(line[i])))
            cols.append(s)
        self.dump(self.col_seperator.join(cols) + "\n")

    # print the seperator as -------
    def show_table_seperator(self):
        sep_cnt = sum(self.col_limit)
        # count in column seperators, why -1?, 2 columns only have one
        sep_cnt += (len(self.col_limit) - 1)*len(self.col_seperator)
        # one extra sep to make it pretty
        sep_cnt += 1
        self.dump("-" * sep_cnt + "\n")

def format_human_readable_time(seconds):
    if seconds < 60:
        return "{0}s".format(seconds)
    minutes = seconds/60
    seconds = seconds%60
    if minutes < 60:
        if seconds == 0:
            return "{0}m".format(minutes)
        else:
            return "{0}m {1}s".format(minutes, seconds)
    hours = minutes/60
    minutes = minutes%60
    if seconds == 0:
        return "{0}h {1}m".format(hours, minutes)
    else:
        return "{0}h {1}m {2}s".format(hours, minutes, seconds)

def log(msg):
    if DRYRUN:
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d %T.%f")
    if "Running cmd: " in msg:
        ts = format_pretty_timestamp(ts)
    print "{ts}: {msg}".format(ts=ts, msg=msg)

class ScriptError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Script Error: " + str(self.value)

class TestError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Test Error: " + str(self.value)

class TestBlock(object):
    def __init__(self, cmdline, cmd_should_fail=False):
        self.cmdline = cmdline
        self.cmd_should_fail = cmd_should_fail
        self.cmd_output = ""
        self.regex_ptn_grp = {}
        self.regex_var_tbl = {}

    def add_regex_ptn(self, regex_ptn):
        if regex_ptn.name in self.regex_ptn_grp:
            raise ScriptError("RegexPtn {0} already exists!".format(\
                              regex_ptn.name))
        else:
            self.regex_ptn_grp[regex_ptn.name] = regex_ptn
        regex_ptn.search(self.cmd_output)

    def add_regex_var(self, regex_var):
        if regex_var.name in self.regex_var_tbl:
            raise ScriptError("RegexVar {0} already exists!".format(\
                              regex_var.name))
        else:
            self.regex_var_tbl[regex_var.name] = regex_var

        if regex_var.regex_ptn_name not in self.regex_ptn_grp:
            err = "RegexVar {0} refers non-exist RegexPtn {1}!".format(\
                  regex_var.name, regex_var.regex_ptn_name)
            raise ScriptError(err)

        regex_ptn = self.regex_ptn_grp[regex_var.regex_ptn_name]
        regex_var.assign(regex_ptn)

    def get_var(self, var_name):
        if var_name not in self.regex_var_tbl:
            raise ScriptError("Var {0} not defined".format(var_name))
        else:
            return self.regex_var_tbl[var_name]

    def is_line_spolier(self, line):
        spoliers = [
            "bash: no job control in this shell",
            "License expires in",
            "Please contact support@tigergraph.com"
        ]
        for spoiler in spoliers:
            if line.startswith(spoiler):
                return True
        else:
            return False

    def dump_output_line(self, line):
        if self.is_line_spolier(line):
            return
        sys.stdout.write(line)
        sys.stdout.flush()

    def save_output_line(self, line):
        if self.is_line_spolier(line):
            return
        self.cmd_output += line

    def dump_cmd(self):
        s = self.cmdline.replace("\n", "\\n")
        return s

    def dump_err_lines(self, lines):
        if lines is None:
            return
        for line in lines:
            if self.is_line_spolier(line):
                continue
            print_pretty_error(line.rstrip("\n"))

    def run_cmd(self):
        if DRYRUN:
            return

        log("Running cmd: " + self.dump_cmd())
        cmdline = ["/bin/bash", "-i", "-c", self.cmdline]
        p = subprocess.Popen(cmdline,
                             stdin=None,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        while True:
            line = p.stdout.readline()
            if line != "":
                self.dump_output_line(line)
                self.save_output_line(line)
                continue
            rc = p.poll()
            if rc is not None:
                break
        self.retrieve_terminal()
        self.dump_err_lines(p.stderr.readlines())

        if rc != 0 and self.cmd_should_fail == False:
            raise TestError("Fail to run cmd {0}".format(self.cmdline))
        elif rc == 0 and self.cmd_should_fail:
            raise TestError("Run cmd {0} should fail".format(self.cmdline))

    def retrieve_terminal(self):
        try:
            os.tcsetpgrp(0, os.getpgrp())
        except OSError:
            pass

    def make_regex_ptn_namespace(self):
        namespace = {}
        for regex_ptn in self.regex_ptn_grp.values():
            namespace[regex_ptn.name] = regex_ptn.ptn_in_output
        return namespace

    def catch_output(self, catch):
        regex_ptn_namespace = self.make_regex_ptn_namespace()
        catch.do_eval(regex_ptn_namespace)

    def make_regex_var_namespace(self):
        namespace = {}
        for regex_var in self.regex_var_tbl.values():
            namespace[regex_var.name] = regex_var.value
        return namespace

    def merge_in_local_var(self, namespace, local_var):
        for var_name in local_var.keys():
            namespace[var_name] = local_var[var_name]

    def evaluate(self, expr_eval, local_var):
        regex_var_namespace = self.make_regex_var_namespace()
        self.merge_in_local_var(regex_var_namespace, local_var)
        expr_eval.do_eval(regex_var_namespace)

class RegexPtn(object):
    def __init__(self, name, ptn):
        self.name = name
        self.ptn = ptn
        self.ptn_in_output = False
        self.match_object = None
        self.validate_regex_ptn()

    def validate_regex_ptn(self):
        try:
            re.compile(self.ptn)
        except Exception as e:
            err = "Compile regex pattern failed, {0}, pattern:\n".format(str(e))
            err += self.ptn
            raise ScriptError(err)

    def search(self, output):
        if DRYRUN:
            return

        m = re.search(self.ptn, output)
        if m is None:
            self.ptn_in_output = False
        else:
            self.ptn_in_output = True
        log("Regex {0} '{1}' result {2}".format(\
            self.name, self.ptn, self.ptn_in_output))
        self.match_object = m

class Expr(object):
    UPPER_OPER = ["AND", "OR", "NOT"]

    def __init__(self, expr):
        self.expr = self.transform_to_python_style(expr)

    def transform_to_python_style(self, expr):
        toks = expr.split()
        for i in xrange(len(toks)):
            if toks[i] in Expr.UPPER_OPER:
                toks[i] = toks[i].lower()
        return " ".join(toks)
    
    def do_eval(self, namespace):
        log("Evaluate {0}, namespace {1}".format(self.expr, namespace))
        try:
            result = eval(self.expr, {}, namespace)
        except:
            raise ScriptError("{0}, {1}".format(\
                              sys.exc_info()[0], sys.exc_info()[1]))

        if not DRYRUN and result == False:
            err = 'Evaluation of expr "{0}" result in False.'.format(self.expr)
            err += str(namespace)
            raise TestError(err)

class Var(object):
    def __init__(self, name):
        self.name = name
        self.value = None

    def set_var_type(self, var_type):
        if DRYRUN:
            expr = "{0}()".format(var_type)
        else:
            expr = "{0}({1})".format(var_type, self.value)
        self.value = eval(expr)

class RegexVar(Var):
    def __init__(self, name, regex_ptn_name, match_group_idx):
        self.name = name
        self.value = None
        self.regex_ptn_name = regex_ptn_name
        self.match_group_idx = match_group_idx

    def assign(self, regex_ptn):
        if DRYRUN:
            return
        try:
            value = regex_ptn.match_object.group(self.match_group_idx)
        except IndexError:
            err = "RegexVar Index {0} exceed limit".format(self.match_group_idx)
            raise ScriptError(err)
        self.value = value
        log("Var {0} value {1}".format(self.name, self.value))

def RUN(cmdline):
    test_block = TestBlock(cmdline)
    global cur_test_block
    cur_test_block = test_block
    cur_test_block.run_cmd()

def RUN_FAIL(cmdline):
    test_block = TestBlock(cmdline, cmd_should_fail=True)
    global cur_test_block
    cur_test_block = test_block
    cur_test_block.run_cmd()

def quote_cmdline(cmdline):
    t = ""
    for ch in cmdline:
        if ch == "\"":
            t += "\\\""
        else:
            t += ch
    return "\"{0}\"".format(t)

def SSH(server, cmdline):
    if server is None:
        RUN(cmdline)
    else:
        cmdline = "ssh {0} {1}".format(server, quote_cmdline(cmdline))
        test_block = TestBlock(cmdline)
        global cur_test_block
        cur_test_block = test_block
        cur_test_block.run_cmd()

def RUN_OUTPUT():
    return cur_test_block.cmd_output

def REGEX(name, ptn):
    regex_ptn = RegexPtn(name, ptn)
    cur_test_block.add_regex_ptn(regex_ptn)

def CATCH(expr):
    catch = Expr(expr)
    cur_test_block.catch_output(catch)

def REGEXVAR(name, regex_ptn_name, match_group_idx):
    regex_var = RegexVar(name, regex_ptn_name, match_group_idx)
    cur_test_block.add_regex_var(regex_var)

def SETVAR(var_name, var_type):
    var = cur_test_block.get_var(var_name)
    var.set_var_type(var_type)

def VARVAL(var_name):
    var = cur_test_block.get_var(var_name)
    return var.value

def EVAL(expr, local_var={}):
    expr_eval = Expr(expr)
    cur_test_block.evaluate(expr_eval, local_var)

def DESC(desc):
    if DRYRUN:
        return

    lines = desc.split("\n")
    func_name = "<" + sys._getframe(1).f_code.co_name + ">"
    lines = [func_name] + lines
    max_line_len = max(len(lines[i]) for i in xrange(len(lines)))

    LINE_START = "* "
    LINE_END = " *"
    head_len = max_line_len + len(LINE_START) + len(LINE_END)

    s = ""
    s += "{0}\n".format("*" * head_len)
    for line in lines:
        spaces = max_line_len - len(line)
        s += "{0}{1}{2}{3}\n".format(LINE_START, line, " "*spaces, LINE_END)
    s += "*" * head_len
    print_pretty_note(s)

def set_dryrun():
    global DRYRUN
    DRYRUN = True

def unset_dryrun():
    global DRYRUN
    DRYRUN = False

_TEST_CASE_STATS_ = {}

class CaseStats(object):
    def __init__(self):
        self.cnt = 0
        self.total = 0
        self.avg = 0

def save_case_runtime(case_name, seconds):
    stats = _TEST_CASE_STATS_
    if case_name in stats:
        stats_entry = stats[case_name]
        stats_entry.cnt += 1
        stats_entry.total += seconds
        stats_entry.avg = stats_entry.total/stats_entry.cnt
    else:
        stats_entry = CaseStats()
        stats[case_name] = stats_entry
        stats_entry.cnt = 1
        stats_entry.total = seconds
        stats_entry.avg = seconds

def get_total_runtime():
    stats = _TEST_CASE_STATS_
    result = reduce(lambda x,y:x+y,[stats[name].total for name in stats.keys()])
    return result

def print_case_runtime_stats():
    lines = []
    stats = _TEST_CASE_STATS_
    case_names = sorted(stats.keys())
    case_names.sort(key=lambda x:stats[x].avg, reverse=True)
    for case_name in case_names:
        stats_entry = stats[case_name]
        avg_time = stats_entry.avg
        avg_time = format_human_readable_time(avg_time)
        total_time = stats_entry.total
        total_time = format_human_readable_time(total_time)
        value = (case_name, str(stats_entry.cnt), avg_time, total_time)
        lines.append(value)
    lines.append(("Total:", "-", "-",\
                 format_human_readable_time(get_total_runtime())))
    print_pretty_info("\nRunning time for all test cases:")
    header = ("Case Name", "N", "Avg Time", "Total Time")
    pretty_table = PrettyTable(header, lines)
    pretty_table.show()
    print

def run_test_case(test_case):
    start = time.time()
    try:
        test_case()
    except:
        msg = ""
        msg += "="*30
        msg += "\n"
        msg +=  "Fail on test case {0}".format(test_case)
        msg += "\n"
        msg += traceback.format_exc()
        print_pretty_error(msg)
        sys.exit(1)
    end = time.time()
    save_case_runtime(test_case.__name__, int(end - start))

def run_specific_test_case(test_case_name, test_cases):
    for test_case in test_cases:
        if test_case.__name__ == test_case_name:
            run_test_case(test_case)
            break
    else:
        print "test case {0} not found.".format(test_case_name)

