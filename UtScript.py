#!/usr/bin/env python
# encoding: utf-8

import re
import json
from UtLogger import logger

class CmdRegex(object):
    TYPE = "type"
    VALUE = "value"
    TYPE_PTN = "ptn"
    TYPE_OPER = "oper"
    OPER_NOT = "not"
    OPER_AND = "and"
    OPER_OR = "or"

    def __init__(self, regex_data):
        self.validate_regex_data(regex_data)
        if regex_data[self.TYPE] == self.TYPE_PTN:
            self.is_operand = True
            self.ptn = regex_data[self.VALUE]
            self.result = False
        else:
            self.is_operand = False
            self.val = regex_data[self.VALUE]
            if self.val == self.OPER_NOT:
                self.binary = False
                self.priority = 1
            else:
                self.binary = True
                self.priority = 0

    def validate_regex_data(self, regex_data):
        result = ""
        names = [self.TYPE, self.VALUE]
        for name in names:
            if name not in regex_data:
                result += "Missing {0},\n".format(name)

        if result != "":
            result += "cmd:\n{0}".format(regex_data)
            err = "Fail to read in CMD regex:\n" + result
            raise Exception(err)

        data_type = regex_data[self.TYPE]
        if data_type not in [self.TYPE_PTN, self.TYPE_OPER]:
            err = "CMD regex type {0} not supported".format(data_type)
            raise Exception(err)

        value = regex_data[self.VALUE]
        if data_type == self.TYPE_PTN:
            self.validate_regex_pattern(value)
        else:
            defined_values = [self.OPER_NOT, self.OPER_AND, self.OPER_OR]
            if value not in defined_values:
                err = "CMD regex operator {0} not supported".format(value)
                raise Exception(err)

    def validate_regex_pattern(self, ptn):
        try:
            re.compile(ptn)
        except Exception as e:
            err = "Compile regex pattern failed, {0}, pattern:\n".format(str(e))
            err += ptn
            raise Exception(err)

    def match_ptn(self, s):
        rc = re.search(self.ptn, s)
        if rc is None:
            self.result = False
        else:
            self.result = True
        logger.info("Match '{0}', result {1}".format(self.ptn, self.result))

    def operate(self, x1, x2):
        if self.val == self.OPER_NOT:
            result = not x1
        elif self.val == self.OPER_AND:
            result = x1 and x2
        elif self.val == self.OPER_OR:
            result = x1 or x2
        logger.info("Operator {0}, x1 {1}, x2 {2}, result {3}".format(\
                    self.val, x1, x2, result))
        return result

    def notation(self):
        if self.is_operand:
            return "??"
        elif self.val == self.OPER_NOT:
            return "NOT"
        elif self.val == self.OPER_AND:
            return "AND"
        elif self.val == self.OPER_OR:
            return "OR"
        else:
            return "??"

class CmdRegexGrp(object):
    def __init__(self, regex_list):
        self.raw_regex_data = regex_list
        if len(regex_list) == 0:
            self.regex_rpn = []
            return

        self.regex_inorder = []
        for regex_data in regex_list:
            cmd_regex = CmdRegex(regex_data)
            self.regex_inorder.append(cmd_regex)
        self.regex_rpn = self.transform_to_rpn(self.regex_inorder)
        self.validate_regex_list()

    # RPN - Reverse Polish Notation
    def transform_to_rpn(self, list_in):
        list_out = []
        operators = []
        i = 0
        while i < len(list_in):
            cmd_regex = list_in[i]
            if cmd_regex.is_operand:
                list_out.append(cmd_regex)
                i += 1
            elif len(operators) == 0 or \
                 cmd_regex.priority > operators[-1].priority:
                operators.append(cmd_regex)
                i += 1
            else:
                operator = operators.pop()
                list_out.append(operator)
        while len(operators) > 0:
            operator = operators.pop()
            list_out.append(operator)
        return list_out

    def validate_regex_list(self):
        stack, err = [], ""
        for cmd_regex in self.regex_rpn:
            if cmd_regex.is_operand:
                stack.append(cmd_regex)
                continue
            if (cmd_regex.binary and len(stack) < 2) or \
               (not cmd_regex.binary and len(stack) < 1):
                err = "Not enough operands in CMD regex."
                break
            if cmd_regex.binary:
                stack.pop()

        if len(stack) != 1:
            err = "Not enough operators in CMD regex."

        if err != "":
            err += "Regex group:\n{0}".format(self.raw_regex_data)
            raise Exception(err)

    def evaluate(self, s):
        stack = [True]
        results = []
        for cmd_regex in self.regex_rpn:
            if cmd_regex.is_operand:
                cmd_regex.match_ptn(s)
                stack.append(cmd_regex.result)
                results.append(cmd_regex.result)
            elif cmd_regex.binary:
                x1 = stack.pop()
                x2 = stack.pop()
                x3 = cmd_regex.operate(x1, x2)
                stack.append(x3)
            else:
                x1 = stack.pop()
                x2 = cmd_regex.operate(x1, None)
                stack.append(x2)
        if stack[-1] == True:
            return ""

        err = "REGEX evaluation failed,\n"
        err += self.format_evaluation_result(results)
        err += "REGEX list,\n"
        for cmd_regex in self.regex_rpn:
            if cmd_regex.is_operand:
                err += (cmd_regex.ptn + "\n")
        return err
    
    def format_evaluation_result(self, results):
        i, s = 0, ""
        for cmd_regex in self.regex_inorder:
            if cmd_regex.is_operand:
                s += str(results[i])
                i += 1
            else:
                s += cmd_regex.notation()
            s += " "
        return s.strip() + "\n"

