from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
from preprocess import preprocess
from postprocess import postprocess
from add_images_to_queue import add_images_to_queue
from util import Parser, get_handler_format
from logging.handlers import RotatingFileHandler
from flask import Flask, request
import pathlib
import sys
import logging
import os
import time
import threading

app = Flask(__name__)

def _process(video):
    """
    This route will perform 3 steps:
      1. split video into frames directory and audio file
      2. add frames into service bus queue
      3. this function will poll storage until the number of 
         input images matches the number of processed images
      4. download processed frames and stitch video back together
    """
    # get varaibles from environment
    namespace = os.getenv("SB_NAMESPACE")
    queue = os.getenv("SB_QUEUE")
    sb_key_name = os.getenv("SB_SHARED_ACCESS_KEY_NAME")
    sb_key_value = os.getenv("SB_SHARED_ACCESS_KEY_VALUE")
    mount_dir = os.getenv("MOUNT_DIR", "data")
    terminate = os.getenv("TERMINATE")

    # start time
    t0 = time.time()

    # set video name
    video_name = video.split(".")[0]
    input_dir = os.path.join(mount_dir, video_name, "input_frames")
    output_dir = os.path.join(mount_dir, video_name, "output_frames")
    audio_file = os.path.join(mount_dir, video_name, "audio.aac")

    # create parent directory in mount_dir
    if not os.path.exists(os.path.join(mount_dir, video_name)):
        os.makedirs(os.path.join(mount_dir, video_name))

    # setup logger
    handler_format = get_handler_format()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    log_file = "{}.log".format(video_name)
    file_handler = RotatingFileHandler(
        os.path.join(mount_dir, video_name, log_file), maxBytes=20000
    )
    file_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    # process video and upload output frames and audio file to blob
    logger.debug("Preprocessing video {}".format(video))
    preprocess(video=video, mount_dir=mount_dir)
    t1 = time.time()

    # service bus client
    bus_service = ServiceBusService(
        service_namespace=namespace,
        shared_access_key_name=sb_key_name,
        shared_access_key_value=sb_key_value,
    )

    # add all images from frame_dir to the queue
    logger.debug("Adding images from {} to queue {}".format(input_dir ,queue))
    image_count = add_images_to_queue(
        mount_dir=mount_dir,
        queue=queue,
        video_name=video_name,
        bus_service=bus_service,
    )
    t2 = time.time()

    # terminate if testing
    if terminate:
        exit(0)

    # poll storage for output
    logger.debug(
        "Polling for input images {} to equal output images {}".format(input_dir, output_dir)
    )

    while True:
        path, dirs, files = next(os.walk(output_dir))
        output_frames_length = len(files)

        if output_frames_length == image_count:
            t3 = time.time()

            # postprocess video
            logger.debug(
                "Stitching video together with processed frames dir '{}' and audio file '{}'.".format(
                    output_dir, audio_file 
                )
            )
            postprocess(video_name=video_name, mount_dir=mount_dir)

            t4 = time.time()
            break

        else:
            logger.debug("Images are still processing. Retrying in 10 seconds...")
            time.sleep(10)
            continue

    t5 = time.time()

    logger.debug("Preprocessing video finished.... Time taken in seconds: {:.2f}".format(t1 - t0))
    logger.debug("Adding image to queue finished.. Time taken in seconds: {:.2f}".format(t2 - t1))
    logger.debug("Style transfer.................. Time taken in seconds: {:.2f}".format(t3 - t2))
    logger.debug("Postprocessing video finished... Time taken in seconds: {:.2f}".format(t4 - t3))
    logger.debug("Total process................... Time taken in seconds: {:.2f}".format(t5 - t0))

@app.route('/process', methods=['GET'])
def process_video():
    video_name = request.args.get('video_name')
    threading.Thread(target=_process, args=(video_name,)).start()
    return "Processing {} in background...\n".format(video_name)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

