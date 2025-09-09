# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import serial
import logging

from rpideck.cli.RPiDeckConfig import SerialConfig

class SERIAL:
    def __init__(self, configMap, logger_name=__name__):
        self.logger = logging.getLogger(logger_name)
        self.configMap = configMap

    def cmd(self, target, bytes):
        targetConfig = self.configMap.get(target)
        if not targetConfig:
            self.logger.error(f"no such target serial config: {target}")
            return
        bytesFormatted=""
        for b in bytes:
            bytesFormatted+=f"{b:#04x} "
        self.logger.info(f"serial cmd: {target} {bytesFormatted}")
        try:
          with serial.Serial(targetConfig.port, targetConfig.baudrate, targetConfig.bytesize, targetConfig.parity, targetConfig.stopbits, targetConfig.timeout) as ser:
              ser.write(serial.to_bytes(bytes))
              resp = str(ser.read_until(b"Write EEPROM"))
              self.logger.info(f"serial cmd: {target} resp: {resp}")
        except Exception as e:
            self.logger.error(f"error opening or writing to serial port {target}")