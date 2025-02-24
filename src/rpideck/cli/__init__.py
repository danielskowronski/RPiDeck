# SPDX-FileCopyrightText: 2025-present Daniel Skowroński <daniel@skowron.ski>
# base on https://github.com/abcminiuser/python-elgato-streamdeck/blob/master/src/example_neo.py by abcminiuser
#
# SPDX-License-Identifier: MIT
import click
import threading
import logging
import coloredlogs
from StreamDeck.Transport.Transport import TransportError
from rpideck.__about__ import __version__
from rpideck.cli.RPiDeck import RPiDeck


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(version=__version__, prog_name="rpideck")
def rpideck():
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        #level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        #handlers=[logging.FileHandler("debug.log", mode="a"), logging.StreamHandler()],
    )

    rd = RPiDeck(
        "~/.config/rpideck"
    )  # FIXME: paramatrize this and split to config and assets path
    logger.setLevel(rd.config.logging["level"])
    coloredlogs.install(level=rd.config.logging["level"])

    rd.openDeck()
    rd.initializeDeck()
    for t in threading.enumerate():
        try:
            t.join()
        except (TransportError, RuntimeError):
            pass
