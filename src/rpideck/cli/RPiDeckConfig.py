# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
from schema import Schema, And, Or, Use, Optional, SchemaError
import yaml
import io
import os
import logging


class RPiDeckConfig:
    BUTTONS = 8

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

        def validate_step(step):
            base_schema = Schema(
                {
                    "text": str,
                    "type": And(str, lambda t: t in ["ddc", "eiscp"]),
                    "parameters": dict,
                }
            )
            base_schema.validate(step)

            if step["type"] == "ddc":
                PARAMETERS_DDC.validate(step["parameters"])
            elif step["type"] == "eiscp":
                PARAMETERS_EISCP.validate(step["parameters"])
            return step

        KEY_SCHEMA = Schema(
            {
                "position": lambda n: 0 <= n <= self.BUTTONS,
                "icon": str,
                "label": str,
                "steps": [validate_step],
            }
        )
        PAGE_SCHEMA = Schema({"keys": {str: KEY_SCHEMA}})
        return Schema(
            {
                "ddc": object, # TODO: implement this
                "avr": {
                    "ip": str,
                },
                "logging": {
                    "level": And(str, lambda t: t in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                },
                "deck": {
                    "brightness": lambda n: 0 <= n <= 100,
                    "matchSerial": str,
                    "font": str,
                    "highlightColour": str,
                    "pages": [PAGE_SCHEMA],
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
        self.deck = validated["deck"]
        self.logging = validated["logging"]

    def getKeyInfo(self, position, page=0, isPresssedDown=False):
        key_name = None
        key_cfg = None
        page = self.deck["pages"][page]
        if page is None:
            raise Exception(f"no such page {page}")
        for k, v in page["keys"].items():
            if v["position"] == position:
                key_name = k
                key_cfg = v
                break
        if key_cfg is None:
            raise Exception(f"no such key position {position} on page {page}")

        return {
            "name": key_name,
            "icon": os.path.join(self.assets_path, key_cfg["icon"]),
            "font": self.getFont(),
            "label": key_cfg["label"],
            "steps": key_cfg["steps"],
        }

    def getFont(self):
        return os.path.join(self.assets_path, self.deck["font"])
