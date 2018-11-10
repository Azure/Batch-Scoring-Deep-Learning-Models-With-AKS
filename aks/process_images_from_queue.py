import ast
import style_transfer
import pathlib
import datetime
import time
import os
import logging
import util
from logging.handlers import RotatingFileHandler


def add_file_handler(logger, log_file):
    """
    :param log_file: the log file to attach the handler to
    """
    handler_format = util.get_handler_format()
    file_handler = RotatingFileHandler(log_file, maxBytes=20000)
    file_handler.setFormatter(handler_format)
    logger.addHandler(file_handler)


def download_models(block_blob_service, model_dir, storage_container, tmp_model_dir):
    """
    :param block_blob_service: blob client
    :param model_dir: the model dir in storage
    :param storage_container: the container in storage
    :param tmp_model_dir: the tmp model directory on disk
    """
    logger = logging.getLogger("root")

    models = block_blob_service.list_blobs(
        storage_container, prefix="{}/".format(model_dir)
    )
    logger.debug("Downloading style models from directory {}".format(model_dir))

    model_names = []
    for model in models:
        model_name = model.name.split("/")[-1]
        model_names.append(model_name)
        block_blob_service.get_blob_to_path(
            container_name=storage_container,
            blob_name=model.name,
            file_path=os.path.join(tmp_model_dir, "{}".format(model_name)),
        )

    if len(model_names) > 0:
        logger.debug(
            "The following model were downloaded: [{}]".format(
                ",".join('"{}"'.format(name) for name in model_names)
            )
        )
    else:
        logger.debug("There are no models in the specified location.")
        exit(1)


def dequeue(
    block_blob_service,
    bus_service,
    model_dir,
    storage_container,
    queue,
    terminate=None,
):
    """
    :param block_blob_service: blob client
    :param bus_service: service bus client
    :param model_dir: the directory in storage where models are stored
    :param storage_container: the storage container in blob
    :param queue: the name of the queue
    :param terminate: (optional) used for debugging - terminate process instead of stay alive
    """

    logger = logging.getLogger("root")

    # make .tmp dir and input/output/model folders in it
    tmp_dir = ".tmp"
    tmp_input_dir = os.path.join(tmp_dir, "input")
    tmp_output_dir = os.path.join(tmp_dir, "output")
    tmp_model_dir = os.path.join(tmp_dir, "models")
    tmp_log_dir = os.path.join(tmp_dir, "logs")

    pathlib.Path(tmp_input_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(tmp_output_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(tmp_model_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(tmp_log_dir).mkdir(parents=True, exist_ok=True)

    # download available style models to tmp dir
    start = time.time()
    download_models(block_blob_service, model_dir, storage_container, tmp_model_dir)
    end = time.time()
    logger.debug("It took {} seconds to download style models.".format(end - start))

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

        style = msg_body["style"]
        input_frame = msg_body["input_frame"]
        storage_input_dir = msg_body["input_dir"]
        storage_output_dir = msg_body["output_dir"]
        storage_log_dir = "{}_logs".format(storage_output_dir)

        # create a new file handler for style transfer logs
        log_file = "{}.log".format(input_frame.split(".")[-1])
        add_file_handler(logger, os.path.join(tmp_log_dir, log_file))
        logger.debug("Queue message body: {}".format(msg_body))

        # set input/output file vars
        tmp_input_path = os.path.join(tmp_dir, "input", input_frame)
        tmp_model_path = os.path.join(tmp_dir, "models", style)
        tmp_output_path = os.path.join(tmp_dir, "output", input_frame)
        tmp_log_path = os.path.join(tmp_dir, "logs", log_file)

        # download blob to temp dir
        block_blob_service.get_blob_to_path(
            storage_container,
            os.path.join(storage_input_dir, input_frame),
            tmp_input_path,
        )

        # run style transfer
        logger.debug(
            "Starting style transfer on {}/{}".format(storage_input_dir, input_frame)
        )
        style_transfer.stylize(
            content_scale=None,
            model_dir=tmp_model_dir,
            cuda=1,
            style=style,
            content_dir=tmp_input_dir,
            output_dir=tmp_output_dir,
        )
        logger.debug(
            "Finished style transfer on {}/{}".format(storage_input_dir, input_frame)
        )

        # upload output + log file
        block_blob_service.create_blob_from_path(
            storage_container,
            os.path.join(storage_output_dir, input_frame),
            tmp_output_path,
        )
        block_blob_service.create_blob_from_path(
            storage_container, os.path.join(storage_log_dir, log_file), tmp_log_path
        )
        logger.debug("Uploaded output file and log file to storage")

        # delete tmp
        if os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)
        if os.path.exists(tmp_output_path):
            os.remove(tmp_output_path)

        # delete msg
        logger.debug("Deleting queue message...")
        msg.delete()

        # pop logger handler
        logger.handlers.pop()
