# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import subprocess


class DDCLinux:
    def readVCP(self, vcp):
        current = subprocess.run(
            ["/usr/bin/ddcutil", "getvcp", "--brief", "0x{:02X}".format(vcp)],
            capture_output=True,
            text=True,
        )
        if current.returncode != 0:
            logger.warn(f"getvcp for {vcp} exited with {current.returncode}")
            return None
        current_out = str(current.stdout).split("\n")[0].split(" ")
        current_value = int(f"0{current_out[3]}", 16)  # FIXME: multibyte values
        return current_value

    def setVCP(self, vcp, new_value, force=False):
        if not force:
            current_value = self.readVCP(vcp)
            if current_value is None:
                return
            if current_value == new_value:
                return
        action = subprocess.run(
            [
                "/usr/bin/ddcutil",
                "setvcp",
                "--sleep-multiplier",
                "10",
                "--brief",
                "0x{:02X}".format(vcp),
                "0x{:02X}".format(new_value),
            ],
            capture_output=True,
            text=True,
        )
        # logger.info(action)
