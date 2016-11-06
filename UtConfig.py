#!/usr/bin/env python
# encoding: utf-8

class UtConfig(object):
    def __init__(self):
        self.root_path = "/Users/Qiang/project/uts_home"
        self.session_dir = "Sessions" 
        self.ssh_config_fname = "ssh_config.json"
        self.script_fname = "script.json"
        self.log_fname = "log.json"

_UT_CONFIG_ = UtConfig()

