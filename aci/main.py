from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from preprocess import preprocess
from postprocess import postprocess
from add_images_to_queue import add_images_to_queue
from util import Parser
import os
import time


if __name__ == "__main__":
    """
    This module will perform 3 steps:
      1. split video into frames directory and audio file
      2. add frames into service bus queue
      3. <TODO> wait until frames are loaded
      4. download processed frames and stitch video back together
    """
    parser = Parser()
    parser.append_main_args()
    args = parser.return_args()

    assert args.video is not None
    assert args.style is not None
    assert args.storage_container_name is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None
    assert args.namespace is not None
    assert args.queue is not None
    assert args.sb_key_name is not None
    assert args.sb_key_value is not None

    # blob client
    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    # process video and upload output frames and audio file to blob
    frames_dir, audio = preprocess(
        block_blob_service=block_blob_service,
        video=args.video,
        storage_container_name=args.storage_container_name,
    )

    # service bus client
    bus_service = ServiceBusService(
        service_namespace=args.namespace,
        shared_access_key_name=args.sb_key_name,
        shared_access_key_value=args.sb_key_value,
    )

    # set output_dir
    input_dir = frames_dir
    output_dir = "{}_processed".format(frames_dir)

    # add all images from frame_dir to the queue
    add_images_to_queue(
        input_dir=input_dir,
        output_dir=output_dir,
        style=args.style,
        storage_container=args.storage_container_name,
        queue=args.queue,
        block_blob_service=block_blob_service,
        bus_service=bus_service,
    )

    # get num of output input frames
    input_frames = block_blob_service.list_blobs(
        args.storage_container_name, prefix="{}/".format(input_dir)
    )
    input_frames_length = sum(1 for x in input_frames)
    output_video = "{}_processed.mp4".format(args.video.split(".")[0])

    # poll storage for output
    print("Polling directory {} in storage for output.".format(output_dir))
    while True:
        output_frames = block_blob_service.list_blobs(
            args.storage_container_name, prefix="{}/".format(output_dir)
        )
        output_frames_length = sum(1 for x in output_frames)
        if output_frames_length == input_frames_length:
            print("Images have finished processing. Stitching video together.")
            postprocess(
                block_blob_service=block_blob_service,
                storage_container=args.storage_container_name,
                frames_dir=output_dir,
                audio_file=audio,
                video_file=output_video,
            )
            break

        else:
            print("Images are still processing. Retrying in 10 seconds...")
            time.sleep(10)
            continue
