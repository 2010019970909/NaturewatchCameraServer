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

# apt-get clean
# apt-get update
# apt-get upgrade -y
# apt-get dist-upgrade -y
# # For some reason I couldn't install libgtk2.0-dev or libgtk-3-dev without running the
# # following line
# # See https://www.raspberrypi.org/forums/viewtopic.php?p=1254646#p1254665 for issue and resolution
# apt-get install -y devscripts debhelper cmake libldap2-dev libgtkmm-3.0-dev libarchive-dev libcurl4-openssl-dev intltool
# apt-get install -y build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libgtk2.0-dev libgtk-3-dev libatlas-base-dev libblas-dev libeigen{2,3}-dev liblapack-dev gfortran python3-dev python3-pip python python3
# apt-get install -y libilmbase25 libopenexr-dev libgstreamer1.0-dev
# apt-get install -y gpac
# apt-get install -y python3-picamera2 --no-install-recommends
# apt-get autoremove -y

# echo "Installing OpenCV"
# pip3 install -U pip setuptools wheel
# pip3 install -U numpy opencv-python-headless

# Copy to installation path
mkdir -p $INSTALLATION_PATH/NaturewatchCameraServer >/dev/null 2>&1
cp -r $DIR $INSTALLATION_PATH >/dev/null 2>&1

pushd $INSTALLATION_PATH
pushd NaturewatchCameraServer

# echo "Installing repo dependencies"
# pip3 install -r requirements-pi.txt

echo "Adding services"
systemctl stop python.naturewatch.service >/dev/null 2>&1
systemctl stop wifisetup.service >/dev/null 2>&1
# mv helpers/python.naturewatch.service /etc/systemd/system/python.naturewatch.service
# mv helpers/wifisetup.service /etc/systemd/system/wifisetup.service# Add service and start it
TEMPLATE="${DIR}/helpers"

echo
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
