from azure.servicebus import ServiceBusService, Message, Queue
from azure.storage.blob import BlockBlobService
import ast
import argparse
import fast_style_transfer
import pathlib
import datetime
import time
import os
import logging
from logging.handlers import RotatingFileHandler
import sys


if __name__ == "__main__":
    """
    TODO
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
        "--storage-container",
        dest="storage_container",
        help="The name storage container.",
        default=os.getenv("STORAGE_CONTAINER_NAME"),
    )
    parser.add_argument(
        "--storage-account-name",
        dest="storage_account_name",
        help="The storage account name.",
        default=os.getenv("STORAGE_ACCOUNT_NAME"),
    )
    parser.add_argument(
        "--storage-account-key",
        dest="storage_account_key",
        help="The name storage key.",
        default=os.getenv("STORAGE_ACCOUNT_KEY"),
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
        "--dequeue-limit",
        dest="dequeue_limit",
        type=int,
        help="DEBUGGING ONLY - The number of items to dequeue before terminating this process.",
        default=None,
    )
    parser.add_argument(
        "--terminate",
        dest="terminate",
				action="store_true",
        help="DEBUGGING ONLY - Terminate process if queue is empty.",
        default=False,
    )
    args = parser.parse_args()

    model_dir = args.model_dir
    dequeue_limit = args.dequeue_limit
    storage_container = args.storage_container
    storage_account_name = args.storage_account_name
    storage_account_key = args.storage_account_key
    namespace = args.namespace
    queue = args.queue
    sb_key_name = args.sb_key_name
    sb_key_value = args.sb_key_value
    terminate_if_queue_is_empty = args.terminate

    assert model_dir is not None
    assert storage_container is not None
    assert storage_account_name is not None
    assert storage_account_key is not None
    assert namespace is not None
    assert queue is not None
    assert sb_key_name is not None
    assert sb_key_value is not None

    # setup logger
    handler_format = logging.Formatter(
        "%(asctime)s [%(name)s:%(filename)s:%(lineno)s] %(levelname)s - %(message)s"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.propagate = False

    # make .tmp dir and input/output/model folders in it
    pathlib.Path(".tmp/input").mkdir(parents=True, exist_ok=True)
    pathlib.Path(".tmp/output").mkdir(parents=True, exist_ok=True)
    pathlib.Path(".tmp/log").mkdir(parents=True, exist_ok=True)
    pathlib.Path(".tmp/model").mkdir(parents=True, exist_ok=True)

    # declare some variables
    now = datetime.datetime.now()
    az_blob_container_name = storage_container
    az_model_folder = model_dir
    local_input_folder = "input"
    local_model_folder = "model"
    local_output_folder = "output"
    local_log_folder = "log"

    # service bus client
    bus_service = ServiceBusService(
        service_namespace=namespace,
        shared_access_key_name=sb_key_name,
        shared_access_key_value=sb_key_value,
    )

    # blob client
    block_blob_service = BlockBlobService(
        account_name=storage_account_name, account_key=storage_account_key
    )

    # download available style models to tmp dir
    start = time.time()
    models = block_blob_service.list_blobs(
        az_blob_container_name, prefix="{}/".format(az_model_folder)
    )
    logger.debug(
        "Style models are downloading from <blob>/{}/{} to .tmp/{}/".format(
            az_blob_container_name, model_dir, local_model_folder
        )
    )

    model_names = []
    for model in models:
        model_name = model.name.split("/")[-1]
        model_names.append(model_name)
        block_blob_service.get_blob_to_path(
            container_name=az_blob_container_name,
            blob_name=model.name,
            file_path=os.path.join(".tmp/model", "{}".format(model_name)),
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

    end = time.time()
    logger.debug("It took {} seconds to download style models.".format(end - start))

    # start listening...
    logger.debug("Start listening to queue '{}' on service bus...".format(queue))

    # set up dequeue counter
    i = 0

    while True:

        # check if dequeue limit is reached, exit if so
        if dequeue_limit is not None and dequeue_limit == i:
            logger.debug(
                "Dequeue limit of {} is reached. Exiting program...".format(
                    dequeue_limit
                )
            )
            exit(0)
        else:
            i += 1

        # inspect queue
        logger.debug("Peek queue...")
        msg = bus_service.receive_queue_message(queue, peek_lock=True, timeout=30)

        if msg.body is None:
            if terminate_if_queue_is_empty:
                logger.debug(
                    "Receiver has timed out, queue is empty. Exiting program..."
                )
                exit(0)
            else:
                logger.debug("Receiver has timed out, queue is empty. Waiting 1 minute before trying again...")
                time.sleep(60)
                continue

        # get style, input_frame, input_dir & output_dir from msg body
        msg_body = ast.literal_eval(msg.body.decode("utf-8"))

        style = msg_body["style"]
        input_frame = msg_body["input_frame"]
        input_dir = msg_body["input_dir"]
        output_dir = msg_body["output_dir"]
        log_dir = "{}_logs".format(output_dir)

        # create a new file handler for style transfer logs
        log_file = "{}.log".format(".".join(input_frame.split(".")[:-1]))
        file_handler = RotatingFileHandler(
            os.path.join(".tmp/{}".format(local_log_folder), log_file), maxBytes=20000
        )
        file_handler.setFormatter(handler_format)
        logger.addHandler(file_handler)
        logger.debug("Queue message body: {}".format(msg_body))

        # set input/output file vars
        local_input_file = ".tmp/{}/{}".format(local_input_folder, input_frame)
        local_model_file = ".tmp/{}/{}.pth".format(local_model_folder, style)
        local_output_file = ".tmp/{}/{}".format(local_output_folder, input_frame)
        local_log_file = ".tmp/{}/{}".format(local_log_folder, log_file)

        # download blob to temp dir
        block_blob_service.get_blob_to_path(
            az_blob_container_name,
            "{}/{}".format(input_dir, input_frame),
            local_input_file,
        )

        # run style transfer
        logger.debug("Starting style transfer on {}/{}".format(input_dir, input_frame))
        fast_style_transfer.stylize(
            content_scale=None,
            model_dir=".tmp/{}".format(local_model_folder),
            cuda=1,
            style=style,
            content_dir=".tmp/{}".format(local_input_folder),
            output_dir=".tmp/{}".format(local_output_folder),
        )
        logger.debug("Finished style transfer on {}/{}".format(input_dir, input_frame))

        # upload output + log file
        block_blob_service.create_blob_from_path(
            az_blob_container_name,
            "{}/{}".format(output_dir, input_frame),
            local_output_file,
        )
        block_blob_service.create_blob_from_path(
            az_blob_container_name,
            "{}/{}".format(log_dir, log_file),
            local_log_file,
        )
        logger.debug("Uploaded output file and log file to storage")

        # delete tmp
        if os.path.exists(local_input_file):
            os.remove(local_input_file)
        if os.path.exists(local_output_file):
            os.remove(local_output_file)

        # delete msg
        logger.debug("Deleting queue message...")
        msg.delete()

        # pop logger handler
        logger.handlers.pop()
