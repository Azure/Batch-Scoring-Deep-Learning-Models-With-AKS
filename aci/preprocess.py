from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os
from util import Parser


def preprocess(
    block_blob_service, video, storage_container_name, frames_dir=None, audio_file=None
):
    """
    this function uses ffmpeg on the `video` to create
      - a new frames_dir with all the frames of the video and
      - a new audio_file which is just the audio track of the video

    it then uploads the new assets to blob

    returns generated frames directory and audio file
    """
    block_blob_service.get_blob_to_path(storage_container_name, video, video)

    if frames_dir is None:
        frames_dir = "{}_frames".format(video.split(".")[0])

    if audio_file is None:
        audio_file = "{}_audio.aac".format(video.split(".")[0])

    os.makedirs(frames_dir, exist_ok=True)

    # video pre-processing: audio extraction
    subprocess.run("ffmpeg -i {} {}".format(video, audio_file), shell=True, check=True)

    # video pre-processing: split to frames
    subprocess.run(
        "ffmpeg -i {} {}/%05d_frame_of_{}.jpg -hide_banner".format(
            video, frames_dir, video.split(".")[0]
        ),
        shell=True,
        check=True,
    )

    # upload all frames
    for img in os.listdir(frames_dir):
        block_blob_service.create_blob_from_path(
            storage_container_name,
            os.path.join(frames_dir, img),
            os.path.join(frames_dir, img),
        )

    # upload audio file
    block_blob_service.create_blob_from_path(
        storage_container_name, audio_file, audio_file
    )

    return frames_dir, audio_file


if __name__ == "__main__":
    parser = Parser()
    parser.append_preprocess_args()
    args = parser.return_args()

    assert args.video is not None
    assert args.storage_container_name is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None

    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    preprocess(
        block_blob_service,
        args.video,
        args.storage_container_name,
        args.frames_dir,
        args.audio_file,
    )
