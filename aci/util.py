import argparse
import logging
import os


def get_handler_format():
    return logging.Formatter(
        "%(asctime)s [%(name)s:%(filename)s:%(lineno)s] %(levelname)s - %(message)s"
    )


class Parser:
    """
    Parsing utility for this module
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser()

    def return_args(self):
        return self.parser.parse_args()

    def append_main_args(self):
        self.parser.add_argument(
            "--video",
            dest="video",
            help="The name of the video in a storage container (including ext).",
            default=os.getenv("VIDEO"),
        )
        self.__append_storage_args()
        self.__append_service_bus_args()

    def append_postprocess_args(self):
        self.__append_video_args()

    def append_preprocess_args(self):
        self.__append_video_args()

    def append_add_images_to_queue_args(self):
        self.parser.add_argument(
            "--input-dir",
            dest="input_dir",
            help="The name of the input frames directory in your azure storage container.",
            default=None,
        )
        self.parser.add_argument(
            "--output-dir",
            dest="output_dir",
            help="The name of the output frames directory in your azure storage container.",
            default=None,
        )
        self.parser.add_argument(
            "--queue-limit",
            dest="queue_limit",
            help="The maximum number of items to add to the queue.",
            type=int,
            default=None,
        )
        self.__append_storage_args()
        self.__append_service_bus_args()

    def __append_video_args(self):
        self.parser.add_argument(
            "--frames-dir",
            dest="frames_dir",
            help="the name of the output frames directory in your azure storage container",
            default=None,
        )
        self.parser.add_argument(
            "--video",
            dest="video",
            help="The name (not path) of the video in a storage container (including ext).",
            default=os.getenv("VIDEO"),
        )
        self.parser.add_argument(
            "--audio",
            dest="audio",
            help="the name of the output audio file in your azure storage container",
            default=os.getenv("AUDIO"),
        )
        self.__append_storage_args()

    def __append_storage_args(self):
        self.parser.add_argument(
            "--storage-mount-dir",
            dest="storage_mount_dir",
            help="The mount directory connected to the azure blob storage container",
            default=os.getenv("MOUNT_DIR", "/data"),
        )

    def __append_service_bus_args(self):
        self.parser.add_argument(
            "--namespace",
            dest="namespace",
            help="The name queue's namespace.",
            default=os.getenv("SB_NAMESPACE"),
        )
        self.parser.add_argument(
            "--queue",
            dest="queue",
            help="The name of the queue",
            default=os.getenv("SB_QUEUE"),
        )
        self.parser.add_argument(
            "--sb-key-name",
            dest="sb_key_name",
            help="The key name for service bus.",
            default=os.getenv("SB_SHARED_ACCESS_KEY_NAME"),
        )
        self.parser.add_argument(
            "--sb-key-value",
            dest="sb_key_value",
            help="The value for service bus.",
            default=os.getenv("SB_SHARED_ACCESS_KEY_VALUE"),
        )
