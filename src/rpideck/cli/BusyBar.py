# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import requests
import logging



class BusyBar:
    def __init__(self, ip, password, logger_name=__name__):
        self.logger = logging.getLogger(logger_name)
        self.ip = ip
        self.password = password

    def cmd(self, cmd, value):
        headers = {"Accept": "application/json"}
        if self.password:
            headers["X-API-Token"] = self.password[0:10]
        url = f"http://{self.ip}/api/"
        if cmd=="input":
            url += f"input?key={value}"
            self.logger.info(f"busybar request: POST {url}")
            response = requests.post(url, headers=headers, data={})
            if response.status_code == 200:
                self.logger.debug(f"busybar response: {response.status_code} {response.text}")
            else:
                self.logger.warning(f"busybar response: {response.status_code} {response.text}")
        else:
            self.logger.warning(f"unsupporrted busybar command: {cmd} {value}")