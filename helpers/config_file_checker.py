"""This script checks the configuration file for the SSID and passphrase
and updates the hostapd.conf file if necessary. It also checks for the
presence of the firstboot file and expands the filesystem if necessary."""
import os

# Keep track of whether we've changed any settings
settings_changed = False

# get SSID and passphrase from hostapd.conf
host_config_file_path = "/etc/hostapd/hostapd.conf"
host_config_file = open(host_config_file_path, "r").readlines()
current_ssid = host_config_file[2][5:].strip()
current_passphrase = host_config_file[10][15:].strip()
print(f"hostapd configuration - SSID: {current_ssid}")
print(f"hostapd configuration - Passphrase: {current_passphrase}")

# get SSID and passphrase from user configuration file
user_config_file_path = "/boot/_naturewatch-configuration.txt"
user_config_file = open(user_config_file_path, "r").readlines()
user_set_ssid = user_config_file[1].strip()
user_set_passphrase = user_config_file[3].strip()
print(f"Boot configuration - SSID: {user_set_ssid}")
print(f"Boot configuration - Passphrase: {user_set_passphrase}")

if user_set_ssid == current_ssid:
    print("Config file and hostapd SSIDs match. No need to change them.")
else:
    host_config_file[2] = f"ssid={user_set_ssid}\n"
    print("Updating hostapd config with new SSID...")
    settings_changed = True

if user_set_passphrase == current_passphrase:
    print("Config file and hostapd passphrases match. No need to change them.")
else:
    host_config_file[10] = f"wpa_passphrase={user_set_passphrase}\n"
    print("Updating hostapd config with new passphrase...")
    settings_changed = True

if os.path.isfile("/home/pi/firstboot"):
    os.system("rm /home/pi/firstboot")
    os.system("sudo raspi-config --expand-rootfs")
    settings_changed = True

if settings_changed:
    open(host_config_file_path, "w").writelines(host_config_file)
    print("Updated hostapd.conf.")
    os.system("sudo reboot now")
