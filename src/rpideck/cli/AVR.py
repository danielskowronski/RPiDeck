# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import eiscp


class AVR:
    def __init__(self, ip):
        self.ip = ip

    def cmd(self, cmd, value):
        with eiscp.eISCP(self.ip) as receiver:
            receiver.command(f"{cmd} {value}")
