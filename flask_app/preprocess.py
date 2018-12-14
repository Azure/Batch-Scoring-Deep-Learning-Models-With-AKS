from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os
import pathlib
from util import Parser, Storage


def preprocess(video, mount_dir):
    """
    This function uses ffmpeg on the `video` to create
        - a new frames_dir with all the frames of the video and
        - a new audio_file which is just the audio track of the video

    It then uploads the new assets to blob, and returns the 
    generated frames storage and audio file

    :param video: the name (not path) of the video file in blob storage (including ext)
    :param mount_dir: the mount storage of the storage container
    """

    # video name (remove ext)
    video_name = video.split(".")[0]

    # audio and input frame paths
    audio_path = os.path.join(mount_dir, video_name, Storage.AUDIO_FILE.value)
    input_frames_path = os.path.join(mount_dir, video_name, Storage.INPUT_DIR.value)

    # create frames storage if not exist
    if not os.path.exists(input_frames_path):
        os.makedirs(input_frames_path)

    # video pre-processing: audio extraction
    subprocess.run(
        "ffmpeg -y -i {} {}".format(
            os.path.join(mount_dir, video), audio_path
        ),
        shell=True,
        check=True,
    )

    # video pre-processing: split to frames
    subprocess.run(
        "ffmpeg -y -i {} {}/%06d_frame.jpg -hide_banner".format(
            os.path.join(mount_dir, video), input_frames_path
        ),
        shell=True,
        check=True,
    )

if __name__ == "__main__":
    parser = Parser()
    parser.append_preprocess_args()
    args = parser.return_args()

    assert args.video is not None
    assert args.storage_mount_dir is not None

    preprocess(args.video, args.storage_mount_dir)
