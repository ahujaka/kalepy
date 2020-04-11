"""
"""

import warnings
import os
import six

import numpy as np
import scipy as sp
import scipy.stats  # noqa
import matplotlib as mpl
import matplotlib.patheffects  # noqa
import matplotlib.pyplot as plt

from kalepy import utils
from kalepy import KDE

_STRETCH = 0.2
_COLOR_CMAP = {
    'k': 'Greys',
    'b': 'Blues',
    'r': 'Reds',
    'g': 'Greens',
    'o': 'Oranges',
    'p': 'Purples',
}
_DEF_SIGMAS = np.arange(0.5, 2.1, 0.5)
_MASK_CMAP = mpl.colors.LinearSegmentedColormap.from_list(
    "white_cmap", [(1, 1, 1), (1, 1, 1)], N=2)


class plot_control:

    def __init__(self, fname, *args, **kwargs):
        self.fname = fname
        self.args = args
        self.kwargs = kwargs
        return

    def __enter__(self):
        plt.close('all')
        return self

    def __exit__(self, type, value, traceback):
        plt.savefig(self.fname, *self.args, **self.kwargs)
        if utils._is_notebook():
            plt.show()
        else:
            plt.close('all')

        return


class Corner:

    def __init__(self, kde_data, labels=None, **figax_kwargs):
        if isinstance(kde_data, KDE):
            kde = kde_data
        else:
            kde = KDE(kde_data)

        data = kde.dataset
        size = len(data)
        # _def_figsize = [10, 10]
        _def_figsize = np.clip(4 * size, 6, 20)
        _def_figsize = [_def_figsize for ii in range(2)]

        last = size - 1
        figax_kwargs.setdefault('figsize', _def_figsize)
        figax_kwargs.setdefault('hspace', 0.1)
        figax_kwargs.setdefault('wspace', 0.1)
        fig, axes = figax(nrows=size, ncols=size, **figax_kwargs)
        self.fig = fig
        self.axes = axes
        if labels is None:
            labels = [''] * size

        for (ii, jj), ax in np.ndenumerate(axes):
            if jj > ii:
                ax.set_visible(False)
                continue
            ax.grid(True)

            if ii == last:
                ax.set_xlabel(labels[jj])
            else:
                ax.set_xlabel('')
                for tlab in ax.xaxis.get_ticklabels():
                    tlab.set_visible(False)

            if jj == 0:
                ax.set_ylabel(labels[ii])
            else:
                ax.set_ylabel('')
                for tlab in ax.yaxis.get_ticklabels():
                    tlab.set_visible(False)

            # Diagonals
            if ii == jj:
                if ii != 0:
                    ax.yaxis.set_label_position('right')
                    ax.yaxis.set_ticks_position('right')

            # Off-Diagonals
            else:
                pass

            self.size = size
            self._data = data
            self._kde = kde

        return

    def data(self, axes=None, data=None, **kwargs):
        if axes is None:
            axes = self.axes
        if data is None:
            data = self._data

        return corner_data(axes, data, **kwargs)

    def kde(self, axes=None, kde=None, **kwargs):
        if axes is None:
            axes = self.axes
        if kde is None:
            kde = self._kde

        return corner_kde(axes, kde, **kwargs)

    def plot(self, kde=None, data=None, **kwargs):
        axes = self.axes
        npar = self.size

        rotate = kwargs.setdefault('rotate', npar == 2)

        if kde is None:
            kde = kwargs.copy()
        if data is None:
            data = kwargs.copy()

        kde.setdefault('hist2d', False)
        data.setdefault('contour', False)

        corner_kde(axes, self._kde, **kde)
        extrema, pdf = _get_corner_axes_extrema(axes, rotate)

        corner_data(axes, self._data, **data)
        extrema, pdf = _get_corner_axes_extrema(axes, rotate, extrema=extrema, pdf=pdf)

        _set_corner_axes(axes, extrema, rotate, pdf=None)

        return

    def savefig(self, fname, **kwargs):
        return _save_fig(self.fig, fname, **kwargs)