class UtCmd(object):
    CMDLINE = "cmdline"
    EXEC_CNT = "exec_cnt"
    RETRY = "retry"
    REGEX = "regex"

    RC_OK = 0
    RC_CMD_FAIL = 1
    RC_REGEX_FAIL = 2

    def __init__(self, cmd_data):
        self.validate_cmd_data(cmd_data)
        self.cmdline = cmd_data[self.CMDLINE]
        if self.EXEC_CNT in cmd_data:
            self.exec_cnt = cmd_data[self.EXEC_CNT]
        else:
            self.exec_cnt = 1
        if self.RETRY in cmd_data:
            self.retry = cmd_data[self.RETRY]
        else:
            self.retry = 0
        if self.REGEX in cmd_data:
            self.regex_grp = CmdRegexGrp(cmd_data[self.REGEX])
        else:
            self.regex_grp = CmdRegexGrp(regex_list=[])

    def validate_cmd_data(self, cmd_data):
        result = ""
        names = [self.CMDLINE]
        for name in names:
            if name not in cmd_data:
                result += "Missing {0},\n".format(name)
        if result != "":
            result += "cmd:\n{0}".format(cmd_data)
            err = "Fail to read in script cmd:\n" + result
            raise Exception(err)

        if self.EXEC_CNT in cmd_data:
            exec_cnt = cmd_data[self.EXEC_CNT]
            if not isinstance(exec_cnt, int):
                err = "CMD exec_cnt should be in int format:\n{0}".format(cmd_data)
                raise Exception(err)
            elif int(exec_cnt) <= 0:
                err = "CMD exec_cnt should larger than 0:\n{0}".format(cmd_data)
                raise Exception(err)

        if self.RETRY in cmd_data:
            retry = cmd_data[self.RETRY]
            if not isinstance(retry, int):
                err = "CMD retry should be in int format:\n{0}".format(cmd_data)
                raise Exception(err)

    def execute(self, ssh):
        logger.info("CMD: Execute cmd '{0}'".format(self.cmdline))
        rc, out, err = ssh.exec_cmd(self.cmdline)
        if rc == False or len(err) > 0:
            logger.info("CMD: Execute return {0}".format(rc))
            return self.RC_CMD_FAIL, out, err
        logger.info("CMD: Evaluate Regex Group, if any")
        err = self.regex_grp.evaluate(out)
        if err != "":
            rc = self.RC_REGEX_FAIL
        else:
            rc = self.RC_OK
        return rc, out, err

class UtScript(object):
    def __init__(self, json_script_fpath):
        with open(json_script_fpath, "r") as f:
            json_script_str = f.read().rstrip()
        script_data = json.loads(json_script_str)
        self.cmd_list = []
        for cmd_data in script_data:
            self.cmd_list.append(UtCmd(cmd_data))

    def total_cmd(self):
        count = 0
        for cmd in self.cmd_list:
            count += cmd.exec_cnt
        return count

    def run_one_cmd(self, cmd, ssh, log, result):
        rc = UtCmd.RC_OK
        for i in xrange(cmd.exec_cnt):
            logger.info("CMD: exec round #{0}".format(i))
            for j in xrange(cmd.retry+1):
                logger.info("CMD: try round #{0}".format(j))
                log.add_action_entry(cmd.cmdline)
                rc, out, err = cmd.execute(ssh)
                log.add_result_entry(rc, out, err)
                if rc == UtCmd.RC_OK:
                    result.inc_success()
                    break
        if rc != UtCmd.RC_OK:
            self.save_last_fail_cmd(cmd, out, err)
        return rc

    def save_last_fail_cmd(self, cmd, out, err):
        self.fail_cmdline = cmd.cmdline
        self.fail_out = out
        self.fail_err = err

    def run(self, session):
        ssh = session.ssh
        log = session.log
        result = session.result
        for cmd in self.cmd_list:
            rc = self.run_one_cmd(cmd, ssh, log, result)
            if rc != UtCmd.RC_OK:
                logger.info("Fail on CMD {0}, exit".format(cmd.cmdline))
                break
        self.rc = rc
        return rc

    def generate_report(self):
        s = ""
        if self.rc == UtCmd.RC_CMD_FAIL:
            s += "Failed to run command:\n"
        elif self.rc == UtCmd.RC_REGEX_FAIL:
            s += "Failed to evaluate REGEX for command:\n"
        if self.rc != UtCmd.RC_OK:
            s += (self.fail_cmdline + "\n")
            s += "Command output:\n"
            s += (self.fail_out + "\n")
            s += "Command error:\n"
            s += (self.fail_err + "\n")
        s += "\n"
        s += self.dump_all_cmd()
        return s

    def dump_all_cmd(self):
        s = "Whole command list:\n"
        for cmd in self.cmd_list:
            s += "{0} {1}\n".format(cmd.exec_cnt, cmd.cmdline)
        return s

