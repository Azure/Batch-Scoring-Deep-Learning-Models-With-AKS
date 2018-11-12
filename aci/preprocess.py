from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os
import pathlib
from util import Parser


def preprocess(
    block_blob_service, video, storage_container, frames_dir=None, audio_file=None
):
    """
		This function uses ffmpeg on the `video` to create
			- a new frames_dir with all the frames of the video and
			- a new audio_file which is just the audio track of the video

		It then uploads the new assets to blob, and returns the 
		generated frames directory and audio file

		:param block_blob_service: blob client
		:param video: the name of the video file in blob storage (including ext)
		:param storage_container: the storage container
		:param frames_dir: (optional) the name of the frames directory in storage to 
			save individual frames to
		:param audio_file: (optional) the name of the audio file in storage to save 
			the extracted audio clip to
		"""

    # create tmp dir
    tmp_dir = ".aci_pre"
    pathlib.Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    # download video file
    block_blob_service.get_blob_to_path(
        storage_container, video, os.path.join(tmp_dir, video)
    )

    # generate frames_dir name based on video name if not explicitly provided
    if frames_dir is None:
        frames_dir = "{}_frames".format(video.split(".")[0])

    pathlib.Path(os.path.join(tmp_dir, frames_dir)).mkdir(parents=True, exist_ok=True)

    # generate audio_file name based on video name if not explicitly provided
    if audio_file is None:
        audio_file = "{}_audio.aac".format(video.split(".")[0])

        # video pre-processing: audio extraction
    subprocess.run(
        "ffmpeg -i {} {}".format(
            os.path.join(tmp_dir, video), os.path.join(tmp_dir, audio_file)
        ),
        shell=True,
        check=True,
    )

    # video pre-processing: split to frames
    subprocess.run(
        "ffmpeg -i {} {}/%06d_frame.jpg -hide_banner".format(
            os.path.join(tmp_dir, video), os.path.join(tmp_dir, frames_dir)
        ),
        shell=True,
        check=True,
    )

    # upload all frames
    for img in os.listdir(os.path.join(tmp_dir, frames_dir)):
        block_blob_service.create_blob_from_path(
            storage_container,
            os.path.join(frames_dir, img),
            os.path.join(tmp_dir, frames_dir, img),
        )

        # upload audio file
    block_blob_service.create_blob_from_path(
        storage_container, audio_file, os.path.join(tmp_dir, audio_file)
    )

    return frames_dir, audio_file


if __name__ == "__main__":
    parser = Parser()
    parser.append_preprocess_args()
    args = parser.return_args()

    assert args.video is not None
    assert args.storage_container is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None

    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    preprocess(
        block_blob_service,
        args.video,
        args.storage_container,
        args.frames_dir,
        args.audio,
    )
