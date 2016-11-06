#!/usr/bin/env python
# encoding: utf-8

import sys
import json
from UtScript import UtCmd

with open(sys.argv[1], "r") as f:
    script_data = []
    for line in f.readlines():
        script_data.append({UtCmd.CMDLINE:line.strip()})
print json.dumps(script_data)
