# RPiDeck

***At this stage, this is a personal project, so many things may be hardcoded***

Python agent enabling Elgato StreamDeck Neo connected to Raspberry Pi 5 running headless (server) system to control various devices including:

- Dell monitor over spare HDMI using MCCS over DDC - inputs, KVM, PBP modes
- Pioneer (Onkyo) AVR - HDMI matrix, audio amplifier source
- TESmart KVM and any other RS232 devices

Future devices to be supported:

- anything from Home Assistant
- multimedia devices connected to AVR using HDMI-CEC
- remote HTTP API with multiple endpoints, aware of KVM connection, especially Kuando BusyLight connected via KVM

[ENV.md](./ENV.md) contains critical information about the environment where this project can be installed.

## Installation

[![PyPI: rpideck](https://img.shields.io/pypi/v/rpideck?style=flat-square&label=PyPI%3A%20rpideck)](https://pypi.org/project/rpideck/)

```bash
pipx install rpideck
```

## CLI usage

Config and assets must be placed under `~/.config/rpideck`. See examples in [example_config](./example_config/).

For now, just run `rpideck` and it'll start main loop. Buttons on last row (next to screen) act as page selectors.
