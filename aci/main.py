from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from preprocess_video import process_video
from add_images_to_queue import add_images_to_queue
import argparse
import os


def create_service_bus_client(namespace, key_name, key_value):
    return ServiceBusService(
        service_namespace=namespace,
        shared_access_key_name=key_name,
        shared_access_key_value=key_value
    )


def create_storage_client(account_name, account_key):
    return BlockBlobService(
        account_name=account_name,
        account_key=account_key
    )


if __name__ == "__main__":
    """
    This module will perform 2 steps:
      1. split video into frames directory and audio file
      2. add frames into service bus queue
    """

    parser = argparse.ArgumentParser(
        description="Add messages to queue based on images in blob storage."
    )
    parser.add_argument(
        "--video",
        dest="video",
        help="the name of the video in a storage container",
        default="{}.mp4".format(os.getenv("VIDEO"))
    )
    parser.add_argument(
        "--storage-container-name",
        dest="storage_container_name",
        help="The name storage container.",
        default=os.getenv("STORAGE_CONTAINER_NAME")
    )
    parser.add_argument(
        "--frames-dir",
        dest="frames_dir",
        help="The name of the image directory in your Azure storage container",
        default="input",
    )
    parser.add_argument(
        "--storage-account-name",
        dest="storage_account_name",
        help="The storage account name.",
        default=os.getenv("STORAGE_ACCOUNT_NAME")
    )
    parser.add_argument(
        "--storage-account-key",
        dest="storage_account_key",
        help="The name storage key.",
        default=os.getenv("STORAGE_ACCOUNT_KEY")
    )
    parser.add_argument(
        "--namespace",
        dest="namespace",
        help="The name queue's namespace.",
        default=os.getenv("SB_NAMESPACE")
    )
    parser.add_argument(
        "--queue",
        dest="queue",
        help="The name of the queue",
        default=os.getenv("SB_QUEUE"),
    )
    parser.add_argument(
        "--sb-key-name",
        dest="sb_key_name",
        help="The key name for service bus.",
        default=os.getenv("SB_SHARED_ACCESS_KEY_NAME")
    )
    parser.add_argument(
        "--sb-key-value",
        dest="sb_key_value",
        help="The value for service bus.",
        default=os.getenv("SB_SHARED_ACCESS_KEY_VALUE")
    )
    parser.add_argument(
        "--queue-limit",
        dest="queue_limit",
        help="The maximum number of items to add to the queue.",
        type=int,
        default=None,
    )
    args = parser.parse_args()


    # blob client
    block_blob_service = create_storage_client(
        args.storage_account_name, 
        args.storage_account_key
    )

    # process video and upload output frames and audio file to blob
    frames_dir, audio = process_video(
        args.video,
        args.storage_container_name,
        block_blob_service
    )

    # service bus client
    bus_service = create_service_bus_client(
        args.namespace, 
        args.sb_key_name, 
        args.sb_key_value
    )

    # add all images from frame_dir to the queue
    add_images_to_queue(
        frames_dir,
        args.storage_container_name,
        args.queue,
        args.queue_limit,
        block_blob_service,
        bus_service
    )



