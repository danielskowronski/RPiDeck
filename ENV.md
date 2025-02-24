# Environment

## Platforms supported

### Operating system

There are two non-directly-portable components used: USB and MCCS over DDC. 

USB should work everywhere LibUSB and HIDAPI are supported, which includes Linux, macOS (Intel and ARM) and Windows. On the software level, DDC works best on Linux with excellent [ddcutil](https://www.ddcutil.com), it seems to work on Windows, and it's a nightmare on non-Intel macOS. macOS supports DDC properly, but no one made a competent ddcutil compatible (providing at least raw read-write to any VCP including multibyte values) utility yet.

### Hardware

While any regular x86 PC with HDMI/DisplayPort and USB should work, I've chosen to run it on an external single-board computer connected to a monitor using a spare HDMI input. The main reason for that is the ability to leave such a small computer always on and make it wake up actual workstations (saving power, bypassing downtimes, not having to decide which workstation in KVM controls the device etc.)

Selected SBC must support both fast and modern USB host controller and proper DDC support in HDMI.

#### USB Host

Some USB hosts like DWC2 found in Raspberry Pi 3B or Zero 2W can't handle Stream Decks, despite tweaks applied. That host was cheap and widely used in Raspberry Pi clones. While it's not about the speed, it seems like the easiest way to determine whether DWC2 is *not* used is to look for an SBC with a USB 3.0 port. 

While Stream Deck will technically work with a bad USB host for a while, it'll quickly crash a device, and you'll need to manually reconnect it. Some more context can be found [here](https://github.com/abcminiuser/python-elgato-streamdeck/issues/154).

There's no way to confirm that DWC2 is the only problematic USB host, but I'd run miles away from any platform which does not adhere to full interface speeds (things like 300Mbps on "Gigabit Ethernet").

#### DDC support

DDC is actually I2C added to various video connectors like HDMI, DisplayPort and even VGA. This means it must be properly exposed as an I2C bus to software. Moreover, an I2C controller onboard handling HDMI must support multibyte operations. Some controllers like DesignWare HDMI can't do that - while most basic MCCS operations should work on single-byte writes, the kernel driver just blacklists DDC over DesignWare HDMI completely (see [this discussion](https://github.com/rockowitz/ddcutil/issues/306) and [kernel patch](https://patchwork.kernel.org/project/dri-devel/patch/20190722181945.244395-1-mka@chromium.org/#22771979)). 

It seems to be the case that most of Rockchip and Amlogic chipsets come withe DesignWare HDMI and thus are incompatible. Some boards may be able to bypass that by using a main I2C controller for GPIO, like [reported for Pine64](https://forum.pine64.org/showthread.php?tid=19462). That said, it looks like the safest options for DDC supporting SoCs are Allwiner and Broadcom.

#### Compatible boards

*Fun fact: both DWC and DesignWare HDMI are products of Synopsys*

Confirmed personally:

- Raspberry Pi 5

Should work:

- Raspberry Pi 4

Confirmed not to work:

- Raspberry Pi 3B (USB)
- Orange Pi 3B (DDC)
- Orange Pi 5+ (DDC)

## Installation on Raspberry Pi 5

Sources:

- https://www.ddcutil.com/config_steps/
- https://www.ddcutil.com/raspberry/#raspberry-pi-4
- https://python-elgato-streamdeck.readthedocs.io/en/stable/pages/installation.html

Assuming Raspbian 64-bit (minimal or desktop) based on Debian Bookwork (default in 2025), install base OS dependencies and configure system so DDC and USB are available to regular users:

```bash
apt update && apt dist-upgrade -y
apt install ddcutil libudev-dev libudev-dev libusb-1.0-0-dev libhidapi-libusb0 python3-dev

echo 'i2c-dev' >> /etc/modules
modprobe i2c-dev

echo 'SUBSYSTEMS=="usb", ATTRS{idVendor}=="0fd9", GROUP="users", TAG+="uaccess"' > /etc/udev/rules.d/10-streamdeck.rules
udevadm control --reload-rules # reconnect USB cable after that
```

Development tools:

```bash
apt install git pipx
pipx install hatch
```

## Running as a systemd service

The simplest way to run this as a service is to create user systemd service. 

I created a dedicated user `rpideck` for that purpose. It's important to keep this user in `i2c` group so it can interact with DDC (e.g. by `sudo usermod -G i2c -a rpideck`; first user in system is usually member of `adm` which covers I2C access). USB access in this scenario was granted by udev rules for group `users` (although it could be safer to get a separate group). 

Then you need to install this package under dedicated user, for example using `pipx install rpideck`. Follow instructions from [README.md](./README.md) to set config file and assets pack.

To define a user systemd service, place the following file as `~/.config/systemd/user/rpideck.service`:

```
[Unit]
Description=RPiDeck
After=network.target
StartLimitIntervalSec=0

[Service]
ExecStart=/home/<USERNAME>/.local/pipx/venvs/rpideck/bin/rpideck
Restart=always
RestartSec=1
KillSignal=SIGINT
TimeoutStopSec=10
RestartKillSignal=SIGINT

[Install]
WantedBy=default.target
```

The final step is to enable it by calling `systemctl --user enable --now rpideck`. Logs can be observed with `journalctl --user -fu rpideck`.
