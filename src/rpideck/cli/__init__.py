# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import click
import os
import sys
import signal
import datetime
import threading
import subprocess
import random
import eiscp

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Transport.Transport import TransportError

import sched, time
import traceback
import logging, coloredlogs
from functools import partial
from threading import Thread, Lock
from rpideck.__about__ import __version__

AVR_IP=os.environ['RPIDECK_AVR_IP']
BRIGHTNESS = 50
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")

display_lock = Lock()

# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, icon_filename, font_filename, label_text, background="black"):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    icon = Image.open(icon_filename)
    image = PILHelper.create_scaled_key_image(deck, icon, margins=[0, 0, 20, 0], background=background)

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image a few pixels from the bottom of the key.
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 14)
    draw.text((image.width / 2, image.height - 5), text=label_text, font=font, anchor="ms", fill="white")
    

    return PILHelper.to_native_key_format(deck, image)


# Generate an image for the screen
def render_screen_image(deck, text, font_filename=os.path.join(ASSETS_PATH, "Roboto-Regular.ttf")):
    image = PILHelper.create_screen_image(deck)
    # Load a custom TrueType font and use it to create an image
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 20)
    draw.text((image.width / 2, image.height - 25), text=text, font=font, anchor="ms", fill="white")

    return PILHelper.to_native_screen_format(deck, image)

PAGE=0
KEYS=[
  [
    {"name": "ddc_nya",   "label": "KVM NYA"},
    {"name": "ddc_corp",  "label": "KVM CORP"},
    {"name": "ddc_hdmi",  "label": "HDMI PBP"},
    {"name": "ddc_power", "label": "Monitor"},
    {"name": "avr_appletv", "label": "AVR AppleTV"},
    {"name": "avr_nya", "label": "AVR NYA Audio"},
    {"name": "avr_nintendo", "label": "AVR Switch"},
    {"name": "avr_playstation", "label": "AVR PS4"},
  ]
]

# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state):
    font = "Roboto-Regular.ttf"
    name = KEYS[PAGE][key]["name"]
    icon = "{}.png".format(name)
    label = KEYS[PAGE][key]["label"]

    # TODO: support switching to other background when state is pressed

    return {
        "name": name,
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": os.path.join(ASSETS_PATH, font),
        "label": label
    }


# Creates a new key image based on the key index, style and current key state
# and updates the image on the StreamDeck.
def update_key_image(deck, key, state, background="black"):
    # Determine what icon and label to use on the generated key.
    key_style = get_key_style(deck, key, state)

    # Generate the custom key with the requested image and label.
    image = render_key_image(deck, key_style["icon"], key_style["font"], key_style["label"], background=background)

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)

def read_ddc(vcp):
    current = subprocess.run(["/usr/bin/ddcutil", "getvcp", "--brief", '0x{:02X}'.format(vcp)], capture_output = True, text = True)
    if current.returncode != 0:
      logger.warn(f"getvcp for {vcp} exited with {current.returncode}")
      return None
    current_out = str(current.stdout).split("\n")[0].split(" ")
    current_value= int(f"0{current_out[3]}", 16)  # FIXME: multibyte values
    return current_value
def ensure_ddc(vcp, new_value, force=False):
    if not force:
        current_value = read_ddc(vcp)
        if current_value is None:
            return

        if current_value==new_value:
          return
    action=subprocess.run(["/usr/bin/ddcutil", "setvcp", "--sleep-multiplier", "10", "--brief", '0x{:02X}'.format(vcp), '0x{:02X}'.format(new_value)], capture_output = True, text = True)
    logger.info(action)

def set_screen_text(deck, text):
  image = render_screen_image(deck, text)
  with deck:
      deck.set_screen_image(image)

