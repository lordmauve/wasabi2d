"""Generate plots of the tweeners, to include in docs."""
import os
from matplotlib import pyplot as plt
import numpy as np

from wasabi2d import animation

IMAGE_SIZE = 64, 64


def plot(f, filename):
    num_points = 256
    x = np.linspace(0, 1, num_points)
    y = np.vectorize(f)(x)
    plt.figure(figsize=(3, 1.5), dpi=num_points)
    plt.axis('off')
    plt.plot(x, y, color='#657907')
    plt.savefig(filename, dpi=num_points)
    plt.tight_layout()
    plt.close()


if __name__ == '__main__':
    try:
        os.mkdir('_static/tween/')
    except FileExistsError:
        pass
    for name, f in animation.TWEEN_FUNCTIONS.items():
        filename = '_static/tween/{}.png'.format(name)
        plot(f, filename)
