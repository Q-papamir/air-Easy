# System Requirements for air-Easy.py

## Python
- Python 3.7 or newer
- No third-party pip packages needed (see requirements.txt) — only standard
  library modules are used.

## Operating System
- Linux only (tested workflow assumes a Debian/Ubuntu/Kali-style system).
  The aircrack-ng suite and monitor-mode networking do not work the same
  way on Windows or macOS.
- Root/sudo access is required for several steps (enabling monitor mode,
  scanning, deauth). The script will prompt for your sudo password when
  needed; it is not stored anywhere.

## Required system packages (not pip packages)
Install the aircrack-ng suite, which provides the actual command-line
tools the script wraps (airmon-ng, airodump-ng, aireplay-ng, aircrack-ng):

```bash
sudo apt update
sudo apt install aircrack-ng
```

On Arch:
```bash
sudo pacman -S aircrack-ng
```

On Fedora:
```bash
sudo dnf install aircrack-ng
```

## Hardware
- A wireless network adapter that supports **monitor mode** and **packet
  injection**. Many built-in laptop Wi-Fi chipsets do NOT support this —
  a dedicated USB Wi-Fi adapter with a supported chipset (e.g. Atheros,
  Ralink) is usually needed.

## Optional but useful
- A wordlist file for the cracking step, e.g. `rockyou.txt`
  (commonly found at `/usr/share/wordlists/rockyou.txt` on Kali Linux,
  or downloadable separately).

## Legal reminder
Only run this against networks you own or have explicit written
authorization to test.