def figax(figsize=[12, 6], nrows=1, ncols=1, scale='linear',
          xlabel='', xlim=None, xscale=None,
          ylabel='', ylim=None, yscale=None,
          left=None, bottom=None, right=None, top=None, hspace=None, wspace=None,
          grid=True, squeeze=True, **kwargs):

    if scale is not None:
        xscale = scale
        yscale = scale

    fig, axes = plt.subplots(figsize=figsize, squeeze=False, ncols=ncols, nrows=nrows,
                             **kwargs)

    plt.subplots_adjust(
        left=left, bottom=bottom, right=right, top=top, hspace=hspace, wspace=wspace)

    if ylim is not None:
        shape = (nrows, ncols, 2)
        if np.shape(ylim) == (2,):
            ylim = np.array(ylim)[np.newaxis, np.newaxis, :]
    else:
        shape = (nrows, ncols,)

    ylim = np.broadcast_to(ylim, shape)

    if xlim is not None:
        shape = (nrows, ncols, 2)
        if np.shape(xlim) == (2,):
            xlim = np.array(xlim)[np.newaxis, np.newaxis, :]
    else:
        shape = (nrows, ncols)

    xlim = np.broadcast_to(xlim, shape)

    _, xscale, xlabel = np.broadcast_arrays(axes, xscale, xlabel)
    _, yscale, ylabel = np.broadcast_arrays(axes, yscale, ylabel)

    for idx, ax in np.ndenumerate(axes):
        ax.set(xscale=xscale[idx], xlabel=xlabel[idx],
               yscale=yscale[idx], ylabel=ylabel[idx])
        if xlim[idx] is not None:
            ax.set_xlim(xlim[idx])
        if ylim[idx] is not None:
            ax.set_ylim(ylim[idx])

        if grid is not None:
            if grid in [True, False]:
                ax.grid(grid)
            else:
                ax.grid(True, **grid)

    if squeeze:
        axes = np.squeeze(axes)
        if np.ndim(axes) == 0:
            axes = axes[()]

    return fig, axes


def corner(kde_data, labels=None, **kwargs):
    corner = Corner(kde_data, labels=labels)
    corner.plot(**kwargs)
    return corner


# ======  API Data Methods  ======
# ================================


def corner_data(axes, data, edges=None, levels=None, hist=None, pad=True, rotate=True,
                mask_dense=True, mask_sparse=True, median=True, sigmas=None, density=True,
                hist1d=True, hist2d=True, scatter=True, carpet=True,
                contour=None, contour1d=True, contour2d=True,
                color='k', smap=None, cmap=None):

    shp = np.shape(axes)
    if (np.ndim(axes) != 2) or (shp[0] != shp[1]):
        raise ValueError("`axes` (shape: {}) must be an NxN arrays!".format(shp))

    size = shp[0]
    last = size - 1
    if np.ndim(data) != 2 or np.shape(data)[0] != size:
        err = "`data` (shape: {}) must be 2D with shape (parameters, data-points)!".format(
            np.shape(data))
        raise ValueError(err)

    if hist is not None:
        hist1d = hist
        hist2d = hist

    if contour is not None:
        contour1d = contour
        contour2d = contour

    edges = utils.parse_edges(edges, data)

    extr = [utils.minmax(dd) for dd in data]

    if carpet and not hist1d:
        warnings.warn("Cannot `carpet` without `hist1d`!")
        carpet = False

    smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)

    #
    # Calculate Distributions
    # ================================
    #

    data_hist1d = np.empty(size, dtype=object)
    data_hist2d = np.empty(shp, dtype=object)
    extr_hist2d = None
    for (ii, jj), ax in np.ndenumerate(axes):
        if jj > ii:
            continue

        # Diagonals
        # ----------------------
        xx = data[jj]
        if ii == jj:
            data_hist1d[jj], _ = np.histogram(xx, bins=edges[jj], density=density)

        # Off-Diagonals
        # ----------------------
        else:
            yy = data[ii]
            bins = [edges[jj], edges[ii]]
            data_hist2d[jj, ii], *_ = np.histogram2d(xx, yy, bins=bins, density=density)
            extr_hist2d = utils.minmax(
                data_hist2d[jj, ii], prev=extr_hist2d, positive=smap_is_log)

    _set_corner_axes(axes, extr, rotate)

    #
    # Draw / Plot Data
    # ===========================
    #

    # Draw 1D Histograms & Carpets
    # -----------------------------------------
    for jj, ax in enumerate(axes.diagonal()):
        rot = (rotate and (jj == last))

        dist1d_data(ax, edges[jj], hist=data_hist1d[jj], data=data[jj],
                    sigmas=sigmas, color=color, density=density, rotate=rot,
                    median=median, hist1d=hist1d, carpet=carpet, contour=contour1d)

    # Draw 2D Histograms and Contours
    # -----------------------------------------
    smap = _get_smap(extr_hist2d, **smap)

    for (ii, jj), ax in np.ndenumerate(axes):
        if jj >= ii:
            continue

        dist2d_data(ax, [edges[jj], edges[ii]],
                    hist=data_hist2d[jj, ii], data=[data[jj], data[ii]],
                    sigmas=sigmas, color=color, smap=smap, cmap=cmap,
                    median=median, hist2d=hist2d, contour=contour2d, scatter=scatter)

    return


