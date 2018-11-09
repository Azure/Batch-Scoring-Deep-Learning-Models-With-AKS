from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os
import pathlib
from util import Parser


def postprocess(
    block_blob_service, storage_container, frames_dir, audio_file, video_file
):
    """
    This function uses ffmpeg on a set of individual frames and 
    an audio file to reconstruct the video. Once the video is 
    reconstructed, it is uploaded to storage.

    :param block_blob_service: blob client
    :param frames_dir: the input directory in Azure storage to download the processed frames from
    :param audio_file: the input audio file in Azure storage to reconstruct the video with (include ext)
    :param video_file: the output video file to store to blob (exclude ext)
    """
    tmp_dir = ".tmp_aci_post"
    pathlib.Path(os.path.join(tmp_dir, frames_dir)).mkdir(parents=True, exist_ok=True)

    # download audio from storage to temp dir
    block_blob_service.get_blob_to_path(
        storage_container, audio_file, os.path.join(tmp_dir, audio_file)
    )

    # download images from blob to temp dir
    frames = block_blob_service.list_blobs(storage_container, prefix=frames_dir)

    for frame in frames:
        frame_name = frame.name.split("/")[-1]
        block_blob_service.get_blob_to_path(
            storage_container,
            os.path.join(frames_dir, frame_name),
            os.path.join(tmp_dir, frames_dir, frame_name),
        )

    # stitch frames to generate new video with ffmpeg
    subprocess.run(
        "ffmpeg -framerate 30 -i {}/%05d_frame.jpg -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -y {}_without_audio.mp4".format(
            os.path.join(tmp_dir, frames_dir), video_file
        ),
        shell=True,
        check=True,
    )

    # reattach audio to the newly generated video
    subprocess.run(
        "ffmpeg -i {}_without_audio.mp4 -i {} -map 0:0 -map 1:0 -vcodec copy -acodec copy -y {}.mp4".format(
            video_file, audio_file, video_file
        ),
        shell=True,
        check=True,
    )

    # upload video to blob
    block_blob_service.create_blob_from_path(
        storage_container, video_file, os.path.join(".tmp_aci", video_file)
    )

    return


if __name__ == "__main__":
    parser = Parser()
    parser.append_postprocess_args()
    args = parser.return_args()

    assert args.frames_dir is not None
    assert args.audio is not None
    assert args.video is not None
    assert args.storage_container_name is not None
    assert args.storage_account_name is not None
    assert args.storage_account_key is not None

    block_blob_service = BlockBlobService(
        account_name=args.storage_account_name, account_key=args.storage_account_key
    )

    postprocess(
        block_blob_service=block_blob_service,
        storage_container=args.storage_container_name,
        frames_dir=args.frames_dir,
        audio_file=args.audio,
        video_file=args.video,
    )
