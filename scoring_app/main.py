from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from process_images_from_queue import dequeue
import util
import logging
import argparse
import os
import sys


if __name__ == "__main__":
    """
    This script is a long running script that will continuously
    pull messages from a specified Service Bus queue. As messages
    are pulled off the queue, it will process the referenced
    image in the queue with the neural style transfer script. All
    processed images will be stored in blob.
    """

    # setup parser
    parser = argparse.ArgumentParser(description="Queue receiver")
    parser.add_argument(
        "--model-dir",
        dest="model_dir",
        help="The directory of the models in blob container.",
        default=os.getenv("STORAGE_MODEL_DIR"),
    )
    parser.add_argument(
        "--namespace",
        dest="namespace",
        help="The name queue's namespace.",
        default=os.getenv("SB_NAMESPACE"),
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
        default=os.getenv("SB_SHARED_ACCESS_KEY_NAME"),
    )
    parser.add_argument(
        "--sb-key-value",
        dest="sb_key_value",
        help="The value for service bus.",
        default=os.getenv("SB_SHARED_ACCESS_KEY_VALUE"),
    )
    parser.add_argument(
        "--storage-mount-dir",
        dest="storage_mount_dir",
        help="The value of the storage mount directory",
        default=os.getenv("MOUNT_DIR", "data")
    )
    parser.add_argument(
        "--terminate",
        dest="terminate",
        action="store_true",
        help="DEBUGGING ONLY - Terminate process if queue is empty.",
        default=False,
    )
    args = parser.parse_args()

    assert args.model_dir is not None
    assert args.namespace is not None
    assert args.queue is not None
    assert args.sb_key_name is not None
    assert args.sb_key_value is not None
    assert args.storage_mount_dir is not None

    # setup logger
    handler_format = util.get_handler_format()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.propagate = False

    # service bus client
    bus_service = ServiceBusService(
        service_namespace=args.namespace,
        shared_access_key_name=args.sb_key_name,
        shared_access_key_value=args.sb_key_value,
    )

    # run dequeue
    dequeue(
        bus_service=bus_service,
        model_dir=args.model_dir,
        queue=args.queue,
        mount_dir=args.storage_mount_dir,
        terminate=args.terminate or os.getenv("TERMINATE"),
    )
