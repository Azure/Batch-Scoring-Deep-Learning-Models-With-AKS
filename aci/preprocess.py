from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os
import pathlib
from util import Parser


def preprocess(video, frames_dir=None, audio_file=None):
    """
    This function uses ffmpeg on the `video` to create
        - a new frames_dir with all the frames of the video and
        - a new audio_file which is just the audio track of the video

    It then uploads the new assets to blob, and returns the 
    generated frames directory and audio file

    :param video: the name (not path) of the video file in blob storage (including ext)
    :param frames_dir: (optional) the name of the frames directory in storage to 
        save individual frames to
    :param audio_file: (optional) the name of the audio file in storage to save 
        the extracted audio clip to
    """
    storage_container = "data"

    # generate frames_dir name based on video name if not explicitly provided
    if frames_dir is None:
        frames_dir = "{}_frames".format(video.split(".")[0])

    # generate audio_file name based on video name if not explicitly provided
    if audio_file is None:
        audio_file = "{}_audio.aac".format(video.split(".")[0])

    # video pre-processing: audio extraction
    subprocess.run(
        "ffmpeg -y -i {} {}".format(
            os.path.join(storage_container, video),
            os.path.join(storage_container, audio_file),
        ),
        shell=True,
        check=True,
    )

    # video pre-processing: split to frames
    subprocess.run(
        "ffmpeg -y -i {} {}/%06d_frame.jpg -hide_banner".format(
            os.path.join(storage_container, video),
            os.path.join(storage_container, frames_dir),
        ),
        shell=True,
        check=True,
    )

    return frames_dir, audio_file


if __name__ == "__main__":
    parser = Parser()
    parser.append_preprocess_args()
    args = parser.return_args()

    assert args.video is not None

    preprocess(args.video, args.frames_dir, args.audio)