def dist1d_data(ax, edges=None, hist=None, data=None,
                sigmas=None, color='k', density=True, rotate=False,
                contour=True, median=None, hist1d=True, carpet=None):

    if carpet is None:
        carpet = (data is not None)

    if median is None:
        median = carpet

    hist1d = _none_dict(hist1d, 'hist1d', dict(color=color))
    carpet = _none_dict(carpet, 'carpet', dict(color=color))

    edges = utils.parse_edges(edges, data)
    if (hist is None) and (data is None):
        raise ValueError("Either `hist` or `data` must be provided!")

    if hist is None:
        hist, _ = np.histogram(data, bins=edges, density=density)

    if np.shape(hist) != (len(edges) - 1,):
        raise ValueError("Shape of `hist` ({}) does not match edges ({})!".format(
            np.shape(hist), len(edges)))

    if hist1d is not None:
        _draw_hist1d(ax, edges, hist=hist, data=data,
                     rotate=rotate, **hist1d)

    if contour or median:
        sigmas = _get_def_sigmas(sigmas, contour=contour, median=median)

        # Calculate Cumulative Distribution Function
        data = np.sort(data)
        cdf = np.arange(data.size) / (data.size - 1)
        # Convert from standard-deviations to percentiles
        percs = sp.stats.norm.cdf(sigmas)
        # Get both the lower (left) and upper (right) values
        percs = np.append(1 - percs, percs)
        # Reshape to (sigmas, 2)
        locs = np.interp(percs, cdf, data).reshape(2, len(sigmas)).T

        _draw_contours_1d(ax, locs, color=color, rotate=rotate)

    if carpet is not None:
        _, _extr = draw_carpet(data, ax=ax,  rotate=rotate, **carpet)

    return


