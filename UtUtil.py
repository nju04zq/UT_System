#!/usr/bin/env python
# encoding: utf-8

import subprocess
from UtLogger import logger

def exec_cmd(cmd_line):
    logger.debug("Running {0}".format(cmd_line))
    out = ""
    p = subprocess.Popen(cmd_line,
                         stdin=None,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    while True:
        line = p.stdout.readline()
        if line != "":
            logger.debug(line.strip())
            out += line
            continue
        rc = p.poll()
        if rc is not None:
            break

    if rc != 0:
        logger.warning("Fail on {0}".format(cmd_line))

    return rc, out

