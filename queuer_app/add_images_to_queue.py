from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
import os
import argparse


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
    This script will take the names of all images inside of a directory in a 
    container in Azure storage and add the name of the images as messages to 
    the Service Bus queue.
    """

    parser = argparse.ArgumentParser(
        description="Add messages to queue based on images in blob storage."
    )
    parser.add_argument(
        "--storage-container",
        dest="storage_container",
        help="The name storage container.",
        default=os.getenv("STORAGE_CONTAINER_NAME")
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
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
    storage_container = args.storage_container
    input_dir = args.input_dir
    storage_account_name = args.storage_account_name
    storage_account_key = args.storage_account_key
    namespace = args.namespace
    queue = args.queue
    sb_key_name = args.sb_key_name
    sb_key_value = args.sb_key_value
    queue_limit = args.queue_limit

    # service bus creds
    bus_service = create_service_bus_client(namespace, sb_key_name, sb_key_value)

    # blob creds
    block_blob_service = create_storage_client(storage_account_name, storage_account_key)

    # list all images in specified blob under directory $input_dir
    blob_iterator = block_blob_service.list_blobs(
        storage_container,
        prefix=input_dir
    )

    # for all images found, add to queue
    print(
        "Adding {} images in the directory '{}' of the storage container '{}' to the queue '{}'.".format(
            queue_limit if queue_limit is not None else "all",
            input_dir, 
            storage_container,
            queue
        )
    )
    for i, blob in enumerate(blob_iterator):
        
        if queue_limit is not None and i >= queue_limit:
            print("Queue limit is reached. Exiting process...")
            exit(0)
            
        print("adding {} to queue...".format(blob.name.split("/")[-1]))
        msg = Message(blob.name.encode())
        bus_service.send_queue_message(queue, msg)