def dist2d_data(ax, edges=None, hist=None, data=None, sigmas=None,
                color='k', smap=None, cmap=None,
                scatter=None, median=None, hist2d=True, contour=True, density=True,
                pad=True, mask_dense=True, mask_sparse=True):

    if scatter is None:
        scatter = (data is not None)
    if median is None:
        median = scatter

    hist2d = _none_dict(hist2d, 'hist2d', dict(smap=smap, cmap=cmap, color=color))
    scatter = _none_dict(scatter, 'scatter', dict(color=color))
    contour = _none_dict(contour, 'contour', dict(smap=smap, cmap=cmap, color=color))

    edges = utils.parse_edges(edges, data)
    extr = [[ee.min(), ee.max()] for ee in edges]
    gsh = tuple([len(ee)-1 for ee in edges])
    if (hist is None) and (data is None):
        raise ValueError("Either `hist` or `data` must be provided!")

    if hist is None:
        hist, *_ = np.histogram2d(*data, bins=edges, density=density)

    if np.shape(hist) != gsh:
        raise ValueError("Shape of `hist` ({}) does not match edges ({})!".format(
            np.shape(hist), gsh))

    if sigmas is None:
        sigmas = _DEF_SIGMAS

    pdf_levels, _levels = _dfm_levels(hist, sigmas=sigmas)

    # smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)
    # if not isinstance(smap, mpl.cm.ScalarMappable):
    #     smap = _get_smap(hist, **smap)

    # Draw Scatter Points
    # -------------------------------
    if scatter is not None:
        _draw_scatter(ax, *data, **scatter)

    # Draw Median Lines (Target Style)
    # -----------------------------------------
    if median:
        effects = ([
            mpl.patheffects.Stroke(linewidth=2.0, foreground='0.75', alpha=0.75),
            mpl.patheffects.Normal()
        ])

        for dd, func in zip(data, [ax.axvline, ax.axhline]):
            med = np.median(dd)
            func(med, color=color, ls='-', alpha=0.5, lw=1.0, path_effects=effects)

    # Pad Histogram for Smoother Contour Edges
    # -----------------------------------------------
    if pad:
        hist = np.pad(hist, 2, mode='edge')
        tf = np.arange(2)  # [+1, +2]
        tr = - tf[::-1]    # [-2, -1]
        edges = [
            [ee[0] + tr * np.diff(ee[:2]), ee, ee[-1] + tf * np.diff(ee[-2:])]
            for ee in edges
        ]
        edges = [np.concatenate(ee) for ee in edges]

    xc, yc = [utils.midpoints(ee, axis=-1) for ee in edges]
    xc, yc = np.meshgrid(xc, yc, indexing='ij')

    # Mask dense scatter-points
    if mask_dense and (scatter is not None):
        span = [pdf_levels.min(), hist.max()]
        ax.contourf(xc, yc, hist, span,
                    cmap=_MASK_CMAP, antialiased=True)

    # Draw 2D Histogram
    # -------------------------------
    if hist2d is not None:
        # hist2d.setdefault('cmap', smap.cmap)
        # hist2d.setdefault('norm', smap.norm)
        if mask_sparse is True:
            mask_sparse = pdf_levels.min()
        _draw_hist2d(ax, *edges, hist, mask_below=mask_sparse, **hist2d)

    # Draw Contours
    # --------------------------------
    if contour is not None:
        _draw_contours_2d(ax, xc, yc, hist, **contour)

    for ex, lim_func in zip(extr, [ax.set_xlim, ax.set_ylim]):
        lim_func(ex)

    return


# ======  API KDEs Methods  ======
# ================================


def corner_kde(axes, kde, edges=None, reflect=None, sigmas=None, levels=None, rotate=True,
               median=True, hist2d=True, contour=None, contour1d=True, contour2d=True,
               color='k', smap=None, cmap=None):

    shp = np.shape(axes)
    if (np.ndim(axes) != 2) or (shp[0] != shp[1]):
        raise ValueError("`axes` (shape: {}) must be an NxN arrays!".format(shp))

    size = shp[0]
    last = size - 1

    if edges is None:
        edges = kde._guess_edges()

    if contour is not None:
        contour1d = contour
        contour2d = contour

    # pdf = kde.pdf_grid(edges, reflect=reflect)
    extr = [utils.minmax(ee) for ee in edges]
    smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)

    #
    # Calculate Distributions
    # ================================
    #

    pdf1d = np.full(size, None, dtype=object)
    pdf2d = np.full(shp, None, dtype=object)
    extr_hist2d = None
    for (ii, jj), ax in np.ndenumerate(axes):
        if jj > ii:
            continue

        # Diagonals
        # ----------------------
        if ii == jj:
            pdf1d[jj] = kde.pdf_grid(edges[jj], params=jj, reflect=reflect)

        # Off-Diagonals
        # ----------------------
        else:
            pdf2d[jj, ii] = kde.pdf_grid([edges[jj], edges[ii]], params=[jj, ii], reflect=reflect)
            extr_hist2d = utils.minmax(pdf2d[jj, ii], prev=extr_hist2d, positive=smap_is_log)

    _set_corner_axes(axes, extr, rotate)

    #
    # Draw / Plot Data
    # ===========================
    #

    # Draw 1D Histograms & Carpets
    # -----------------------------------------
    for jj, ax in enumerate(axes.diagonal()):
        rot = (rotate and (jj == last))
        dist1d_kde(ax, kde, pdf=pdf1d[jj], param=jj, reflect=reflect, color=color, rotate=rot,
                   sigmas=sigmas, median=median, contour=contour1d)

    # Draw 2D Histograms and Contours
    # -----------------------------------------
    # _smap = _get_smap(extr_hist2d, **smap)

    for (ii, jj), ax in np.ndenumerate(axes):
        if jj >= ii:
            continue

        _smap = _get_smap(pdf2d[jj, ii], **smap)
        dist2d_kde(ax, kde, params=(jj, ii), pdf=pdf2d[jj, ii], reflect=reflect,
                   sigmas=sigmas, color=color, smap=_smap, cmap=cmap,
                   median=median, hist2d=hist2d, contour=contour2d)

    return


