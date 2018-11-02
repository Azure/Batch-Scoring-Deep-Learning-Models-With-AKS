from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
import subprocess
import os
import argparse


def add_images_to_queue(
    frames_dir,
    storage_container,
    queue,
    queue_limit,
    block_blob_service, 
    bus_service
):

    # list all images in specified blob under the frames directory
    blob_iterator = block_blob_service.list_blobs(
        storage_container,
        prefix=frames_dir
    )

    # for all images found, add to queue
    print(
        "Adding {} images in the directory '{}' of the storage container '{}' to the queue '{}'.".format(
            queue_limit if queue_limit is not None else "all",
            frames_dir, 
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



