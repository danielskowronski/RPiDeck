# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
from schema import Schema, And, Or, Use, Optional, SchemaError
import yaml
import io
import os
import logging

@dataclass
class SerialConfig:
  port: str
  baudrate: int
  bytesize: int
  parity: str
  stopbits: int
  timeout: int

class RPiDeckConfig:
    def _build_schema(self):
        PARAMETERS_DDC = Schema(
            {
                "vcp": lambda n: 0x00 <= n <= 0xFF,
                "value": lambda n: 0x00 <= n <= 0xFFFF,
                Optional("force"): bool,
            }
        )
        PARAMETERS_EISCP = Schema(
            {
                "cmd": str,
                "value": str,
            }
        )
        PARAMETERS_SERIAL = Schema(
            {
                "target": str,
                "bytes": list[lambda n: 0x00 <= n <= 0xFF],
            }
        )

        def validate_step(step):
            base_schema = Schema(
                {
                    "text": str,
                    "type": And(str, lambda t: t in ["ddc", "eiscp", "serial"]),
                    "parameters": dict,
                }
            )
            base_schema.validate(step)

            if step["type"] == "ddc":
                PARAMETERS_DDC.validate(step["parameters"])
            elif step["type"] == "eiscp":
                PARAMETERS_EISCP.validate(step["parameters"])
            elif step["type"] == "serial":
                PARAMETERS_SERIAL.validate(step["parameters"])
            return step

        ACTION_SCHEMA = Schema(
            {
                # TODO: labels here as well?
                "steps": [validate_step],
            }
        )
        KEY_SCHEMA = Schema(
            {
                "icon": str,
                Optional("label"): str,
                "action": str,
            }
        )
        PAGE_SCHEMA = Schema({"title": str, "keys": {int: KEY_SCHEMA}})
        
        SERIAL_SCHEMA = Schema(
          {
            "port": str,
            "baudrate": int,
            "bytesize": int,
            "parity": And(str, lambda t: t in ["Y", "N"]),
            "stopbits": int,
            "timeout": int
          }
        )
        
        return Schema(
            {
                "ddc": object,  # TODO: implement this
                "avr": {
                    "ip": str,
                },
                "serial": {
                    str: Use(lambda d: SerialConfig(**SERIAL_SCHEMA.validate(d))),
                },
                "logging": {
                    "level": And(
                        str,
                        lambda t: t
                        in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    ),
                },
                "actions": {str: ACTION_SCHEMA},
                "deck": {
                    "brightness": lambda n: 0 <= n <= 100,
                    "matchSerial": str,
                    "font": str,
                    "highlightColour": str,
                    "keyLayout": {
                        "actionButtonCount": lambda n: 1 <= n <= 100,
                        "prevButtonId": lambda n: 0 <= n <= 100,
                        "nextButtonId": lambda n: 0 <= n <= 100,
                    },
                    "watchdogTimerSeconds": int,
                    "pages": {int: PAGE_SCHEMA},
                },
            }
        )

    def __init__(self, path, logger_name=__name__):
        self.logger = logging.getLogger(logger_name)
        cfg_path = os.path.join(os.path.expanduser(path), "rpideck.yml")
        self.assets_path = os.path.join(os.path.expanduser(path), "assets")

        with open(cfg_path) as stream:
            self.raw_config = yaml.safe_load(stream)

        self.schema = self._build_schema()
        validated = self.schema.validate(self.raw_config)
        self.ddc = validated["ddc"]
        self.avr = validated["avr"]
        self.serial = validated["serial"]
        self.actions = validated["actions"]
        self.deck = validated["deck"]
        self.logging = validated["logging"]
        self.BUTTONS = self.deck["keyLayout"]["actionButtonCount"]
        self.BUTTON_PREV = self.deck["keyLayout"]["prevButtonId"]
        self.BUTTON_NEXT = self.deck["keyLayout"]["nextButtonId"]

    def getPageInfo(self, page):
        page_cfg = self.deck["pages"][page]
        if page_cfg is None:
            raise Exception(f"no such page {page}")
        return page_cfg

    def getKeyInfo(self, position, page=0, isPresssedDown=False):
        key_name = None
        key_cfg = None
        page_cfg = self.getPageInfo(page)
        button = page_cfg["keys"][position]

        if button is None:
            raise Exception(f"no such key position {position} on page {page}")
        action = self.actions.get(button["action"], {"steps": []})

        return {
            "name": key_name,
            "icon": os.path.join(self.assets_path, button["icon"]),
            "font": self.getFont(),
            "label": button.get("label", None),
            "steps": action["steps"],
        }

    def getFont(self):
        return os.path.join(self.assets_path, self.deck["font"])