def dist1d_kde(ax, kde, param=None, pdf=None, reflect=None, edges=None, sigmas=True, color='k',
               contour=True, median=True, rotate=False):

    if (param is None):
        if kde.ndim > 1:
            raise ValueError("`kde` has {} dimensions, `param` required!".format(kde.ndim))

        param = 0

    edges = kde._guess_edges()[param]
    if pdf is None:
        pdf = kde.pdf(edges, reflect=reflect, params=param)

    vals = [edges, pdf]
    if rotate:
        vals = vals[::-1]
    ax.plot(*vals, color=color)

    if contour or median:
        sigmas = _get_def_sigmas(sigmas, contour=contour, median=median)
        # Convert from standard-deviations to percentiles
        percs = sp.stats.norm.cdf(sigmas)
        # NOTE: currently `kde.cdf` does not work with `params`... once it does, use that!
        cdf = utils.cumtrapz(pdf, edges)
        # Normalize to the maximum value
        cdf /= cdf.max()
        # Get both the lower (left) and upper (right) values
        percs = np.append(1 - percs, percs)
        # Reshape to (sigmas, 2)
        locs = np.interp(percs, cdf, edges).reshape(2, len(sigmas)).T

        _draw_contours_1d(ax, locs, color=color, rotate=rotate)

    return


def dist2d_kde(ax, kde, params=None, pdf=None, reflect=None, color='k', smap=None, cmap=None,
               hist2d=True, contour=True, sigmas=None, median=True):
    # from datetime import datetime

    if (params is None):
        if kde.ndim > 2:
            raise ValueError("`kde` has {} dimensions, `params` required!".format(kde.ndim))

        params = (0, 1)

    hist2d = _none_dict(hist2d, 'hist2d', dict())
    contour = _none_dict(contour, 'contour', dict())

    edges = kde._guess_edges()
    edges = [edges[pp] for pp in params]

    if pdf is None:
        pdf = kde.pdf_grid(edges, params=params, reflect=reflect)
    xx, yy = np.meshgrid(*edges, indexing='ij')

    pdf_levels, _levels = _dfm_levels(pdf, sigmas=sigmas)

    smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)
    if not isinstance(smap, mpl.cm.ScalarMappable):
        smap = _get_smap(pdf, **smap)

    # Draw 2D Histogram
    # -------------------------------
    if hist2d is not None:
        hist2d.setdefault('cmap', smap.cmap)
        hist2d.setdefault('norm', smap.norm)
        _draw_hist2d(ax, *edges, pdf, **hist2d)

    # Draw Median Lines (Target Style)
    # -----------------------------------------
    if median:
        effects = ([
            mpl.patheffects.Stroke(linewidth=2.0, foreground='0.75', alpha=0.75),
            mpl.patheffects.Normal()
        ])

        for ii, func in enumerate([ax.axvline, ax.axhline]):
            pp = params[ii]
            ee = edges[ii]
            cdf = kde.pdf(ee, reflect=reflect, params=pp)
            cdf = utils.cumtrapz(cdf, ee)
            cdf /= cdf.max()
            cdf = np.interp(0.5, cdf, ee)
            func(cdf, color=color, ls='-', alpha=0.5, lw=1.0, path_effects=effects)

    # Draw Contours
    # --------------------------------
    if contour is not None:
        _draw_contours_2d(ax, xx, yy, pdf, smap, sigmas=sigmas, **contour)

    return


def _get_def_sigmas(sigmas, contour=True, median=True):
    if (sigmas is False) or (contour is False):
        sigmas = []
    elif (sigmas is True) or (sigmas is None):
        sigmas = _DEF_SIGMAS

    if median:
        sigmas = np.append([0.0], sigmas)

    return sigmas


# ======  Drawing Methods  =====
# ==============================


def draw_carpet(xx, ax=None, ystd=None, yave=None, fancy=False, random='normal',
                rotate=False, **kwargs):
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

    return ax.scatter(xx, yy, **kwargs), extr


