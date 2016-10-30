#!/usr/bin/env python
# encoding: utf-8

import sys
import json
import paramiko

class UtSSH(object):
    HOST_IP = "host_ip"
    HOST_PORT = "host_port"
    USR_NAME = "username"
    USR_PWD = "password"

    def __init__(self, json_config_fpath):
        self.apply_json_config(json_config_fpath)
        self.ssh = paramiko.SSHClient()

    def apply_json_config(self, config_fpath):
        with open(config_fpath, "r") as f:
            config_str = f.read().rstrip()
        config = json.loads(config_str)
        self.validate_input_config(config, config_str)
        self.host_ip = config[self.HOST_IP]
        self.host_port = int(config[self.HOST_PORT])
        self.username = config[self.USR_NAME]
        self.password = config[self.USR_PWD]

    def validate_input_config(self, config, config_str):
        result = ""
        names = [self.HOST_IP, self.HOST_PORT, self.USR_NAME , self.USR_PWD]
        for name in names:
            if name not in config:
                result += "Missing {0},\n".format(name)

        if result != "":
            result += "SSH config:\n{0}".format(config_str)
            err = "Fail to read in SSH config:\n" + result
            raise Exception(err)

        port = config[self.HOST_PORT]
        if not port.isdigit():
            err = "SSH port {0} should be a number".format(port)
            raise Exception(err)

    def ssh_detail(self):
        return "{0}@{1}:{2}".format(self.username, self.host_ip, self.host_port)

    def __str__(self):
        s = self.ssh_detail() + " password " + self.password
        return s

    def connect(self):
        try:
            ssh = self.ssh
            #avoid xxx not found in known_hosts
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host_ip, self.host_port,
                        self.username, self.password)
        except Exception as e:
            err = "SSH {0} failed, {1}".format(self.ssh_detail(), str(e))
            raise Exception(err)

    def exec_cmd(self, cmdline):
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
        return rc, out, err

