#!/usr/bin/env python
# encoding: utf-8

import sys
import json
import paramiko
from UtLogger import logger

class UtSSH(object):
    HOST_IP = "host_ip"
    HOST_PORT = "host_port"
    USR_NAME = "username"
    USR_PWD = "password"
    KEY_FILE = "key_file"

    def __init__(self, json_config_fpath):
        self.apply_json_config(json_config_fpath)
        self.ssh = paramiko.SSHClient()

    def apply_json_config(self, config_fpath):
        with open(config_fpath, "r") as f:
            config_str = f.read().rstrip()
        config = json.loads(config_str)
        self.validate_input_config(config, config_str)
        self.host_ip = config[self.HOST_IP]
        self.host_port = config[self.HOST_PORT]
        self.username = config[self.USR_NAME]
        if self.USR_PWD in config:
            self.password = config[self.USR_PWD]
        else:
            self.password = ""
        if self.KEY_FILE in config:
            self.key_file = config[self.KEY_FILE]
        else:
            self.key_file = ""

    def validate_input_config(self, config, config_str):
        result = ""
        names = [self.HOST_IP, self.HOST_PORT, self.USR_NAME]
        for name in names:
            if name not in config:
                result += "Missing {0},\n".format(name)

        if self.USR_PWD not in config and self.KEY_FILE not in config:
            result += "Missing password or key file\n"

        if result != "":
            result += "SSH config:\n{0}".format(config_str)
            err = "Fail to read in SSH config:\n" + result
            raise Exception(err)

        port = config[self.HOST_PORT]
        if not isinstance(port, int):
            err = "SSH port should be in int format"
            raise Exception(err)

    def ssh_detail(self):
        return "{0}@{1}:{2}".format(self.username, self.host_ip, self.host_port)

    def __str__(self):
        s = self.ssh_detail() + " password " + self.password
        return s

    def connect(self):
        logger.info("SSH: connect {0}".format(self.ssh_detail()))
        try:
            ssh = self.ssh
            #avoid xxx not found in known_hosts
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.key_file != "":
                ssh.connect(self.host_ip, self.host_port,
                            self.username, key_filename=self.key_file)
            else:
                ssh.connect(self.host_ip, self.host_port,
                            self.username, self.password)
        except Exception as e:
            err = "SSH {0} failed, {1}".format(self.ssh_detail(), str(e))
            raise Exception(err)

    def close(self):
        self.ssh.close()

    def exec_cmd(self, cmdline):
        logger.info("SSH: Run cmd '{0}'".format(cmdline))
        rc = True
        try:
            stdin, stdout, stderr = self.ssh.exec_command(cmdline)
            out = stdout.read()
            err = stderr.read()
        except Exception as e:
            rc = False
            err = "Fail to exec cmd {0}, {1}, SSH {2}".format(
                     cmdline, str(e), self.ssh_detail)
            out = err
        logger.debug("SSH: exec_cmd rc {0}".format(rc))
        logger.debug("SSH: exec_cmd out:\n{0}".format(out))
        logger.debug("SSH: exec_cmd err:\n{0}".format(err))
        return rc, out, err

