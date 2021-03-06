from typing import Dict, Union

import torch
from torch.distributions import Uniform

from kornia.augmentation.random_generator.base import RandomGeneratorBase
from kornia.augmentation.utils import _adapted_rsampling, _adapted_uniform, _common_param_check
from kornia.utils.helpers import _deprecated, _extract_device_dtype


class PerspectiveGenerator(RandomGeneratorBase):
    r"""Get parameters for ``perspective`` for a random perspective transform.

    Args:
        distortion_scale: the degree of distortion, ranged from 0 to 1.

    Returns:
        A dict of parameters to be passed for transformation.
            - start_points (torch.Tensor): element-wise perspective source areas with a shape of (B, 4, 2).
            - end_points (torch.Tensor): element-wise perspective target areas with a shape of (B, 4, 2).

    Note:
        The generated random numbers are not reproducible across different devices and dtypes. By default,
        the parameters will be generated on CPU in float32. This can be changed by calling
        ``self.set_rng_device_and_dtype(device="cuda", dtype=torch.float64)``.
    """

    def __init__(self, distortion_scale: Union[torch.Tensor, float] = 0.5) -> None:
        super().__init__()
        self.distortion_scale = distortion_scale

    def __repr__(self) -> str:
        repr = f"distortion_scale={self.distortion_scale}"
        return repr

    def make_samplers(self, device: torch.device, dtype: torch.dtype) -> None:
        self._distortion_scale = torch.as_tensor(self.distortion_scale, device=device, dtype=dtype)
        if not (self._distortion_scale.dim() == 0 and 0 <= self._distortion_scale <= 1):
            raise AssertionError(f"'distortion_scale' must be a scalar within [0, 1]. Got {self._distortion_scale}.")
        self.rand_val_sampler = Uniform(
            torch.tensor(0, device=device, dtype=dtype),
            torch.tensor(1, device=device, dtype=dtype),
            validate_args=False,
        )

    def forward(self, batch_shape: torch.Size, same_on_batch: bool = False) -> Dict[str, torch.Tensor]:  # type:ignore
        batch_size = batch_shape[0]
        height = batch_shape[-2]
        width = batch_shape[-1]

        _device, _dtype = _extract_device_dtype([self.distortion_scale])
        _common_param_check(batch_size, same_on_batch)
        if not (type(height) is int and height > 0 and type(width) is int and width > 0):
            raise AssertionError(f"'height' and 'width' must be integers. Got {height}, {width}.")

        start_points: torch.Tensor = torch.tensor(
            [[[0.0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]], device=_device, dtype=_dtype
        ).expand(batch_size, -1, -1)

        # generate random offset not larger than half of the image
        fx = self._distortion_scale * width / 2
        fy = self._distortion_scale * height / 2

        factor = torch.stack([fx, fy], dim=0).view(-1, 1, 2).to(device=_device, dtype=_dtype)

        # TODO: This line somehow breaks the gradcheck
        rand_val: torch.Tensor = _adapted_rsampling(start_points.shape, self.rand_val_sampler, same_on_batch).to(
            device=_device, dtype=_dtype
        )

        pts_norm = torch.tensor([[[1, 1], [-1, 1], [-1, -1], [1, -1]]], device=_device, dtype=_dtype)

        end_points = start_points + factor * rand_val * pts_norm

        return dict(start_points=start_points, end_points=end_points)


@_deprecated(replace_with=PerspectiveGenerator.__name__)
def random_perspective_generator(
    batch_size: int,
    height: int,
    width: int,
    distortion_scale: torch.Tensor,
    same_on_batch: bool = False,
    device: torch.device = torch.device('cpu'),
    dtype: torch.dtype = torch.float32,
) -> Dict[str, torch.Tensor]:
    r"""Get parameters for ``perspective`` for a random perspective transform.

    Args:
        batch_size (int): the tensor batch size.
        height (int) : height of the image.
        width (int): width of the image.
        distortion_scale (torch.Tensor): it controls the degree of distortion and ranges from 0 to 1.
        same_on_batch (bool): apply the same transformation across the batch. Default: False.
        device (torch.device): the device on which the random numbers will be generated. Default: cpu.
        dtype (torch.dtype): the data type of the generated random numbers. Default: float32.

    Returns:
        params Dict[str, torch.Tensor]: parameters to be passed for transformation.
            - start_points (torch.Tensor): element-wise perspective source areas with a shape of (B, 4, 2).
            - end_points (torch.Tensor): element-wise perspective target areas with a shape of (B, 4, 2).

    Note:
        The generated random numbers are not reproducible across different devices and dtypes.
    """
    _common_param_check(batch_size, same_on_batch)
    if not (distortion_scale.dim() == 0 and 0 <= distortion_scale <= 1):
        raise AssertionError(f"'distortion_scale' must be a scalar within [0, 1]. Got {distortion_scale}.")
    if not (type(height) is int and height > 0 and type(width) is int and width > 0):
        raise AssertionError(f"'height' and 'width' must be integers. Got {height}, {width}.")

    start_points: torch.Tensor = torch.tensor(
        [[[0.0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]],
        device=distortion_scale.device,
        dtype=distortion_scale.dtype,
    ).expand(batch_size, -1, -1)

    # generate random offset not larger than half of the image
    fx = distortion_scale * width / 2
    fy = distortion_scale * height / 2

    factor = torch.stack([fx, fy], dim=0).view(-1, 1, 2)

    # TODO: This line somehow breaks the gradcheck
    rand_val: torch.Tensor = _adapted_uniform(
        start_points.shape,
        torch.tensor(0, device=device, dtype=dtype),
        torch.tensor(1, device=device, dtype=dtype),
        same_on_batch,
    ).to(device=distortion_scale.device, dtype=distortion_scale.dtype)

    pts_norm = torch.tensor(
        [[[1, 1], [-1, 1], [-1, -1], [1, -1]]], device=distortion_scale.device, dtype=distortion_scale.dtype
    )
    end_points = start_points + factor * rand_val * pts_norm

    return dict(start_points=start_points, end_points=end_points)
