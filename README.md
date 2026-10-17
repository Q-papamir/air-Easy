# air-Easy

An interactive, step-by-step wrapper around the **aircrack-ng** suite
(`airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng`). Nothing runs
automatically end-to-end — every step prints the exact command it's about
to run and waits for your confirmation first.

## ⚠️ Legal Notice

Only use this tool against:
- Wi-Fi networks **you personally own**, or
- Networks you have **explicit written authorization** to test.

Attacking networks without permission is illegal in most countries. You
are solely responsible for how you use this tool.

## Features

- Confirmation prompt before every single action — nothing is automatic.
- Root/sudo password is requested once (via `sudo -v`) and never written
  to disk; later root commands reuse the cached sudo session instead of
  piping the password into every process (this also avoids the hang that
  happens if you pipe a password into an interactive tool's stdin).
- Walks through the full workflow:
  1. Enable monitor mode (`airmon-ng start`)
  2. Scan nearby networks (`airodump-ng`)
  3. Capture a handshake for a specific target (`airodump-ng --bssid ...`)
  4. (Optional) Send deauth packets (`aireplay-ng --deauth`)
  5. Attempt to crack the handshake with a wordlist (`aircrack-ng -w`)
  6. Disable monitor mode and restore the interface (`airmon-ng stop`)

## Requirements

See `SYSTEM_REQUIREMENTS.md` and `requirements.txt` for full details.

Short version:
- Linux, Python 3.7+ (standard library only, no pip packages needed)
- The `aircrack-ng` suite installed:
  ```bash
  sudo apt install aircrack-ng
  ```
- A wireless adapter that supports monitor mode + packet injection
- (Optional) a wordlist file for the cracking step, e.g. `rockyou.txt`

## Usage

```bash
python3 air_Easy.py
```

You'll be walked through each step with a `[y/N]` confirmation. Enter `y`
to proceed with a step, anything else to skip it.

### Restoring your network after use

If your Wi-Fi doesn't come back automatically after disabling monitor
mode, check `iwconfig` / `ip link show` for any leftover monitor
interface (e.g. `wlan0mon`), stop it manually with
`sudo airmon-ng stop wlan0mon`, then run:

```bash
sudo systemctl restart NetworkManager
```

## Disclaimer

This tool is provided for educational and authorized security-testing
purposes only. The author and any distributor of this script accept no
liability for misuse.
