from azure.storage.blob import BlockBlobService
import glob
import subprocess
import os


def process_video(
    video, 
    storage_container_name, 
    block_blob_service
):
    """
    this function uses ffmpeg on the `video` to create
      - a new frames_dir with all the frames of the video and
      - a new audio_file which is just the audio track of the video

    it then uploads the new assets to blob

    returns generated frames directory and audio file
    """
    block_blob_service.get_blob_to_path(
        storage_container_name,
        video,
        video
    )

    frames_dir = "{}_frames".format(video.split(".")[0])
    audio = "{}_audio.mp3".format(video.split(".")[0])

    os.makedirs(frames_dir, exist_ok=True)

    subprocess.run("ffmpeg -i {} {}"
        .format(video, audio),
        shell=True, check=True
    )

    # video pre-processing: audio extraction
    subprocess.run("ffmpeg -i {} {}/%05d_frame_of_{}.jpg -hide_banner"
        .format(video, frames_dir, video),
        shell=True, check=True
    )

    # upload all frames
    for img in os.listdir(frames_dir):
        block_blob_service.create_blob_from_path(
            storage_container_name,
            os.path.join(frames_dir, img),
            os.path.join(frames_dir, img)
        )
    
    # upload audio file
    block_blob_service.create_blob_from_path(
        storage_container_name,
        audio,
        audio
    )

    return frames_dir, audio
