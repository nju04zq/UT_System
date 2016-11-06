#!/usr/bin/env python
# encoding: utf-8

from UtSession import UtSession

session = UtSession("ssh_config.json", "test_script.json", "notify.json")
session.prepare()
session.go()
session.send_notify()
