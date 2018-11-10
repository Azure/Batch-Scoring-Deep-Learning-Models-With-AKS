from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from preprocess import preprocess
from postprocess import postprocess
from add_images_to_queue import add_images_to_queue
from util import Parser, get_handler_format
from logging.handlers import RotatingFileHandler
import pathlib
import sys
import logging
import os
import time


if __name__ == "__main__":
    """
    This module will perform 3 steps:
      1. split video into frames directory and audio file
      2. add frames into service bus queue
      3. this function will poll storage until the number of 
         input images matches the number of processed images
      4. download processed frames and stitch video back together
    """
    parser = Parser()
    parser.append_main_args()
    args = parser.return_args()

    assert args.video is not None
    assert args.style is not None
    assert args.storage_container is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None
    assert args.namespace is not None
    assert args.queue is not None
    assert args.sb_key_name is not None
    assert args.sb_key_value is not None

    video_name = args.video.split(".")[0]
    tmp_dir = ".aci_main"
    pathlib.Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    # setup logger
    handler_format = get_handler_format()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    tmp_log_file = "{}.log".format(video_name)
    file_handler = RotatingFileHandler(os.path.join(tmp_dir, tmp_log_file), maxBytes=20000)
    file_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    t0 = time.time()

    # blob client
    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    # process video and upload output frames and audio file to blob
    logger.debug("Preprocessing video {}".format(args.video))
    frames_dir, audio = preprocess(
        block_blob_service=block_blob_service,
        video=args.video,
        storage_container=args.storage_container,
    )
    t1 = time.time()
    logger.debug("Preprocessing video finished. Time taken: {}".format(t1 - t0))

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
    logger.debug("Adding images from {} to queue {}".format(input_dir, args.queue))
    add_images_to_queue(
        input_dir=input_dir,
        output_dir=output_dir,
        style=args.style,
        storage_container=args.storage_container,
        queue=args.queue,
        block_blob_service=block_blob_service,
        bus_service=bus_service,
    )
    t2 = time.time()
    logger.debug("Adding image to queue finished. Time taken: {}".format(t2 - t1))

    # poll storage for output
    logger.debug("Polling for input images {} to equal output images {}".format(input_dir, output_dir))

    input_frames = block_blob_service.list_blobs(
        args.storage_container, prefix="{}/".format(input_dir)
    )
    input_frames_length = sum(1 for x in input_frames)
    output_video = "{}_processed.mp4".format(args.video.split(".")[0])

    while True:
        output_frames = block_blob_service.list_blobs(
            args.storage_container, prefix="{}/".format(output_dir)
        )
        output_frames_length = sum(1 for x in output_frames)
        if output_frames_length == input_frames_length:
            t3 = time.time()
            logger.debug("Polling succeeded, images have finished processing. Time taken: {}".format(t3 - t2))

            # postprocess video
            logger.debug("Stitching video together using processed frames dir '{}' and audio file '{}'.".format(output_dir, audio))
            postprocess(
                block_blob_service=block_blob_service,
                storage_container=args.storage_container,
                frames_dir=output_dir,
                audio_file=audio,
                video_file=output_video,
            )
            t4 = time.time()
            logger.debug("Postprocessing vdeo finished. Time taken: {}".format(t4 - t3))
            break

        else:
            logger.debug("Images are still processing. Retrying in 10 seconds...")
            time.sleep(10)
            continue

    # upload log file to blob
    t5 = time.time()  
    logger.debug("Process ending. Total time taken: {}".format(t5 - t0))
    block_blob_service.create_blob_from_path(
        args.storage_container,
        "{}.log".format(video_name),
        os.path.join(tmp_dir, tmp_log_file)
    )

        
