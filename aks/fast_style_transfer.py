# Original source: https://github.com/pytorch/examples/blob/master/fast_neural_style/neural_style/neural_style.py
import argparse
import os
import sys
import re
import logging
from PIL import Image
import torch
from torchvision import transforms


def load_image(filename, size=None, scale=None):
    img = Image.open(filename)
    if size is not None:
        img = img.resize((size, size), Image.ANTIALIAS)
    elif scale is not None:
        img = img.resize(
            (int(img.size[0] / scale), int(img.size[1] / scale)), Image.ANTIALIAS
        )
    return img


def save_image(filename, data):
    img = data.clone().clamp(0, 255).numpy()
    img = img.transpose(1, 2, 0).astype("uint8")
    img = Image.fromarray(img)
    img.save(filename)


class TransformerNet(torch.nn.Module):
    def __init__(self):
        super(TransformerNet, self).__init__()
        # Initial convolution layers
        self.conv1 = ConvLayer(3, 32, kernel_size=9, stride=1)
        self.in1 = torch.nn.InstanceNorm2d(32, affine=True)
        self.conv2 = ConvLayer(32, 64, kernel_size=3, stride=2)
        self.in2 = torch.nn.InstanceNorm2d(64, affine=True)
        self.conv3 = ConvLayer(64, 128, kernel_size=3, stride=2)
        self.in3 = torch.nn.InstanceNorm2d(128, affine=True)
        # Residual layers
        self.res1 = ResidualBlock(128)
        self.res2 = ResidualBlock(128)
        self.res3 = ResidualBlock(128)
        self.res4 = ResidualBlock(128)
        self.res5 = ResidualBlock(128)
        # Upsampling Layers
        self.deconv1 = UpsampleConvLayer(128, 64, kernel_size=3, stride=1, upsample=2)
        self.in4 = torch.nn.InstanceNorm2d(64, affine=True)
        self.deconv2 = UpsampleConvLayer(64, 32, kernel_size=3, stride=1, upsample=2)
        self.in5 = torch.nn.InstanceNorm2d(32, affine=True)
        self.deconv3 = ConvLayer(32, 3, kernel_size=9, stride=1)
        # Non-linearities
        self.relu = torch.nn.ReLU()

    def forward(self, X):
        y = self.relu(self.in1(self.conv1(X)))
        y = self.relu(self.in2(self.conv2(y)))
        y = self.relu(self.in3(self.conv3(y)))
        y = self.res1(y)
        y = self.res2(y)
        y = self.res3(y)
        y = self.res4(y)
        y = self.res5(y)
        y = self.relu(self.in4(self.deconv1(y)))
        y = self.relu(self.in5(self.deconv2(y)))
        y = self.deconv3(y)
        return y


class ConvLayer(torch.nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride):
        super(ConvLayer, self).__init__()
        reflection_padding = kernel_size // 2
        self.reflection_pad = torch.nn.ReflectionPad2d(reflection_padding)
        self.conv2d = torch.nn.Conv2d(in_channels, out_channels, kernel_size, stride)

    def forward(self, x):
        out = self.reflection_pad(x)
        out = self.conv2d(out)
        return out


class ResidualBlock(torch.nn.Module):
    """ResidualBlock
    introduced in: https://arxiv.org/abs/1512.03385
    recommended architecture: http://torch.ch/blog/2016/02/04/resnets.html
    """

    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = ConvLayer(channels, channels, kernel_size=3, stride=1)
        self.in1 = torch.nn.InstanceNorm2d(channels, affine=True)
        self.conv2 = ConvLayer(channels, channels, kernel_size=3, stride=1)
        self.in2 = torch.nn.InstanceNorm2d(channels, affine=True)
        self.relu = torch.nn.ReLU()

    def forward(self, x):
        residual = x
        out = self.relu(self.in1(self.conv1(x)))
        out = self.in2(self.conv2(out))
        out = out + residual
        return out


class UpsampleConvLayer(torch.nn.Module):
    """UpsampleConvLayer
    Upsamples the input and then does a convolution. This method gives better results
    compared to ConvTranspose2d.
    ref: http://distill.pub/2016/deconv-checkerboard/
    """

    def __init__(self, in_channels, out_channels, kernel_size, stride, upsample=None):
        super(UpsampleConvLayer, self).__init__()
        self.upsample = upsample
        if upsample:
            self.upsample_layer = torch.nn.Upsample(
                mode="nearest", scale_factor=upsample
            )
        reflection_padding = kernel_size // 2
        self.reflection_pad = torch.nn.ReflectionPad2d(reflection_padding)
        self.conv2d = torch.nn.Conv2d(in_channels, out_channels, kernel_size, stride)

    def forward(self, x):
        x_in = x
        if self.upsample:
            x_in = self.upsample_layer(x_in)
        out = self.reflection_pad(x_in)
        out = self.conv2d(out)
        return out


def stylize(content_scale, model_dir, cuda, style, content_dir, output_dir):

    logger = logging.getLogger("root")

    # check that all the paths and image references are good
    assert os.path.exists(content_dir)
    assert os.path.exists(output_dir)
    assert os.path.isdir(model_dir)

    device = torch.device("cuda" if cuda else "cpu")
    with torch.no_grad():
        style_model = TransformerNet()
        state_dict = torch.load(os.path.join(model_dir, style + ".pth"))
        # remove saved deprecated running_* keys in InstanceNorm from the checkpoint
        for k in list(state_dict.keys()):
            if re.search(r"in\d+\.running_(mean|var)$", k):
                del state_dict[k]
        style_model.load_state_dict(state_dict)
        style_model.to(device)

        filenames = os.listdir(content_dir)

        for filename in filenames:
            full_path = os.path.join(content_dir, filename)
            logger.debug("Processing {}".format(full_path))
            content_image = load_image(full_path, scale=content_scale)
            content_transform = transforms.Compose(
                [transforms.ToTensor(), transforms.Lambda(lambda x: x.mul(255))]
            )
            content_image = content_transform(content_image)
            content_image = content_image.unsqueeze(0).to(device)

            output = style_model(content_image).cpu()

            output_path = os.path.join(output_dir, filename)
            save_image(output_path, output[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="parser for fast-neural-style")

    parser.add_argument(
        "--content-scale",
        type=float,
        default=None,
        help="factor for scaling down the content image",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        required=True,
        help="saved model to be used for stylizing the image.",
    )
    parser.add_argument(
        "--cuda",
        type=int,
        required=True,
        help="set it to 1 for running on GPU, 0 for CPU",
    )
    parser.add_argument("--style", type=str, help="style name")
    parser.add_argument(
        "--content-dir", type=str, required=True, help="directory holding the images"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="directory holding the output images",
    )
    args = parser.parse_args()

    if args.cuda and not torch.cuda.is_available():
        print("ERROR: cuda is not available, try running on CPU")
        sys.exit(1)

    # os.makedirs(args.output_dir, exist_ok=True)
    # stylize(args)

    # set up logger
    handler_format = logging.Formatter(
        "%(asctime)s [%(name)s:%(filename)s:%(lineno)s] %(levelname)s - %(message)s"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(handler_format)
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.propagate = False

    logger.debug("Starting neural style transfer...")
    stylize(
        content_scale=args.content_scale,
        model_dir=args.model_dir,
        cuda=args.cuda,
        style=args.style,
        content_dir=args.content_dir,
        output_dir=args.output_dir,
    )
