from azure.storage.blob import BlockBlobService
import time
import glob
import subprocess
import os
import pathlib
from util import Parser, Storage


def postprocess(mount_dir, video_name):
    """
    This function uses ffmpeg on a set of individual frames and 
    an audio file to reconstruct the video. Once the video is 
    reconstructed, it is uploaded to storage.

    :param mount_dir: the mount directory of the storage container
    :param video_name: the name of the video file
    """
    # set video file without audio name
    video_without_audio = "{}_without_audio.mp4".format(video_name)
    video_with_audio = "{}_processed.mp4".format(video_name)

    # stitch frames to generate new video with ffmpeg
    subprocess.run(
        "ffmpeg -framerate 30 -i {}/%06d_frame.jpg -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -y {}".format(
            os.path.join(mount_dir, video_name, Storage.OUTPUT_DIR.value),
            os.path.join(mount_dir, video_name, video_without_audio),
        ),
        shell=True,
        check=True,
    )

    # reattach audio to the newly generated video
    subprocess.run(
        "ffmpeg -i {} -i {} -map 0:0 -map 1:0 -vcodec copy -acodec copy -y {}".format(
            os.path.join(mount_dir, video_name, video_without_audio),
            os.path.join(mount_dir, video_name, "audio.aac"),
            os.path.join(mount_dir, video_name, video_with_audio),
        ),
        shell=True,
        check=True,
    )

    # remove temp video without audio
    os.remove(os.path.join(mount_dir, video_name, video_without_audio))


if __name__ == "__main__":
    parser = Parser()
    parser.append_postprocess_args()
    args = parser.return_args()

    assert args.video_name is not None
    assert args.storage_mount_dir is not None

    postprocess(
        mount_dir=args.storage_mount_dir,
        video_name=args.video_name
    )
