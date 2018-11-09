from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
import subprocess
import os
from util import Parser


def add_images_to_queue(
    input_dir,
    output_dir,
    style,
    storage_container,
    queue,
    block_blob_service,
    bus_service,
    queue_limit=None,
):
    """
    :param input_dir: the input directory where the frames are stored
    :param output_dir: the output directory where we want to store the processed frames
    :param style: the name of the style model (excluding .pth)
    :param storage_container: the storage container of the above three params
    :param queue: the queue to add messages to
    :param queue_limit: (optional) an optional queue limit to stop queuing at
    :param block_blob_service: blob client
    :param bus_service: service bus client
    """

    # list all images in specified blob under the frames directory
    blob_iterator = block_blob_service.list_blobs(storage_container, prefix=input_dir)

    # for all images found, add to queue
    print(
        "Adding {} images in the directory '{}' of the storage container '{}' to the queue '{}'.".format(
            queue_limit if queue_limit is not None else "all",
            input_dir,
            storage_container,
            queue,
        )
    )
    count = 0
    for i, blob in enumerate(blob_iterator):
        count += 1
        if queue_limit is not None and i >= queue_limit:
            print("Queue limit is reached. Exiting process...")
            exit(0)

        msg_body = {
            "input_frame": blob.name.split("/")[-1],
            "input_dir": blob.name.split("/")[0],
            "output_dir": output_dir,
            "style": style,
        }
        msg = Message(str(msg_body).encode())
        bus_service.send_queue_message(queue, msg)
    print("All {} images added to queue...".format(count))


if __name__ == "__main__":

    parser = Parser()
    parser.append_add_images_to_queue_args()
    args = parser.return_args()

    assert args.style is not None
    assert args.input_dir is not None
    assert args.output_dir is not None
    assert args.storage_container_name is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None
    assert args.namespace is not None
    assert args.queue is not None
    assert args.sb_key_name is not None
    assert args.sb_key_value is not None

    bus_service = ServiceBusService(
        service_namespace=args.namespace,
        shared_access_key_name=args.sb_key_name,
        shared_access_key_value=args.sb_key_value,
    )

    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    add_images_to_queue(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        style=args.style,
        storage_container=args.storage_container_name,
        queue=args.queue,
        block_blob_service=block_blob_service,
        bus_service=bus_service,
        queue_limit=args.queue_limit,
    )
