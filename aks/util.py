import logging
from enum import Enum

class Storage(Enum):
    AUDIO_FILE = "audio.aac"
    INPUT_DIR = "input_frames"
    OUTPUT_DIR = "output_frames"

def get_handler_format():
    return logging.Formatter(
        "%(asctime)s [%(name)s:%(filename)s:%(lineno)s] %(levelname)s - %(message)s"
    )
