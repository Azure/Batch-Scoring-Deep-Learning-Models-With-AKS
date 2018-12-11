from azure.storage.blob import BlockBlobService
import time
import glob
import subprocess
import os
import pathlib
from util import Parser


def postprocess(frames_dir, audio_file, video_file):
    """
    This function uses ffmpeg on a set of individual frames and 
    an audio file to reconstruct the video. Once the video is 
    reconstructed, it is uploaded to storage.

    :param frames_dir: the input directory in Azure storage to download the processed frames from
    :param audio_file: the input audio file in Azure storage to reconstruct the video with (include ext)
    :param video_file: the output video file to store to blob (include ext)
    """
    t0 = time.time()

    # set video file without audio name
    video_file_without_audio = "{}_without_audio.mp4".format(video_file.split(".")[0])

    # stitch frames to generate new video with ffmpeg
    t1 = time.time()
    subprocess.run(
        "ffmpeg -framerate 30 -i {}/%06d_frame.jpg -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -y {}".format(
            os.path.join("data", frames_dir),
            os.path.join("data", video_file_without_audio),
        ),
        shell=True,
        check=True,
    )

    # reattach audio to the newly generated video
    t2 = time.time()
    subprocess.run(
        "ffmpeg -i {} -i {} -map 0:0 -map 1:0 -vcodec copy -acodec copy -y {}".format(
            os.path.join("data", video_file_without_audio),
            os.path.join("data", audio_file),
            os.path.join("data", video_file),
        ),
        shell=True,
        check=True,
    )

    # time
    t3 = time.time()
    print("Download images from blob. Time taken: {:.2f}".format(t1 - t0))
    print("Stitch images together.    Time taken: {:.2f}".format(t2 - t1))
    print("Reattach audio file.       Time taken: {:.2f}".format(t3 - t2))
    print("Total.                     Time taken: {:.2f}".format(t3 - t0))

    return


if __name__ == "__main__":
    parser = Parser()
    parser.append_postprocess_args()
    args = parser.return_args()

    assert args.frames_dir is not None
    assert args.audio is not None
    assert args.video is not None

    postprocess(
        frames_dir=args.frames_dir, audio_file=args.audio, video_file=args.video
    )
