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
sudo /opt/nvidia/jetson-io/jetson-io.py   # Configure 40-pin header → enable spi1
sudo reboot