from azure.storage.blob import BlockBlobService
import time
import glob
import subprocess
import os
import pathlib
from util import Parser


def postprocess(mount_dir, frames_dir, audio_file, video_file):
    """
    This function uses ffmpeg on a set of individual frames and 
    an audio file to reconstruct the video. Once the video is 
    reconstructed, it is uploaded to storage.

    :param mount_dir: the mount directory of the storage container
    :param frames_dir: the input directory in Azure storage to download the processed frames from
    :param audio_file: the input audio file in Azure storage to reconstruct the video with (include ext)
    :param video_file: the output video file to store to blob (include ext)
    """
    # set video file without audio name
    video_file_without_audio = "{}_without_audio.mp4".format(video_file.split(".")[0])

    # stitch frames to generate new video with ffmpeg
    subprocess.run(
        "ffmpeg -framerate 30 -i {}/%06d_frame.jpg -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -y {}".format(
            os.path.join(mount_dir, frames_dir),
            os.path.join(mount_dir, video_file_without_audio),
        ),
        shell=True,
        check=True,
    )

    # reattach audio to the newly generated video
    subprocess.run(
        "ffmpeg -i {} -i {} -map 0:0 -map 1:0 -vcodec copy -acodec copy -y {}".format(
            os.path.join(mount_dir, video_file_without_audio),
            os.path.join(mount_dir, audio_file),
            os.path.join(mount_dir, video_file),
        ),
        shell=True,
        check=True,
    )


if __name__ == "__main__":
    parser = Parser()
    parser.append_postprocess_args()
    args = parser.return_args()

    assert args.frames_dir is not None
    assert args.audio is not None
    assert args.video is not None
    assert args.storage_mount_dir is not None

    postprocess(
        mount_dir=args.storage_mount_dir,
        frames_dir=args.frames_dir,
        audio_file=args.audio,
        video_file=args.video
    )