def _draw_scatter(ax, xx, yy, color='k', alpha=0.1, s=4, **kwargs):
    kwargs.setdefault('facecolor', color)
    kwargs.setdefault('edgecolor', 'none')
    kwargs.setdefault('alpha', alpha)
    kwargs.setdefault('s', s)
    # kwargs.setdefault('zorder', 80)
    return ax.scatter(xx, yy, **kwargs)


def _draw_hist2d(ax, xx, yy, data, mask_below=None, color=None, smap=None, **kwargs):
    cmap = kwargs.pop('cmap')
    smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)
    if not isinstance(smap, mpl.cm.ScalarMappable):
        smap = _get_smap(data, **smap)

    kwargs.setdefault('cmap', smap.cmap)
    kwargs.setdefault('norm', smap.norm)

    if (mask_below is not None) and (mask_below is not False):
        data = np.ma.masked_less_equal(data, mask_below)
    ax.pcolormesh(xx, yy, data.T, **kwargs)
    return


def _draw_contours_1d(ax, locs, color='k', span=None, rotate=False, alpha=0.1):
    kw = dict(facecolor=color, alpha=alpha, edgecolor='none')

    for lo, hi in locs:
        # If median is included (sigma=0, cdf=0.5), lo will equal hi
        if lo == hi:
            line_func = ax.axhline if rotate else ax.axvline
            line_func(lo, ls='--', color=color, alpha=0.5)

        if span is None:
            span_func = ax.axhspan if rotate else ax.axvspan
            span_func(lo, hi, **kw)
        else:
            center = [lo, span[0]]
            extent = [hi - lo, span[1] - span[0]]
            if rotate:
                center = center[::-1]
                extent = span[::-1]
            rect = mpl.patches.Rectangle(center, *extent, **kw)
            ax.add_patch(rect)

    return


def _draw_contours_2d(ax, xx, yy, hist, smap=None, color=None, cmap=None,
                      linewidths=1.0, alpha=0.8, colors=None, zorder=10,
                      background=True, sigmas=None, levels=None, **kwargs):
    pdf_levels, levels = _dfm_levels(hist, cdf_levels=levels, sigmas=sigmas)
    lw = kwargs.pop('lw', None)
    bg_alpha = alpha  # /2
    if lw is not None:
        linewidths = lw
    kwargs['levels'] = pdf_levels
    background = _none_dict(background, 'background', defaults=kwargs)

    if colors is None:
        smap, smap_is_log = _parse_smap(smap, color, cmap=cmap)
        if not isinstance(smap, mpl.cm.ScalarMappable):
            smap = _get_smap(hist, **smap)

        colors_bg = smap.to_rgba(pdf_levels)
        colors = colors_bg[::-1]

        # colors_bg = [0.8] * 3 + [bg_alpha]
        # colors = smap.to_rgba(pdf_levels)

        # colors_bg = smap.to_rgba(pdf_levels)
        # colors = np.array([_invert_color(cc) for cc in colors_bg])

        # Set alpha (transparency)
        colors[:, 3] = alpha
        colors_bg[:, 3] = bg_alpha
    else:
        colors_bg = ['0.5'] * 3 + [bg_alpha]

    background.setdefault('colors', colors_bg)
    background.setdefault('linewidths', 2*linewidths)
    background.setdefault('zorder', zorder - 1)

    kwargs['colors'] = colors
    kwargs['linewidths'] = linewidths
    kwargs['zorder'] = zorder

    if background:
        ax.contour(xx, yy, hist, **background)

    ax.contour(xx, yy, hist, **kwargs)

    return


def _draw_hist1d(ax, edges, hist=None, data=None, joints=False,
                 nonzero=False, positive=False, extend=None,
                 rotate=False, **kwargs):

    if hist is None:
        hist, _ = np.histogram(data, bins=edges, density=True)

    # Extend bin edges if needed
    if len(edges) != len(hist)+1:
        raise RuntimeError("``edges`` must have length hist+1!")

    # Construct plot points to manually create a step-plot
    xval = np.hstack([[edges[jj], edges[jj+1]] for jj in range(len(edges)-1)])
    yval = np.hstack([[hh, hh] for hh in hist])

    if not joints:
        size = len(xval)
        half = size // 2

        outs = []
        for zz in [xval, yval]:
            zz = np.atleast_2d(zz).T
            zz = np.reshape(zz, [half, 2], order='C')
            zz = np.pad(zz, [[0, 0], [0, 1]], constant_values=np.nan)
            zz = zz.reshape(size + half)
            outs.append(zz)

        xval, yval = outs

    # Select nonzero values
    if nonzero:
        xval = np.ma.masked_where(yval == 0.0, xval)
        yval = np.ma.masked_where(yval == 0.0, yval)

    # Select positive values
    if positive:
        xval = np.ma.masked_where(yval < 0.0, xval)
        yval = np.ma.masked_where(yval < 0.0, yval)

    if rotate:
        temp = np.array(xval)
        xval = yval
        yval = temp

    # Plot Histogram
    line, = ax.plot(xval, yval, **kwargs)

    return line


