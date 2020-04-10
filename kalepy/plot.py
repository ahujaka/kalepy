"""Plotting methods
"""

import os
import six

import numpy as np
import matplotlib as mpl  # noqa
from matplotlib import pyplot as plt

from kalepy import utils


def align_axes_loc(tw, ax, ymax=None, ymin=None, loc=0.0):
    if ((ymax is None) and (ymin is None)) or ((ymin is not None) and (ymax is not None)):
        raise ValueError("Either `ymax` or `ymin`, and not both, must be provided!")

    ylim = np.array(ax.get_ylim())
    # beg = np.array(tw.get_ylim())

    hit = np.diff(ylim)[0]
    frac_up = (loc - ylim[0]) / hit
    frac_dn = 1 - frac_up

    new_ylim = [0.0, 0.0]
    if ymax is not None:
        new_ylim[1] = ymax
        new_hit = (ymax - loc) / frac_dn
        new_ylim[0] = ymax - new_hit

    if ymin is not None:
        new_ylim[0] = ymin
        new_hit = (loc - ymin) / frac_up
        new_ylim[1] = ymax - new_hit

    tw.set_ylim(new_ylim)
    return new_ylim


def draw_carpet_fuzz(xx, ax=None, ystd=None, yave=None, rotate=False, fancy=False, random='normal',
                     **kwargs):
    """Draw a carpet plot on the given axis in the 'fuzz' style.

    Arguments
    ---------
    xx : values to plot
    ax : matplotlib.axis.Axis
    kwargs : key-value pairs
        Passed to `matplotlib.axes.Axes.scatter()`

    """
    if ax is None:
        ax = plt.gca()

    # Dispersion (yaxis) of the fuzz values
    if ystd is None:
        if yave is None:
            get_lim_func = ax.get_xlim if rotate else ax.get_ylim
            ystd = get_lim_func()[1] * 0.02
        else:
            ystd = np.fabs(yave) / 5.0

    # Baseline on the yaxis at which the fuzz is plotted
    if yave is None:
        yave = -5.0 * ystd

    # General random y-values for the fuzz
    if random.lower() == 'normal':
        yy = np.random.normal(yave, ystd, size=xx.size)
    elif random.lower() == 'uniform':
        yy = np.random.uniform(yave-ystd, yave+ystd, size=xx.size)
    else:
        raise ValueError("Unrecognized `random` = '{}'!".format(random))

    # Choose an appropriate opacity
    alpha = np.clip(10 / np.sqrt(xx.size), 1e-4, 3e-1)

    # Choose sizes proportional to their deviation (to make outliers more visible)
    size = np.clip(300 / np.sqrt(xx.size), 5, 100)

    if fancy:
        # Estimate the deviation of each point from the median
        dev = np.fabs(xx - np.median(xx)) / np.std(xx)
        # Rescale the y-values based on their deviation from median
        yy = (yy - yave) / (np.sqrt(dev) + 1) + yave
        # Choose sizes proportional to their deviation (to make outliers more visible)
        size = (size / 1.5) * (1.5 + dev)

    # size = 10
    # alpha = 1.0

    # Set parameters
    color = kwargs.pop('color', 'red')
    kwargs.setdefault('facecolor', color)
    kwargs.setdefault('edgecolor', 'none')
    kwargs.setdefault('marker', '.')
    kwargs.setdefault('alpha', alpha)
    kwargs.setdefault('s', size)

    extr = utils.minmax(yy)
    trans = [ax.transData, ax.transAxes]
    if rotate:
        temp = xx
        xx = yy
        yy = temp
        trans = trans[::-1]

    # trans = mpl.transforms.blended_transform_factory(*trans)
    # print("carpet yy = ", utils.stats_str(yy))

    return ax.scatter(xx, yy, **kwargs), extr


def smap(args=[0.0, 1.0], cmap=None, log=False, norm=None, under='w', over='w'):
    args = np.asarray(args)

    if not isinstance(cmap, mpl.colors.Colormap):
        if cmap is None:
            cmap = 'viridis'
        if isinstance(cmap, six.string_types):
            cmap = plt.get_cmap(cmap)

    if under is not None:
        cmap.set_under(under)
    if over is not None:
        cmap.set_over(over)

    vmin, vmax = utils.minmax(args, positive=log)
    if vmin == vmax:
        raise ValueError("`smap` extrema are identical: {}, {}!".format(vmin, vmax))

    if log:
        norm = mpl.colors.LogNorm(vmin=vmin, vmax=vmax)
    else:
        norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    # Create scalar-mappable
    smap = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    # Bug-Fix something something
    smap._A = []
    smap._log = log

    return smap


def nbshow():
    return utils.run_if_notebook(plt.show, otherwise=lambda: plt.close('all'))


def save_fig(fig, fname, path=None, quiet=False, rename=True, **kwargs):
    """Save the given figure to the given filename, with some added niceties.
    """
    if path is None:
        path = os.path.abspath(os.path.curdir)
    fname = os.path.join(path, fname)
    utils.check_path(fname)
    if rename:
        fname = utils.modify_exists(fname)
    fig.savefig(fname, **kwargs)
    if not quiet:
        print("Saved to '{}'".format(fname))
    return fname


class plot_control:

    def __init__(self, fname, *args, **kwargs):
        self.fname = fname
        self.args = args
        self.kwargs = kwargs
        return

    def __enter__(self):
        # if not _is_notebook():
        #     raise _DummyError

        plt.close('all')
        return self

    def __exit__(self, type, value, traceback):
        # if isinstance(value, _DummyError):
        #     return True

        plt.savefig(self.fname, *self.args, **self.kwargs)
        if utils._is_notebook():
            plt.show()
        else:
            plt.close('all')

        return
