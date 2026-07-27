## JetVisionModel
Run U-net for jetson orin nano super for image ML

# New venv with system packages
python3 -m venv --system-site-packages .venv

# activate venv 
source .venv/bin/activate

# deactivate venv
deactivate

# install packages
sudo apt update
sudo apt install python3-opencv
sudo apt install -y python3-spidev
pip install -r requirements.txt

# Enable GPIO
sudo /opt/nvidia/jetson-io/jetson-io.py --show   
    # Configure 40-pin header → enable spi1
# if this does not work, check DTB file:
sudo mkdir -p /boot/dtb
sudo rm -rf /boot/dtb/*
sudo ln -snf /boot/tegra234-p3768-0000+p3767-0005-nv.dtb /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv.dtb
NPATH=/opt/nvidia/jetson-io:$PYTHONPATH TERM=vt100 /opt/nvidia/jetson-io/jetson-io.py

sudo reboot