def _set_corner_axes(axes, extrema, rotate, pdf=None):
    npar = len(axes)
    last = npar - 1
    if not np.all([sh == npar for sh in np.shape(axes)]):
        raise ValueError("`axes` (shape: {}) must be square!".format(np.shape(axes)))

    if len(extrema) == 2 and npar != 2:
        extrema = [extrema] * npar

    if len(extrema) != npar:
        err = "Length of `extrema` (shape: {}) does not match axes shape ({}^2)!".format(
            np.shape(extrema), npar)
        raise ValueError(err)

    if (pdf is not None) and (len(pdf) != 2 or not utils.really1d(pdf)):
        raise ValueError("`pdf` (shape: {}) must be length 2!".format(np.shape(pdf)))

    for (ii, jj), ax in np.ndenumerate(axes):
        if jj > ii:
            ax.set_visible(False)
            continue

        # Diagonals
        # ----------------------
        if ii == jj:
            rot = (rotate and (jj == last))
            set_lim_func = ax.set_ylim if rot else ax.set_xlim
            set_lim_func(extrema[jj])

        # Off-Diagonals
        # ----------------------
        else:
            ax.set_xlim(extrema[jj])
            ax.set_ylim(extrema[ii])

    return extrema


def _get_corner_axes_extrema(axes, rotate, extrema=None, pdf=None):
    npar = len(axes)
    last = npar - 1
    if not np.all([sh == npar for sh in np.shape(axes)]):
        raise ValueError("`axes` (shape: {}) must be square!".format(np.shape(axes)))

    if extrema is None:
        extrema = npar * [None]

    for (ii, jj), ax in np.ndenumerate(axes):
        if jj > ii:
            continue

        if ii == jj:
            pdf_func = ax.get_xlim if (rotate and (ii == last)) else ax.get_ylim
            oth_func = ax.get_ylim if (rotate and (ii == last)) else ax.get_xlim
            pdf = utils.minmax(pdf_func(), prev=pdf)
            extrema[jj] = utils.minmax(oth_func(), prev=extrema[jj])

        else:
            extrema[jj] = utils.minmax(ax.get_xlim(), prev=extrema[jj])
            extrema[ii] = utils.minmax(ax.get_ylim(), prev=extrema[ii])

    return extrema, pdf


# ====  Utility Methods  ====
# ===========================


def nbshow():
    return utils.run_if_notebook(plt.show, otherwise=lambda: plt.close('all'))


def _save_fig(fig, fname, path=None, subdir=None, quiet=False, rename=True, **kwargs):
    """Save the given figure to the given filename, with some added niceties.
    """
    if path is None:
        path = os.path.abspath(os.path.curdir)
    if subdir is not None:
        path = os.path.join(path, subdir, '')
    fname = os.path.join(path, fname)
    utils.check_path(fname)
    if rename:
        fname = utils.modify_exists(fname)
    fig.savefig(fname, **kwargs)
    if not quiet:
        print("Saved to '{}'".format(fname))
    return fname


def _get_smap(args=[0.0, 1.0], cmap=None, log=False, norm=None, under='w', over='w'):
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


def _parse_smap(smap, color, cmap=None, defaults=dict(log=False)):
    if isinstance(smap, mpl.cm.ScalarMappable):
        # If `smap` was created with `kalepy.plot._get_smap()` than it should have this attribute
        try:
            smap_is_log = smap._log
        # Otherwise assume it's linear
        # NOTE: this might be wrong.  Better way to check?
        except AttributeError:
            smap_is_log = False

        return smap, smap_is_log

    if smap is None:
        smap = {}

    if not isinstance(smap, dict):
        raise ValueError("`smap` must either be a dict or ScalarMappable!")

    for kk, vv in defaults.items():
        smap.setdefault(kk, vv)

    smap_is_log = smap['log']
    if cmap is None:
        cmap = _COLOR_CMAP.get(color[0], 'Greys')

    smap.setdefault('cmap', cmap)

    return smap, smap_is_log


