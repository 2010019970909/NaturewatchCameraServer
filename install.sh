#!/bin/bash
# chmod +x install.sh

# Check for sudo permissions
if [ $EUID != 0 ]; then
    echo "Launch the script as sudo"
    sudo "$0" "$@"
    exit $?
fi

echo "-----------------------------------------"

# Not really used
# echo "$NATUREWATCHCAMERA_VAR"

# Extract argument passed to the script
# $1 is the installation path
INSTALLATION_PATH="$1"
echo "Installation path: $INSTALLATION_PATH"

# Get install.sh parent directory
SOURCE="${BASH_SOURCE:-0}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

apt-get clean
apt-get update
apt-get upgrade -y
apt-get dist-upgrade -y

apt-get install -y python3 python3-pip python3-dev python3-setuptools python3-wheel python3-requests
apt-get install -y python3-picamera2 --no-install-recommends
apt-get install -y git ffmpeg

echo "Installing OpenCV"
# Note: python is now python3 in current distro releases
python ${DIR}/helpers/install_piwheels_dependencies.py opencv-python-headless
python ${DIR}/helpers/install_piwheels_dependencies.py numpy
apt-get autoremove -y
python -m pip install -U numpy
# Install latest Wheel available
python -m pip install -U opencv-python-headless --prefer-binary

# Copy to installation path
mkdir -p $INSTALLATION_PATH/NaturewatchCameraServer >/dev/null 2>&1
cp -r $DIR $INSTALLATION_PATH >/dev/null 2>&1

pushd $INSTALLATION_PATH
pushd NaturewatchCameraServer

echo "Installing repo dependencies"
python -m pip install -r requirements-pi.txt

echo "Adding services"
systemctl stop python.naturewatch.service >/dev/null 2>&1
systemctl stop wifisetup.service >/dev/null 2>&1
# mv helpers/python.naturewatch.service /etc/systemd/system/python.naturewatch.service
# mv helpers/wifisetup.service /etc/systemd/system/wifisetup.service# Add service and start it
TEMPLATE="${DIR}/helpers"


sed -e "s|\${path}|${INSTALLATION_PATH}|" "${TEMPLATE}/python.naturewatch.service" > "/etc/systemd/system/python.naturewatch.service"
sed -e "s|\${path}|${INSTALLATION_PATH}|" "${TEMPLATE}/wifisetup.service" > "/etc/systemd/system/wifisetup.service"


popd
popd

echo "Enabling and starting services"
chmod 644 /etc/systemd/system/python.naturewatch.service
chmod 644 /etc/systemd/system/wifisetup.service
systemctl daemon-reload
systemctl enable python.naturewatch.service
systemctl enable wifisetup.service
systemctl start python.naturewatch.service
systemctl start wifisetup.service
