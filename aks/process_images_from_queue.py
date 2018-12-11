import ast
import style_transfer
import pathlib
import datetime
import time
import os
import logging
import util
import torch
from logging.handlers import RotatingFileHandler


def add_file_handler(logger, log_path):
    """
    :param log_path: the log file to attach the handler to
    """
    handler_format = util.get_handler_format()
    file_handler = RotatingFileHandler(log_path, maxBytes=20000)
    file_handler.setFormatter(handler_format)
    logger.addHandler(file_handler)


def dequeue(bus_service, model_dir, queue, mount_dir, terminate=None):
    """
    :param bus_service: service bus client
    :param model_dir: the directory in storage where models are stored
    :param queue: the name of the queue
    :param terminate: (optional) used for debugging - terminate process instead of stay alive
    """

    logger = logging.getLogger("root")

    # start listening...
    logger.debug("Start listening to queue '{}' on service bus...".format(queue))

    while True:

        # inspect queue
        logger.debug("Peek queue...")
        msg = bus_service.receive_queue_message(queue, peek_lock=True, timeout=30)

        if msg.body is None:
            if terminate:
                logger.debug(
                    "Receiver has timed out, queue is empty. Exiting program..."
                )
                exit(0)
            else:
                logger.debug(
                    "Receiver has timed out, queue is empty. Waiting 1 minute before trying again..."
                )
                time.sleep(60)
                continue

        # get style, input_frame, input_dir & output_dir from msg body
        msg_body = ast.literal_eval(msg.body.decode("utf-8"))

        input_frame = msg_body["input_frame"]
        video_name = msg_body["video_name"]
        input_dir = os.path.join(mount_dir, video_name, util.Storage.INPUT_DIR.value)
        output_dir = os.path.join(mount_dir, video_name, util.Storage.OUTPUT_DIR.value)
        log_dir = os.path.join(mount_dir, video_name, "logs")

        # make output dir if not exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # make log dir if not exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # create a new file handler for style transfer logs
        log_file = "{}.log".format(input_frame.split(".")[0])
        add_file_handler(logger, os.path.join(log_dir, log_file))
        logger.debug("Queue message body: {}".format(msg_body))

        # run style transfer
        logger.debug("Starting style transfer on {}/{}".format(input_dir, input_frame))
        style_transfer.stylize(
            content_scale=None,
            model_dir=os.path.join(mount_dir, model_dir),
            cuda=1 if torch.cuda.is_available() else 0,
            content_dir=input_dir,
            content_filename=input_frame,
            output_dir=output_dir,
        )
        logger.debug("Finished style transfer on {}/{}".format(input_dir, input_frame))

        # delete msg
        logger.debug("Deleting queue message...")
        msg.delete()

        # pop logger handler
        logger.handlers.pop()
