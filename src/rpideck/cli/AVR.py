# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import eiscp
import logging


class AVR:
    def __init__(self, ip, logger_name=__name__):
        self.logger = logging.getLogger(logger_name)
        self.ip = ip

    def cmd(self, cmd, value):
        expanded_cmd=f"{cmd} {value}"
        self.logger.info(f"eiscp cmd: {expanded_cmd}")
        with eiscp.eISCP(self.ip) as receiver:
            receiver.command(expanded_cmd)
