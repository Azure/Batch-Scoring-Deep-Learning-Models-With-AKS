from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from util import Parser, get_handler_format
import time
import sys
import subprocess
import os
import logging
from util import Parser


def add_images_to_queue(
    input_dir,
    output_dir,
    storage_container,
    queue,
    block_blob_service,
    bus_service,
    queue_limit=None,
):
    """
    :param input_dir: the input directory where the frames are stored
    :param output_dir: the output directory where we want to store the processed frames
    :param storage_container: the storage container of the above three params
    :param queue: the queue to add messages to
    :param queue_limit: (optional) an optional queue limit to stop queuing at
    :param block_blob_service: blob client
    :param bus_service: service bus client
    """
    t0 = time.time()

    print("Adding images from '{}' in storage to queue '{}'".format(input_dir, queue))

    msg_batch = []
    batch_size = 500
    next_marker = None
    while True:
        # list all images in specified blob under the frames directory
        blob_iterator = block_blob_service.list_blobs(
            storage_container, prefix="{}/".format(input_dir), marker=next_marker
        )
        next_marker = blob_iterator.next_marker

        # for all images found, add to queue
        for i, blob in enumerate(blob_iterator):

            if queue_limit is not None and i >= queue_limit:
                logger.debug("Queue limit is reached. Exiting process...")
                exit(0)

            msg_body = {
                "input_frame": blob.name.split("/")[-1],
                "input_dir": blob.name.split("/")[0],
                "output_dir": output_dir,
            }
            msg = Message(str(msg_body).encode())
            msg_batch.append(msg)

            if i > 0:
                if queue_limit:
                    condition = i % batch_size == 0 or i == queue_limit - 1
                else:
                    condition = (
                        i % batch_size == 0 or i == sum(1 for x in blob_iterator) - 1
                    )

                if condition:
                    # print("{}, length: {}".format(i, len(msg_batch)))
                    bus_service.send_queue_message_batch(queue, msg_batch)
                    msg_batch = []

        if not next_marker:
            break

    t1 = time.time()
    print("Adding image to queue finished. Time taken: {:.2f}".format(t1 - t0))


if __name__ == "__main__":

    parser = Parser()
    parser.append_add_images_to_queue_args()
    args = parser.return_args()

    assert args.input_dir is not None
    assert args.output_dir is not None
    assert args.storage_container is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None
    assert args.namespace is not None
    assert args.queue is not None
    assert args.sb_key_name is not None
    assert args.sb_key_value is not None

    # setup logger
    handler_format = get_handler_format()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.propagate = False

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
        storage_container=args.storage_container,
        queue=args.queue,
        block_blob_service=block_blob_service,
        bus_service=bus_service,
        queue_limit=args.queue_limit,
    )
