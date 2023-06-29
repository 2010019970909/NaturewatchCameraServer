"""Automatically generate a unique SSID for the MyNaturewatch WiFi hotspot,
based on the Pi's serial number."""
import os
import subprocess

# Get SSID and passphrase from hostapd.conf
host_config_file_path = "/etc/hostapd/hostapd.conf"
host_config_file = open(host_config_file_path, "r").readlines()
current_ssid = host_config_file[2][5:].strip()
print(f"hostapd configuration - SSID: {current_ssid}")

# Generate a unique SSID based on the Pi's serial number
unique_id = subprocess.check_output(
    "sed -n 's/^Serial\s*: 0*//p' /proc/cpuinfo", shell=True)
unique_ssid = f"MyNaturewatch-{unique_id.strip().decode('utf-8')}"

if unique_ssid == current_ssid:
    print("Unique SSID already set, no further action is needed.")
else:
    host_config_file[2] = f"ssid={unique_ssid}\n"
    print("Updating hostapd config with unique SSID...")
    open(host_config_file_path, "w").writelines(host_config_file)
    print("Updated hostapd.conf.")
    os.system("sudo reboot now")
