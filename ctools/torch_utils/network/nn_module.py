"""
Copyright 2020 Sensetime X-lab. All Rights Reserved

Main Function:
    1. The neural network model, include methods such as init weight, build conv block or fully-connected block ,etc.
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.init import xavier_normal_, kaiming_normal_, orthogonal_

from .normalization import build_normalization


def weight_init_(weight, init_type="xavier", activation=None):
    r"""
    Overview:
        Init weight according to the given init_type.

    Arguments:
        - weight (:obj:`tensor`): the weight that needed to init
        - init_type (:obj:`str`): the type of init to implement, include ["xavier", "kaiming", "orthogonal"]
        - activation (:obj:`str`): the non-linear function (`nn.functional` name), recommended to use only with
                                   ``'relu'`` or ``'leaky_relu'``.
    """

    def xavier_init(weight, *args):
        xavier_normal_(weight)

    def kaiming_init(weight, activation):
        assert activation is not None
        if hasattr(activation, "negative_slope"):
            kaiming_normal_(weight, a=activation.negative_slope)
        else:
            kaiming_normal_(weight, a=0)

    def orthogonal_init(weight, *args):
        orthogonal_(weight)

    init_type_dict = {"xavier": xavier_init, "kaiming": kaiming_init, "orthogonal": orthogonal_init}
    if init_type in init_type_dict:
        init_type_dict[init_type](weight, activation)
    else:
        raise KeyError("Invalid Value in init type: {}".format(init_type))


def sequential_pack(layers):
    r"""
    Overview:
        Packing the layers in the input list to a nn.Sequential module
        if there is a convolutional layer in module, an extra attribute
        `out_channels` will be added to the module
        and set to the out_channel of the conv layer

    Arguments:
        - layers (:obj:`list`): the input list

    Returns:
        - seq (:obj:`nn.Sequential`): packed sequential container
    """
    assert isinstance(layers, list)
    seq = nn.Sequential(*layers)
    for item in layers:
        if isinstance(item, nn.Conv2d) or isinstance(item, nn.ConvTranspose2d):
            seq.out_channels = item.out_channels
            break
        elif isinstance(item, nn.Conv1d):
            seq.out_channels = item.out_channels
            break
    return seq


def conv1d_block(
    in_channels,
    out_channels,
    kernel_size,
    stride=1,
    padding=0,
    dilation=1,
    groups=1,
    init_type="xavier",
    activation=None,
    norm_type=None
):
    r"""
    Overview:
        create a 1-dim convlution layer with activation and normalization.

        Note:
            Conv1d (https://pytorch.org/docs/stable/generated/torch.nn.Conv1d.html#torch.nn.Conv1d)

    Arguments:
        - in_channels (:obj:`int`): Number of channels in the input tensor
        - out_channels (:obj:`int`): Number of channels in the output tensor
        - kernel_size (:obj:`int`): Size of the convolving kernel
        - stride (:obj:`int`): Stride of the convolution
        - padding (:obj:`int`): Zero-padding added to both sides of the input
        - dilation (:obj:`int`): Spacing between kernel elements
        - groups (:obj:`int`): Number of blocked connections from input channels to output channels
        - init_type (:obj:`str`): the type of init to implement
        - activation (:obj:`nn.Module`): the optional activation function
        - norm_type (:obj:`str`): type of the normalization

    Returns:
        - block (:obj:`nn.Sequential`): a sequential list containing the torch layers of the 1 dim convlution layer
    """
    block = []
    block.append(nn.Conv1d(in_channels, out_channels, kernel_size, stride, padding, dilation, groups))
    weight_init_(block[-1].weight, init_type, activation)
    if norm_type is not None:
        block.append(build_normalization(norm_type, dim=1)(out_channels))
    if activation is not None:
        block.append(activation)
    return sequential_pack(block)


def conv2d_block(
    in_channels,
    out_channels,
    kernel_size,
    stride=1,
    padding=0,
    dilation=1,
    groups=1,
    init_type="xavier",
    pad_type='zero',
    activation=None,
    norm_type=None
):
    r"""
    Overview:
        create a 2-dim convlution layer with activation and normalization.

        Note:
            Conv2d (https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html#torch.nn.Conv2d)

    Arguments:
        - in_channels (:obj:`int`): Number of channels in the input tensor
        - out_channels (:obj:`int`): Number of channels in the output tensor
        - kernel_size (:obj:`int`): Size of the convolving kernel
        - stride (:obj:`int`): Stride of the convolution
        - padding (:obj:`int`): Zero-padding added to both sides of the input
        - dilation (:obj:`int`): Spacing between kernel elements
        - groups (:obj:`int`): Number of blocked connections from input channels to output channels
        - init_type (:obj:`str`): the type of init to implement
        - pad_type (:obj:`str`): the way to add padding, include ['zero', 'reflect', 'replicate'], default: None
        - activation (:obj:`nn.Moduel`): the optional activation function
        - norm_type (:obj:`str`): type of the normalization, default set to None, now support ['BN', 'IN', 'SyncBN']

    Returns:
        - block (:obj:`nn.Sequential`): a sequential list containing the torch layers of the 2 dim convlution layer
    """

    block = []
    assert pad_type in ['zero', 'reflect', 'replication'], "invalid padding type: {}".format(pad_type)
    if pad_type == 'zero':
        pass
    elif pad_type == 'reflect':
        block.append(nn.ReflectionPad2d(padding))
        padding = 0
    elif pad_type == 'replication':
        block.append(nn.ReplicationPad2d(padding))
        padding = 0
    block.append(
        nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding=padding, dilation=dilation, groups=groups)
    )
    weight_init_(block[-1].weight, init_type, activation)
    if norm_type is not None:
        block.append(build_normalization(norm_type, dim=2)(out_channels))
    if activation is not None:
        block.append(activation)
    return sequential_pack(block)


def deconv2d_block(
    in_channels,
    out_channels,
    kernel_size,
    stride=1,
    padding=0,
    output_padding=0,
    groups=1,
    init_type="xavier",
    activation=None,
    norm_type=None
):
    r"""
    Overview:
        create a 2-dim transopse convlution layer with activation and normalization

        Note:
            ConvTranspose2d (https://pytorch.org/docs/master/generated/torch.nn.ConvTranspose2d.html)

    Arguments:
        - in_channels (:obj:`int`): Number of channels in the input tensor
        - out_channels (:obj:`int`): Number of channels in the output tensor
        - kernel_size (:obj:`int`): Size of the convolving kernel
        - stride (:obj:`int`): Stride of the convolution
        - padding (:obj:`int`): Zero-padding added to both sides of the input
        - init_type (:obj:`str`): the type of init to implement
        - pad_type (:obj:`str`): the way to add padding, include ['zero', 'reflect', 'replicate']
        - activation (:obj:`nn.Moduel`): the optional activation function
        - norm_type (:obj:`str`): type of the normalization

    Returns:
        - block (:obj:`nn.Sequential`): a sequential list containing the torch layers of the 2 dim transpose
                                        convlution layer
    """
    block = []
    block.append(
        nn.ConvTranspose2d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            output_padding=output_padding,
            groups=groups
        )
    )
    weight_init_(block[-1].weight, init_type, activation)
    if norm_type is not None:
        block.append(build_normalization(norm_type, dim=2)(out_channels))
    if activation is not None:
        block.append(activation)
    return sequential_pack(block)


def fc_block(
    in_channels,
    out_channels,
    init_type="xavier",
    activation=None,
    norm_type=None,
    use_dropout=False,
    dropout_probability=0.5
):
    r"""
    Overview:
        create a fully-connected block with activation, normalization and dropout
        optional normalization can be done to the dim 1 (across the channels)
        x -> fc -> norm -> act -> dropout -> out
    Arguments:
        - in_channels (:obj:`int`): Number of channels in the input tensor
        - out_channels (:obj:`int`): Number of channels in the output tensor
        - init_type (:obj:`str`): the type of init to implement
        - activation (:obj:`nn.Moduel`): the optional activation function
        - norm_type (:obj:`str`): type of the normalization
        - use_dropout (:obj:`bool`) : whether to use dropout in the fully-connected block
        - dropout_probability (:obj:`float`) : probability of an element to be zeroed in the dropout. Default: 0.5
    Returns:
        - block (:obj:`nn.Sequential`): a sequential list containing the torch layers of the fully-connected block

    .. note::
        you can refer to nn.linear (https://pytorch.org/docs/master/generated/torch.nn.Linear.html)
    """
    block = []
    block.append(nn.Linear(in_channels, out_channels))
    weight_init_(block[-1].weight, init_type, activation)
    if norm_type is not None:
        block.append(build_normalization(norm_type, dim=1)(out_channels))
    if activation is not None:
        block.append(activation)
    if use_dropout:
        block.append(nn.Dropout(dropout_probability))
    return sequential_pack(block)


class ChannelShuffle(nn.Module):
    r"""
        Overview:
            Apply channelShuffle to the input tensor

            Note:
            You can see the original paper shuffle net in link below
            shuffleNet(https://arxiv.org/abs/1707.01083)
        Interface:
            __init__, forward
    """

    def __init__(self, group_num):
        r"""
            Overview:
                Init class ChannelShuffle

            Arguments:
                - group_num (:obj:`int`): the number of groups to exchange
        """
        super(ChannelShuffle, self).__init__()
        self.group_num = group_num

    def forward(self, x):
        r"""
        Overview:
            return the upsampled input

        Arguments:
            - x (:obj:`tensor`): the input tensor

        Returns:
            - x (:obj:`tensor`): the shuffled input tensor
        """
        b, c, h, w = x.shape
        g = self.group_num
        assert (c % g == 0)
        x = x.view(b, g, c // g, h, w).permute(0, 2, 1, 3, 4).contiguous().view(b, c, h, w)
        return x


def one_hot(val, num, num_first=False):
    r"""
    Overview:
        convert a Long tensor to one hot encoding
        if num_first is False, the one hot code dimension is added as the last
        if num_first is True, the code is made as the first dimension
        this implementation can be slightly faster than torch.nn.functional.one_hot

    Arguments:
        - val (:obj:`torch.LongTensor`): each element contains the state to be encoded, the range should be [0, num-1]
        - num (:obj:`int`): number of states of the one hot encoding
        - num_first (:obj:`bool`)

    Returns:
        - one_hot (:obj:`torch.FloatTensor`)

    Example:
        >>> one_hot(2*torch.ones([2,2]).long(),3)
        tensor([[[0., 0., 1.],
                 [0., 0., 1.]],
                [[0., 0., 1.],
                 [0., 0., 1.]]])
        >>> one_hot(2*torch.ones([2,2]).long(),3,num_first=True)
        tensor([[[0., 0.], [1., 0.]],
                [[0., 1.], [0., 0.]],
                [[1., 0.], [0., 1.]]])
    """
    return torch.nn.functional.one_hot(val, num).float()


class NearestUpsample(nn.Module):
    r"""
    Overview:
        Upsamples the input to the given member varible scale_factor using mode nearest

    Interface:
        __init__, forward
    """

    def __init__(self, scale_factor):
        r"""
        Overview:
            Init class NearestUpsample

        Arguments:
            - scale_factor (:obj:`float` or :obj:`list` of :obj:`float`): multiplier for spatial size
        """
        super(NearestUpsample, self).__init__()
        self.scale_factor = scale_factor

    def forward(self, x):
        r"""
        Overview:
            return the upsampled input

        Arguments:
            - x (:obj:`tensor`): the input tensor

        Returns:
            - upsample(:obj:`tensor`): the upsampled input tensor
        """
        return F.interpolate(x, scale_factor=self.scale_factor, mode='nearest', align_corners=False)


class BilinearUpsample(nn.Module):
    r"""
    Overview:
        Upsamples the input to the given member varible scale_factor using mode biliner

    Interface:
        __init__, forward
    """

    def __init__(self, scale_factor):
        r"""
        Overview:
            Init class BilinearUpsample

        Arguments:
            - scale_factor (:obj:`float` or :obj:`list` of :obj:`float`): multiplier for spatial size
        """
        super(BilinearUpsample, self).__init__()
        self.scale_factor = scale_factor

    def forward(self, x):
        r"""
        Overview:
            return the upsampled input

        Arguments:
            - x (:obj:`tensor`): the input tensor

        Returns:
            - upsample(:obj:`tensor`): the upsampled input tensor
        """
        return F.interpolate(x, scale_factor=self.scale_factor, mode='bilinear', align_corners=False)


def binary_encode(y, max_val):
    r"""
    Overview:
        Convert elements in a tensor to its binary representation

    Arguments:
        - y (:obj:`tensor`): the tensor to be transfered into its binary representation
        - max_val (:obj:`tensor`): the max value of the elements in tensor

    Returns:
        - binary (:obj:`tensor`): the input tensor in its binary representation

    Example:
        >>> binary_encode(torch.tensor([3,2]),torch.tensor(8))
        tensor([[0, 0, 1, 1],[0, 0, 1, 0]])
    """
    assert (max_val > 0)
    x = y.clamp(0, max_val)
    B = x.shape[0]
    L = int(math.log(max_val, 2)) + 1
    binary = []
    one = torch.ones_like(x)
    zero = torch.zeros_like(x)
    for i in range(L):
        num = 1 << (L - i - 1)  # 2**(L-i-1)
        bit = torch.where(x >= num, one, zero)
        x -= bit * num
        binary.append(bit)
    return torch.stack(binary, dim=1)
