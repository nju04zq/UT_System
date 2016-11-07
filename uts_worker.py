#!/usr/bin/env python
# encoding: utf-8

from UtSession import UtSession

json_input = ["ssh_config.json", "test_script.json", "notify.json"]
session = UtSession(*json_input)
session.prepare()
session.go()
session.send_notify()
