# JetVisionModel
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
pip install -r requirements.txt