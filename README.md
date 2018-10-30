# Batch Scoring Deep Learning Models With Kubernetes

## Overview
In this repository, we use the scenario of applying style transfer onto a video (collection of images). This architecture can be generalized for any batch scoring with deep learning scenario.

## Design (TODO)
![Reference Architecture Diagram](https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/arhictecture_diagram)

The above architecture works as follows:
1. Upload your selected style image (like a Van Gogh painting) and your style transfer script to Blob Storage.
2. Split up your video into individual frames and upload those frames into Blob Storage.
3. Logic App will then be triggered, and will create an ACI that runs a Batch AI job creation script.
4. The script running in ACI will create the Batch AI jobs. Each job will apply the style transfer in parallel across the nodes of the Batch AI cluster.
5. Once the images are generated, they will be saved back to Blob Storage.
6. Finally, you can download the generates frames, and stitch back the images into a video.

### Style Transfer for Video

| Style image: | Input/content video: | Output video: | 
|--------|--------|---------|
| <img src="https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/style_image.jpg" width="300"> | [<img src="https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/input_video_image_0.jpg" width="300" height="300">](https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/input_video.mp4 "Input Video") *click to view video* | [<img src="https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/output_video_image_0.jpg" width="300" height="300">](https://happypathspublic.blob.core.windows.net/assets/batch_scoring_for_dl/output_video.mp4 "Output Video") *click to view* |

## Prerequsites

Local/Working Machine:
- Ubuntu >=16.04LTS (not tested on Mac or Windows)
- [NVIDIA Drivers on GPU enabled machine](https://linuxconfig.org/how-to-install-the-nvidia-drivers-on-ubuntu-18-04-bionic-beaver-linux) [Additional ref: [https://github.com/NVIDIA/nvidia-docker](https://github.com/NVIDIA/nvidia-docker)]
- [Conda >=4.5.4](https://conda.io/docs/)
- [Docker >=1.0](https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce-1) 
- [AzCopy >=7.0.0](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-linux?toc=%2fazure%2fstorage%2ffiles%2ftoc.json)
- [ffmpeg >=3.4.4](https://tecadmin.net/install-ffmpeg-on-linux/)
- [Azure CLI >=2.0](https://docs.microsoft.com/en-us/cli/azure/?view=azure-cli-latest)

Accounts:
- [Dockerhub account](https://hub.docker.com/)
- [Azure Subscription](https://azure.microsoft.com/en-us/free/) (with a [quota](https://docs.microsoft.com/en-us/azure/azure-supportability/resource-manager-core-quotas-request) for GPU-enabled VMs)

While it is not required, it is also useful to use the [Azure Storage Explorer](https://azure.microsoft.com/en-us/features/storage-explorer/) to inspect your storage account.e `az cli` installed and logged into

## Setup

#### Run the Kubernetes Dashboard
Run `az aks browse -n $aks_cluster -g $resource_group` in your terminal so that you can use the Kubernetes Dashboard. If you're not able to access the dashboard, follow the instructions [here](https://blog.tekspace.io/kubernetes-dashboard-remote-access/).

#### Clean up
Please refer to the [last notebook](./07_stitch_together_the_results.ipynb) to clean up your Azure resources. If you want to keep certain resources, you can also use the `az cli` or the Azure portal to cherry pick the ones you want to deprovision.

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
