import argparse
import os


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
            "--style",
            dest="style",
            help="The style name to use (exclude .pth).",
            default=os.getenv("STYLE"),
        )
        self.parser.add_argument(
            "--video",
            dest="video",
            help="The name of the video in a storage container (including ext).",
            default=os.getenv("VIDEO"),
        )
        self.__append_storage_args()
        self.__append_service_bus_args()

    def append_preprocess_args(self):
        self.parser.add_argument(
            "--frames-dir",
            dest="frames_dir",
            help="the name of the output frames directory in your azure storage container",
            default=None,
        )
        self.parser.add_argument(
            "--video",
            dest="video",
            help="The name of the video in a storage container (including ext).",
            default=os.getenv("VIDEO"),
        )
        self.parser.add_argument(
            "--audio-file",
            dest="audio_file",
            help="the name of the output audio file in your azure storage container",
            default=os.getenv("AUDIO"),
        )
        self.__append_storage_args()

    def append_add_images_to_queue_args(self):
        self.parser.add_argument(
            "--style",
            dest="style",
            help="The style name to use (exclude .pth).",
            default=None,
        )
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

    def __append_storage_args(self):
        self.parser.add_argument(
            "--storage-container-name",
            dest="storage_container_name",
            help="The name storage container.",
            default=os.getenv("STORAGE_CONTAINER_NAME"),
        )
        self.parser.add_argument(
            "--storage-account-name",
            dest="storage_account_name",
            help="The storage account name.",
            default=os.getenv("STORAGE_ACCOUNT_NAME"),
        )
        self.parser.add_argument(
            "--storage-account-key",
            dest="storage_account_key",
            help="The name storage key.",
            default=os.getenv("STORAGE_ACCOUNT_KEY"),
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