def _none_dict(val, name, defaults={}):
    """

    False/None  ===>  None
    True/dict   ===>  dict
    otherwise   ===>  error

    """
    if (val is False) or (val is None):
        return None

    if val is True:
        val = dict()

    if not isinstance(val, dict):
        raise ValueError("Unrecognized type '{}' for `{}`!".format(type(val), name))

    for kk, vv in defaults.items():
        val.setdefault(kk, vv)

    return val


def _dfm_levels(hist, cdf_levels=None, sigmas=None):
    if cdf_levels is None:
        if sigmas is None:
            sigmas = _DEF_SIGMAS
        # Convert from standard-deviations to CDF values
        cdf_levels = 1.0 - np.exp(-0.5 * np.square(sigmas))

    # Compute the density levels.
    hflat = hist.flatten()
    inds = np.argsort(hflat)[::-1]
    hflat = hflat[inds]
    sm = np.cumsum(hflat)
    sm /= sm[-1]
    pdf_levels = np.empty(len(cdf_levels))
    for i, v0 in enumerate(cdf_levels):
        try:
            pdf_levels[i] = hflat[sm <= v0][-1]
        except:
            pdf_levels[i] = hflat[0]

    pdf_levels.sort()
    bad = (np.diff(pdf_levels) == 0)
    bad = np.pad(bad, [1, 0], constant_values=False)

    # -- Remove Bad Levels
    pdf_levels = np.delete(pdf_levels, np.where(bad)[0])
    if np.any(bad):
        _levels = cdf_levels
        cdf_levels = np.array(cdf_levels)[~bad]
        print("Removed bad levels: '{}' ==> '{}'".format(_levels, cdf_levels))

    # -- Adjust Bad Levels:
    # if np.any(bad) and not quiet:
    #     logging.warning("Too few points to create valid contours")
    # while np.any(bad):
    #     V[np.where(bad)[0][0]] *= 1.0 - 1e-4
    #     m = np.diff(V) == 0
    pdf_levels.sort()
    return pdf_levels, cdf_levels


'''
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
'''

'''
def _draw_colorbar_contours(cbar, levels, colors=None, smap=None):
    ax = cbar.ax

    if colors is None:
        if smap is None:
            colors = ['0.5' for ll in levels]
        else:
            colors = [smap.to_rgba(ll) for ll in levels]
            # colors = [_invert_color(cc) for cc in colors]

    orient = cbar.orientation
    if orient.startswith('v'):
        line_func = ax.axhline
    elif orient.startswith('h'):
        line_func = ax.axvline
    else:
        raise RuntimeError("UNKNOWN ORIENTATION '{}'!".format(orient))

    for ll, cc, bg in zip(levels, colors, colors[::-1]):
        effects = ([
            mpl.patheffects.Stroke(linewidth=4.0, foreground=bg, alpha=0.5),
            mpl.patheffects.Normal()
        ])
        line_func(ll, 0.0, 1.0, color=cc, path_effects=effects, lw=2.0)

    return
'''

'''
def _invert_color(col):
    rgba = mpl.colors.to_rgba(col)
    alpha = rgba[-1]
    col = 1.0 - np.array(rgba[:-1])
    col = tuple(col.tolist() + [alpha])
    return col
'''

'''
if colorbar:
    if fig is None:
        fig = plt.gcf()

    # bbox = ax.get_position()
    # cbax = fig.add_axes([bbox.x1+PAD, bbox.y0, 0.03, bbox.height])

    # if size in [2, 3]:
    bbox = axes[0, -1].get_position()
    left = bbox.x0
    width = bbox.width
    top = bbox.y1
    height = 0.04
    # elif size in [4, 5]
    #     bbox = axes[0, -2].get_position()
    #     left = bbox.x0
    #     width = bbox.width

    cbax = fig.add_axes([left, top - height, width, height])
    cbar = plt.colorbar(smap, orientation='horizontal', cax=cbax)
    _draw_colorbar_contours(cbar, pdf_levels, smap=smap)
'''
