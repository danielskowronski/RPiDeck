# RPiDeck

***At this stage, this is a personal project, so many things may be hardcoded***

Python agent enabling Elgato StreamDeck Neo connected to Raspberry Pi 5 running headless (server) system to control various devices including:

- Dell monitor over spare HDMI using MCCS over DDC - inputs, KVM, PBP modes
- Pioneer (Onkyo) AVR - HDMI matrix, audio amplifier source
- TESmart KVM and any other RS232 devices
- [Busy Bar](https://busy.app/products/busy-bar)

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

## Daemon

It can be run wit user systemd unit. Here's example config to run from pipx:

`~.config/systemd/user/rpideck.service`:

```
[Unit]
Description=RPiDeck
After=network.target
StartLimitIntervalSec=0

[Service]
ExecStart=/home/rpideck/.local/pipx/venvs/rpideck/bin/rpideck
Restart=always
RestartSec=1
KillSignal=SIGINT
TimeoutStopSec=10
RestartKillSignal=SIGINT

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now rpideck
systemctl --user status rpideck
journalctl --user -u rpideck.service
```

Just ensure that user has correct permissions. For now on Ubuntu, this means following:

1. for DDC - group `i2c`
2. for serial port - group `dialout`
