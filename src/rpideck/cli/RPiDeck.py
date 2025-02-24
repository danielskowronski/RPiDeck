# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from threading import Thread, Lock
import sched
import time
import datetime
import sys
import signal
from functools import partial
import traceback

import logging

from rpideck.cli.RPiDeckConfig import RPiDeckConfig
from rpideck.cli.DDC import DDCLinux
from rpideck.cli.AVR import AVR


class RPiDeck:
    def __init__(self, config_path="~/.config/rpideck", logger_name=__name__):
        self.logger = logging.getLogger(logger_name)
        print(logger_name)
        self.config = RPiDeckConfig(config_path, logger_name)
        self.display_lock = Lock()
        self.deck = None
        self.page = 0
        self.ddcController = DDCLinux()
        self.avrController = AVR(self.config.avr["ip"])
        sys.excepthook = self.exceptionHandler
        self.clock_scheduler = sched.scheduler(time.time, time.sleep)

    def openDeck(self, matchSerial=""):
        streamdecks = DeviceManager().enumerate()
        signal.signal(signal.SIGINT, partial(self.sigintHandler))
        for deck in streamdecks:
            deck.open()
            self.logger.debug(deck.get_serial_number())
            if matchSerial in deck.get_serial_number():
                self.deck = deck
            deck.close()
        if self.deck is None:
            raise Exception(f"didn't find working deck matching {matchSerial}")
        self.deck.open()
        self.logger.info(
            "Opened '{}' device (serial number: '{}', fw: '{}')".format(
                self.deck.deck_type(),
                self.deck.get_serial_number(),
                self.deck.get_firmware_version(),
            )
        )  # FIXME

    def initializeDeck(self):
        self.deck.reset()
        self.deck.set_poll_frequency(100)
        self.deck.set_brightness(self.config.deck["brightness"])
        self.loadPage(0)
        self.deck.set_key_callback(self.keyChangeCallback)
        self.updateScreenText("RPiDeck started")
        self.clock_scheduler.enter(0.25, 1, self.updateClock)
        self.clock_scheduler.run()

    def loadPage(self, page=0):
        self.page = page
        for key in range(self.deck.key_count()):
            self.updateKeyImage(key, page, False)

    def updateKeyImage(self, position, isPressedDown, page, background="black"):
        try:
            keyInfo = self.config.getKeyInfo(position, self.page, isPressedDown)
            keyImage = self.renderKeyImage(
                keyInfo["icon"], keyInfo["font"], keyInfo["label"], background
            )
            with self.deck:
                self.deck.set_key_image(position, keyImage)
        except Exception:
            with self.deck:
                self.deck.set_key_color(position, 0, 0, 0)

    def renderKeyImage(
        self, icon_filename, font_filename, label_text, background="black"
    ):
        icon = Image.open(icon_filename)
        image = PILHelper.create_scaled_key_image(
            self.deck, icon, margins=[0, 0, 20, 0], background=background
        )
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_filename, 14)
        draw.text(
            (image.width / 2, image.height - 5),
            text=label_text,
            font=font,
            anchor="ms",
            fill="white",
        )
        return PILHelper.to_native_key_format(self.deck, image)

    def updateScreenText(self, text):
        screenImage = self.renderScreenImage(text, self.config.getFont())
        with self.deck:
            self.deck.set_screen_image(screenImage)

    def renderScreenImage(self, text, font_filename):
        image = PILHelper.create_screen_image(self.deck)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_filename, 22)
        draw.text(
            (image.width / 2, image.height - 25),
            text=text,
            font=font,
            anchor="ms",
            fill="white",
        )
        return PILHelper.to_native_screen_format(self.deck, image)

    def executeKeyAction(self, position, page):
        pass
        # TODO: implement logic separation from keyChangeCallback

    def keyChangeCallback(self, deck, position, isPressedDown):
        if position >= self.config.BUTTONS:
            if isPressedDown:
                delta = 0
                if position == self.config.BUTTONS:
                    self.logger.info(f"Key {position} pressed => calling page:previous")
                    delta = -1
                if position == self.config.BUTTONS + 1:
                    self.logger.info(f"Key {position} pressed => calling page:next")
                    delta = +1
                self.page = (self.page + delta) % self.getPageCount()
                self.loadPage(self.page)
            else:
                self.logger.info(f"Key {position} pressed up")
        else:
            keyInfo = self.config.getKeyInfo(position, self.page, isPressedDown)
            actionInfo = f"down => calling {keyInfo['name']}" if isPressedDown else "up"
            self.logger.info(f"Key {position} on page {self.page} pressed {actionInfo}")

            if isPressedDown:
                with self.deck:
                    self.updateKeyImage(
                        position,
                        isPressedDown,
                        self.page,
                        background=self.config.deck["highlightColour"],
                    )
                    with self.display_lock:
                        for step in keyInfo["steps"]:
                            self.updateScreenText(step["text"])
                            params = step["parameters"]
                            if step["type"] == "ddc":
                                self.ddcController.setVCP(
                                    params["vcp"],
                                    params["value"],
                                    params.get("force", False),
                                )
                            elif step["type"] == "eiscp":
                                self.avrController.cmd(params["cmd"], params["value"])
                        self.updateScreenText("callback finished")
                        self.updateKeyImage(position, isPressedDown, self.page)

    def getPageCount(self):
        return len(self.config.deck["pages"])

    def updateClock(self):
        now = datetime.datetime.now()
        if self.getPageCount() == 1:
            text = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                now.year, now.month, now.day, now.hour, now.minute, now.second
            )
        else:
            text = "page {:01d}/{:01d} | {:02d}:{:02d}:{:02d}".format(
                self.page + 1, self.getPageCount(), now.hour, now.minute, now.second
            )
        with self.display_lock:
            self.updateScreenText(text)
        self.clock_scheduler.enter(0.25, 1, self.updateClock)

    def exceptionHandler(self, exctype, value, tb):
        self.logger.exception("".join(traceback.format_exception(exctype, value, tb)))
        self.logger.exception("Uncaught exception: {0}".format(str(value)))

    def sigintHandler(self, sig, frame):
        self.logger.info("SIGINT")
        with self.deck:
            self.deck.reset()
            self.deck.close()
        sys.exit(0)
