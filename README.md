uv pip install PyQt6 opencv-python-headless websockets pillow numpy requests
uv run --project personalive_client python -m personalive_client.main

sudo modprobe v4l2loopback exclusive_caps=1 card_label="Animage VirtualCam" video_nr=9