# Prints key state change information, updates the key image and performs any
# associated actions when a key is pressed.
def key_change_callback(deck, key, state):
    # Print new key state
    logger.info("Deck {} Key {} = {}".format(deck.id(), key, state))

    # Don't try to set an image for touch buttons but set a random color
    if key >= deck.key_count():
        set_random_touch_color(deck, key)
        return

    # Update the key image based on the new key state.

    # Check if the key is changing to the pressed state.
    if state:
        with deck:
          update_key_image(deck, key, state, "#2E7D32")
          key_style = get_key_style(deck, key, state)
          logger.info(f"Action: {key_style['name']}")
          display_lock.acquire()
          match key_style["name"]:
              case "ddc_nya":
                  set_screen_text(deck, "DDC PBP OFF")
                  ensure_ddc(0xE9, 0x00, True) # PBP off
                  set_screen_text(deck, "DDC input DisplayPort")
                  ensure_ddc(0x60, 0x0F) # INPUT DP
                  set_screen_text(deck, "AVR AppleTV")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('source strm-box')
              case "ddc_corp":
                  set_screen_text(deck, "DDC PBP OFF")
                  ensure_ddc(0xE9, 0x00, True) # PBP off
                  set_screen_text(deck, "DDC input USB-C")
                  ensure_ddc(0x60, 0x19) # INPUT USB-C
              case "ddc_hdmi":
                  set_screen_text(deck, "AVR ON")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('power on')
                  set_screen_text(deck, "DDC PBP OFF")
                  ensure_ddc(0xE9, 0x00, True) # PBP off
                  set_screen_text(deck, "DDC input HDMI-2")
                  ensure_ddc(0x60, 0x12) # INPUT HDMI-2
                  set_screen_text(deck, "DDC PBP 75%-25%")
                  ensure_ddc(0xE9, 0x2A) # PBP 75%-25%
                  set_screen_text(deck, "DDC PBP-SUB DP")
                  ensure_ddc(0xE8, 0x0F) # SUB-INPUT DP
              case "ddc_power":
                  set_screen_text(deck, "AVR AppleTV")
                  ensure_ddc(0xD6, 0x04)
              case "avr_appletv":
                  set_screen_text(deck, "AVR AppleTV")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('source strm-box')
              case "avr_nya":
                  set_screen_text(deck, "AVR MacStudio")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('source tv')
              case "avr_nintendo":
                  set_screen_text(deck, "AVR Nintendo")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('source game')
              case "avr_playstation":
                  set_screen_text(deck, "AVR Playstation")
                  with eiscp.eISCP(AVR_IP) as receiver:
                    receiver.command('source dvd')
          set_screen_text(deck, "Callback finished")
          display_lock.release()
    else:
          update_key_image(deck, key, state, "#000000")



# Set a random color for the specified key
def set_random_touch_color(deck, key):
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)

    deck.set_key_color(key, r, g, b)

def clock(scheduler, deck):
  now=datetime.datetime.now()
  text='{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(now.year, now.month, now.day, now.hour, now.minute, now.second)
  image = render_screen_image(deck, text)
  display_lock.acquire()
  with deck:
      deck.set_screen_image(image)
  scheduler.enter(0.25, 1, clock, (scheduler,deck,))
  display_lock.release()

def signal_handler(deck, sig, frame):
    with deck:
        # Reset deck, clearing all button images.
        deck.reset()

        # Close deck handle, terminating internal worker threads.
        deck.close()
    logger.info("SIGINT")
    sys.exit(0)
def my_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)), exc_info=False)
    logger.exception("Uncaught exception: {0}".format(str(value)), exc_info=False)

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("debug.log", mode='a'),
        logging.StreamHandler()
    ])
coloredlogs.install()
sys.excepthook = my_handler

deck = None

@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="rpideck")
def rpideck():
    logger.info("starting __main__")
    streamdecks = DeviceManager().enumerate()
    if len(streamdecks)!=1:
        logger.error("no or more than one device attached")
        sys.exit(1)

    deck = streamdecks[0]
    deck

    deck.open()
    deck.reset()

    signal.signal(signal.SIGINT, partial(signal_handler, deck))

    logger.info("Opened '{}' device (serial number: '{}', fw: '{}')".format(
        deck.deck_type(), deck.get_serial_number(), deck.get_firmware_version()
    ))

    # Set initial screen brightness to 30%.
    deck.set_poll_frequency(100)
    deck.set_brightness(BRIGHTNESS)

    # Set initial key images.
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)

    # Register callback function for when a key state changes.
    deck.set_key_callback(key_change_callback)

    # Set a screen image
    image = render_screen_image(deck, "Python StreamDeck")
    deck.set_screen_image(image)

    my_scheduler = sched.scheduler(time.time, time.sleep)
    my_scheduler.enter(0.25, 1, clock, (my_scheduler,deck,))
    my_scheduler.run()

    # Wait until all application threads have terminated (for this example,
    # this is when all deck handles are closed).
    for t in threading.enumerate():
        try:
            t.join()
        except (TransportError, RuntimeError):
            pass
