## JetVisionModel
Run U-net for jetson orin nano super for image ML
CAMERA CAPCTURE -> Jetson -> ESP for disp
                          -> Server for debug

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
sudo apt install python3-evdev
pip install -r requirements.txt

## Enable GPIO
sudo /opt/nvidia/jetson-io/jetson-io.py --show   
    # Configure 40-pin header → enable spi1
# if this does not work, check DTB file:
    sudo mkdir -p /boot/dtb
    sudo rm -rf /boot/dtb/*
    sudo ln -snf /boot/tegra234-p3768-0000+p3767-0005-nv.dtb /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv.dtb
    NPATH=/opt/nvidia/jetson-io:$PYTHONPATH TERM=vt100 /opt/nvidia/jetson-io/jetson-io.py

    sudo reboot

# check CUDA, CuDNN, TensorRT version and ONNX ver
/usr/local/cuda/bin/nvcc --version
    -> Cuda compilation tools, release 12.6, V12.6.68

cat /usr/include/cudnn_version.h | grep CUDNN_MAJOR -A 2
    -> CuDNN Version: 9.3.0

cat /usr/include/aarch64-linux-gnu/NvInferVersion.h | grep NV_TENSORRT
    -> TensorRT Version: 10.3.0

python3 -c "import onnxruntime as ort; print(ort.__version__, ort.get_available_providers())"
    -> 1.24.0 ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']

# download ONNX:
https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#requirements
https://pypi.jetson-ai-lab.io/jp6
    -> Jetpack uses aarch64 so download any version compatible with cuda126, NOW it is 1.24.0

## systemctl service:
sudo cp ~/workspace/JetVisionModel/defectdetect.service /etc/systemd/system/defectdetect.service
sudo systemctl daemon-reload
sudo systemctl enable defectdetect      # start automatically on every boot
sudo systemctl start defectdetect       # start it right now


journalctl -u defectdetect -f           # view cmd

sudo systemctl stop defectdetect        # stop
sudo systemctl disable jetvision        # stop running on boot

sudo systemctl restart jetvision
systemctl status jetvision

# IP
at WPA: 172.26.136.239