"""
"""

# import warnings
import logging
# import os
# import six

import numpy as np
import scipy as sp
import scipy.stats  # noqa
import matplotlib as mpl
import matplotlib.patheffects  # noqa
import matplotlib.pyplot as plt

import kalepy as kale
from kalepy import utils
from kalepy import KDE

_DEF_SIGMAS = [0.5, 1.0, 1.5, 2.0]
_MASK_CMAP = mpl.colors.LinearSegmentedColormap.from_list(
    "white_cmap", [(1, 1, 1), (1, 1, 1)], N=2)
_OUTLINE = ([
    mpl.patheffects.Stroke(linewidth=2.0, foreground='white', alpha=0.85),
    mpl.patheffects.Normal()
])


class Corner:

    _LW = 2.0
    _LIMITS_STRETCH = 0.1

    def __init__(self, kde_data, weights=None, labels=None, limits=None, rotate=None, **kwfig):
        """Construct a figure and axes for creating a 'corner' plot.

        Arguments
        ---------
        kde_data : object, one of the following
            * instance of `kalepy.kde.KDE`, including the data to be plotted,
            * array_like scalar (D,N) of data with `D` parameters and `N` data points,
            * int D, the number of parameters to construct a DxD corner plot.

        weights : array_like scalar (N,) or None
            The weights for each data point.
            NOTE: only applicable when `kde_data` is a (D,N) dataset.

        labels : array_like string (N,) of labels/names for each parameters.

        limits : None or (2,) or (D,) of [None or (2,)]
            Specification for the limits of each axes (for each of `D` parameters):
            * None : the limits are determined automatically,
            * (2,) : limits to be applied to all axes,
            * (3,) : limits for each axis, where each entry can be either 'None' or (2,)

        **kwfig : keyword-arguments passed to `_figax()` for constructing figure and axes.
            See `kalepy.plot._figax()` for specifications.

        """

        # --- Parse the given `kde_data` and store parameters accordingly --
        if np.isscalar(kde_data):
            if not isinstance(kde_data, int):
                err = ("If `kde_data` is a scalar, it must be an integer "
                       "specifying the number of parameters!")
                raise ValueError(err)
            size = kde_data
            kde = None
            data = None
        else:
            kde, data, weights = _parse_kde_data(kde_data, weights=weights)
            size = kde._ndim

        if limits is None:
            limits = [None] * size
            limit_flag = True
        else:
            limit_flag = False

        if rotate is None:
            rotate = (size in [2, 3])

        # -- Construct figure and axes using `_figax()`
        fig, axes = _figax(size, **kwfig)
        self.fig = fig
        self.axes = axes

        # -- Setup axes
        last = size - 1
        if labels is None:
            labels = [''] * size

        for (ii, jj), ax in np.ndenumerate(axes):
            # Set upper-right plots to invisible
            if jj > ii:
                ax.set_visible(False)
                continue
            ax.grid(True)

            # Bottom row
            if ii == last:
                ax.set_xlabel(labels[jj])
            # Non-bottom row
            else:
                ax.set_xlabel('')
                for tlab in ax.xaxis.get_ticklabels():
                    tlab.set_visible(False)

            # First column
            if jj == 0:
                # Not-first rows
                if ii != 0:
                    ax.set_ylabel(labels[ii])
            # Not-first columns
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

        # --- Store key parameters
        self.size = size
        self._kde = kde
        self._data = data
        self._weights = weights
        self._limits = limits
        self._limit_flag = limit_flag
        self._rotate = rotate

        return

    def plot(self, kde_data=None, edges=None, weights=None, rotate=None, quantiles=None,
             limit=None, color=None, cmap=None, dist1d={}, dist2d={}):

        if kde_data is None:
            # If either data or a KDE was given on initialization, `self._kde` will be set
            kde_data = self._kde
            if kde_data is None:
                err = "kde or data required either during initialization or here!"
                raise ValueError(err)

        kde, data, weights = _parse_kde_data(kde_data, weights=weights)

        dist1d.setdefault('density', True)
        dist1d.setdefault('contour', True)
        dist1d.setdefault('carpet', True)
        dist1d.setdefault('hist', False)

        dist2d.setdefault('hist', True)
        dist2d.setdefault('scatter', True)
        dist2d.setdefault('contour', True)
        dist2d.setdefault('mask_dense', True)
        dist2d.setdefault('mask_below', True)

        rv = self.plot_kde(
            kde, edges=edges, rotate=rotate, quantiles=quantiles,
            limit=limit, color=color, cmap=cmap,
            dist1d=dist1d, dist2d=dist2d
        )
        return rv

    def clean(self, kde_data=None, weights=None, **kwargs):
        if kde_data is None:
            # If either data or a KDE was given on initialization, `self._kde` will be set
            kde_data = self._kde
            if kde_data is None:
                err = "kde or data required either during initialization or here!"
                raise ValueError(err)

        kde, data, weights = _parse_kde_data(kde_data, weights=weights)

        dist1d.setdefault('density', True)
        dist1d.setdefault('contour', False)
        dist1d.setdefault('carpet', False)
        dist1d.setdefault('hist', False)

        dist2d.setdefault('hist', False)
        dist2d.setdefault('contour', True)
        dist2d.setdefault('scatter', False)
        dist2d.setdefault('mask_dense', False)
        dist2d.setdefault('mask_below', False)

        return self.plot_kde(kde, dist1d=dist1d, dist2d=dist2d, **kwargs)

    def hist(self, kde_data=None, weights=None, dist1d={}, dist2d={}, **kwargs):
        if kde_data is None:
            # If either data or a KDE was given on initialization, `self._kde` will be set
            kde_data = self._kde
            if kde_data is None:
                err = "kde or data required either during initialization or here!"
                raise ValueError(err)

        kde, data, weights = _parse_kde_data(kde_data, weights=weights)

        dist1d.setdefault('density', False)
        dist1d.setdefault('contour', False)
        dist1d.setdefault('carpet', False)
        dist1d.setdefault('hist', True)

        dist2d.setdefault('hist', True)
        dist2d.setdefault('contour', False)
        dist2d.setdefault('scatter', False)
        dist2d.setdefault('mask_dense', False)
        dist2d.setdefault('mask_below', False)

        return self.plot_data(data, dist1d=dist1d, dist2d=dist2d, **kwargs)

    def plot_data(self, data=None, edges=None, weights=None, color=None, cmap=None,
                  rotate=None, quantiles=None, limit=None, dist1d={}, dist2d={}):

        if data is None:
            # If either data or a KDE was given on initialization, `self._data` will be set
            data = self._data
            if data is None:
                err = "kde or data required either during initialization or here!"
                raise ValueError(err)

        kde, data, weights = _parse_kde_data(data, weights=weights)

        # ---- Sanitize
        if np.ndim(data) != 2:
            err = "`data` (shape: {}) must be 2D with shape (parameters, data-points)!".format(
                np.shape(data))
            raise ValueError(err)

        axes = self.axes
        size = np.shape(data)[0]
        shp = np.shape(axes)
        if (np.ndim(axes) != 2) or (shp[0] != shp[1]) or (shp[0] != size):
            raise ValueError("`axes` (shape: {}) does not match data dimension {}!".format(shp, size))

        # ---- Set parameters
        last = size - 1
        if rotate is None:
            rotate = self._rotate

        if limit is None:
            limit = self._limit_flag

        # Set default color or cmap as needed
        color, cmap = _parse_color_cmap(ax=axes[0][0], color=color, cmap=cmap)

        edges = utils.parse_edges(data, edges=edges)
        quantiles, _ = _default_quantiles(quantiles=quantiles)

        #
        # Draw / Plot Data
        # ----------------------------------

        # ---- Draw 1D Histograms & Carpets
        limits = [None] * size
        for jj, ax in enumerate(axes.diagonal()):
            rot = (rotate and (jj == last))
            self._data1d(
                ax, edges[jj], data[jj], weights=weights, quantiles=quantiles, rotate=rot,
                color=color, **dist1d
            )
            limits[jj] = utils.minmax(data[jj], stretch=self._LIMITS_STRETCH)

        # ---- Draw 2D Histograms and Contours
        for (ii, jj), ax in np.ndenumerate(axes):
            if jj >= ii:
                continue
            self._data2d(
                ax, [edges[jj], edges[ii]], [data[jj], data[ii]], weights=weights,
                color=color, cmap=cmap, quantiles=quantiles, **dist2d
            )

        if limit:
            for ii in range(self.size):
                self._limits[ii] = utils.minmax(limits[ii], prev=self._limits[ii])

            _set_corner_axes_extrema(self.axes, self._limits, self._rotate)

        return

    def _data1d(self, ax, edge, data, color=None, **dist1d):
        dist1d.setdefault('density', False)
        dist1d.setdefault('contour', False)
        dist1d.setdefault('carpet', True)
        dist1d.setdefault('hist', True)
        rv = _dist1d(data, ax=ax, edges=edge, color=color, **dist1d)
        return rv

    def _data2d(self, ax, edges, data, cmap=None, **dist2d):
        dist2d.setdefault('hist', True)
        dist2d.setdefault('contour', False)
        dist2d.setdefault('scatter', True)
        dist2d.setdefault('mask_dense', True)
        dist2d.setdefault('mask_below', True)
        rv = _dist2d(data, ax=ax, edges=edges, cmap=cmap, **dist2d)
        return rv

    def plot_kde(self, kde=None, weights=None, edges=None, rotate=None, quantiles=None, limit=None,
                 color=None, cmap=None, dist1d={}, dist2d={}):

        if kde is None:
            # If either data or a KDE was given on initialization, `self._kde` will be set
            kde = self._kde
            if kde is None:
                err = "kde or data required either during initialization or here!"
                raise ValueError(err)

        kde, data, weights = _parse_kde_data(kde, weights=weights)

        # ---- Sanitize
        axes = self.axes
        size = kde.ndim
        shp = np.shape(axes)
        if (shp[0] != shp[1]) or (shp[0] != size):
            err = "`axes` (shape: {}) does not match data dimension {}!".format(shp, size)
            raise ValueError(err)

        # ---- Set parameters
        last = size - 1
        if rotate is None:
            rotate = self._rotate

        if limit is None:
            limit = self._limit_flag

        edges = utils.parse_edges(kde.dataset, edges=edges)
        quantiles, _ = _default_quantiles(quantiles=quantiles)

        # Set default color or cmap as needed
        color, cmap = _parse_color_cmap(ax=axes[0][0], color=color, cmap=cmap)

        #
        # Draw / Plot KDE
        # ----------------------------------

        # ---- Draw 1D
        limits = [None] * size
        for jj, ax in enumerate(axes.diagonal()):
            rot = (rotate and (jj == last))
            self._kde1d(
                ax, edges[jj], kde, param=jj, quantiles=quantiles, rotate=rot,
                color=color, **dist1d
            )
            limits[jj] = utils.minmax(edges[jj], stretch=self._LIMITS_STRETCH)

        # ---- Draw 2D
        for (ii, jj), ax in np.ndenumerate(axes):
            if jj >= ii:
                continue
            self._kde2d(
                ax, [edges[jj], edges[ii]], kde, params=[jj, ii], quantiles=quantiles,
                color=color, cmap=cmap, **dist2d
            )

        if limit:
            for ii in range(self.size):
                self._limits[ii] = utils.minmax(limits[ii], prev=self._limits[ii])

            _set_corner_axes_extrema(self.axes, self._limits, self._rotate)

        return

    def _kde1d(self, ax, edge, kde, param, color=None, **dist1d):
        dist1d.setdefault('density', True)
        dist1d.setdefault('contour', True)
        dist1d.setdefault('carpet', False)
        dist1d.setdefault('hist', False)
        # This is identical to `kalepy.plot.dist1d` (just used for naming convenience)
        rv = _dist1d(kde, ax=ax, edges=edge, color=color, param=param, **dist1d)
        return rv

    def _kde2d(self, ax, edges, kde, params, cmap=None, **dist2d):
        dist2d.setdefault('hist', False)
        dist2d.setdefault('contour', True)
        dist2d.setdefault('scatter', False)
        dist2d.setdefault('mask_dense', True)
        dist2d.setdefault('mask_below', True)
        rv = _dist2d(kde, ax=ax, edges=edges, cmap=cmap, params=params, **dist2d)
        return rv

    '''
    def legend(self, handles=None, labels=None, index=None,
               loc=None, fancybox=False, borderaxespad=0, **kwargs):
        """
        """
        fig = self.fig

        # Set Bounding Box Location
        # ------------------------------------
        bbox = kwargs.pop('bbox', None)
        bbox = kwargs.pop('bbox_to_anchor', bbox)
        if bbox is None:
            if index is None:
                size = self.size
                if size in [2, 3]:
                    index = (0, -1)
                    loc = 'lower left'
                elif size == 1:
                    index = (0, 0)
                    loc = 'upper right'
                elif size % 2 == 0:
                    index = size // 2
                    index = (1, index)
                    loc = 'upper right'
                else:
                    index = (size // 2) + 1
                    loc = 'lower left'
                    index = (size-index-1, index)

            bbox = self.axes[index].get_position()
            bbox = (bbox.x0, bbox.y0)
            kwargs['bbox_to_anchor'] = bbox
            kwargs.setdefault('bbox_transform', fig.transFigure)

        # Set other defaults
        leg = fig.legend(handles, labels, fancybox=fancybox,
                         borderaxespad=borderaxespad, loc=loc, **kwargs)
        return leg
    '''


def _figax(size, grid=True, left=None, bottom=None, right=None, top=None, hspace=None, wspace=None,
           **kwfig):

    _def_figsize = np.clip(4 * size, 6, 20)
    _def_figsize = [_def_figsize for ii in range(2)]

    figsize = kwfig.pop('figsize', _def_figsize)
    if not np.iterable(figsize):
        figsize = [figsize, figsize]

    if hspace is None:
        hspace = 0.1
    if wspace is None:
        wspace = 0.1

    fig, axes = plt.subplots(figsize=figsize, squeeze=False, ncols=size, nrows=size, **kwfig)

    plt.subplots_adjust(
        left=left, bottom=bottom, right=right, top=top, hspace=hspace, wspace=wspace)
    if grid is True:
        grid = dict(alpha=0.2, color='0.5', lw=0.5)
    elif grid is False:
        grid = None

    for idx, ax in np.ndenumerate(axes):
        if grid is not None:
            ax.grid(True, **grid)

    return fig, axes


def corner(kde_data, labels=None, kwcorner={}, kwplot={}):
    corner = Corner(kde_data, labels=labels, **kwcorner)
    corner.plot(**kwplot)
    return corner


# ======  API Methods  ======
# ================================


def dist2d(kde_data, ax=None, edges=None, weights=None,
           params=[0, 1], probability=True, quantiles=None, color=None, cmap=None,
           median=True, scatter=True, contour=True, hist=True, mask_dense=None, mask_below=True):

    if ax is None:
        ax = plt.gca()

    if isinstance(kde_data, kale.KDE):
        if weights is not None:
            raise ValueError(f"`weights` of given `KDE` instance cannot be overridden!")
        kde = kde_data
        data = kde.dataset
        ndim = np.shape(data)[0]
        if ndim > 2:
            if len(params) != 2:
                raise ValueError(f"`dist2d` requires two chosen `params` (dimensions)!")
            data = np.vstack([data[ii] for ii in params])
        weights = None if kde._weights_uniform else kde.weights
    else:
        try:
            data = kde_data
            kde = KDE(data, weights=weights)
        except:
            logging.error(f"Failed to construct KDE from given data!")
            raise

    # Set default color or cmap as needed
    color, cmap = _parse_color_cmap(ax=ax, color=color, cmap=cmap)

    if mask_dense is None:
        mask_dense = (hist or scatter)

    edges = utils.parse_edges(data, edges=edges)
    hh, *_ = np.histogram2d(*data, bins=edges, weights=weights, density=True)

    _, levels, quantiles = _dfm_levels(hh, quantiles=quantiles)
    if mask_below is True:
        mask_below = levels.min()

    # Draw Scatter Points
    # -------------------------------
    if scatter:
        draw_scatter(ax, *data, color=color, zorder=5)

    # Draw Median Lines (Target Style)
    # -----------------------------------------
    if median:
        for dd, func in zip(data, [ax.axvline, ax.axhline]):
            if weights is None:
                med = np.median(dd)
            else:
                med = utils.quantiles(dd, percs=0.5, weights=weights)

            func(med, color=color, ls='-', alpha=0.25, lw=1.0, zorder=40, path_effects=_OUTLINE)

    # Draw 2D Histogram
    # -------------------------------
    # We may need edges and histogram for `mask_dense` later; store them from hist2d or contour2d
    _ee = None
    _hh = None

    if hist:
        _ee, _hh, _ = draw_hist2d(
            ax, edges, hh, mask_below=mask_below, cmap=cmap, zorder=10
        )
        # Convert from edges to centers, then to meshgrid (if we need it)
        if mask_dense:
            _ee = [utils.midpoints(ee, axis=-1) for ee in _ee]
            _ee = np.meshgrid(*_ee, indexing='ij')

    # Draw Contours
    # --------------------------------
    if contour:
        points, pdf = kde.density(params=params, probability=probability)
        _ee, _hh, _ = draw_contour2d(
            ax, points, pdf, quantiles=quantiles, smooth=2, upsample=2, pad=2,
            cmap=cmap.reversed(), zorder=20,
        )

    # Mask dense scatter-points
    if mask_dense:
        hh = _hh if (_hh is not None) else hh
        if _ee is not None:
            ee = _ee
        else:
            ee = [utils.midpoints(ee, axis=-1) for ee in edges]
            ee = np.meshgrid(*ee, indexing='ij')

        _, levels, quantiles = _dfm_levels(hh, quantiles=quantiles)
        span = [levels.min(), hh.max()]
        ax.contourf(*ee, hh, span, cmap=_MASK_CMAP, antialiased=True, zorder=9)

    return


def dist1d(kde_data, ax=None, edges=None, weights=None, probability=True, param=0, rotate=False,
           density=None, contour=False, hist=None, carpet=True, color=None, quantiles=None):

    if ax is None:
        ax = plt.gca()

    if isinstance(kde_data, kale.KDE):
        if weights is not None:
            raise ValueError("`weights` of given `KDE` instance cannot be overridden!")
        kde = kde_data
        data = kde.dataset
        if np.ndim(data) > 1:
            data = data[param]

        weights = None if kde._weights_uniform else kde.weights
    else:
        data = kde_data
        kde = None

    if color is None:
        color = _get_next_color(ax)

    # Default: plot KDE-density curve if KDE is given (data not given explicitly)
    if density is None:
        density = (kde is not None)

    # Default: plot histogram if data is given (KDE is *not* given)
    if hist is None:
        hist = (kde is None)

    # Draw PDF from KDE
    # -----------------
    if density:
        if kde is None:
            try:
                kde = KDE(data, weights=weights)
            except:
                logging.error(f"Failed to construct KDE from given data!")
                raise

        points, pdf = kde.density(probability=probability, params=param)
        if rotate:
            ax.plot(pdf, points, color=color, ls='--')
        else:
            ax.plot(points, pdf, color=color, ls='--')

    # Draw Histogram
    # --------------------------
    if hist:
        hist1d(data, ax=ax, edges=edges, weights=weights, color=color,
               density=True, probability=probability, joints=True, rotate=rotate)

    # Draw Contours and Median Line
    # ------------------------------------
    if contour:
        contour1d(data, ax=ax, color=color, quantiles=quantiles, rotate=rotate)

    # Draw Carpet Plot
    # ------------------------------------
    if carpet:
        _draw_carpet(data, weights=weights, ax=ax, color=color, rotate=rotate)

    return


def _get_def_sigmas(sigmas, contour=True, median=True):
    if (sigmas is False) or (contour is False):
        sigmas = []
    elif (sigmas is True) or (sigmas is None):
        sigmas = _DEF_SIGMAS

    if median:
        sigmas = np.append([0.0], sigmas)

    return sigmas


def _dist1d(*args, **kwargs):
    return dist1d(*args, **kwargs)


def _dist2d(*args, **kwargs):
    return dist2d(*args, **kwargs)


# ======  Drawing Methods  =====
# ==============================


def carpet(xx, weights=None, ax=None, ystd=None, yave=None, shift=0.0,
           fancy=False, random='normal', rotate=False, **kwargs):
    """Draw a carpet plot on the given axis in the 'fuzz' style.

    Arguments
    ---------
    xx : values to plot
    ax : matplotlib.axis.Axis
    kwargs : key-value pairs
        Passed to `matplotlib.axes.Axes.scatter()`

    """
    xx = np.asarray(xx)
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

    # Convert weights to a linear scaling for opacity and size
    if weights is None:
        ww = 1.0
    else:
        if utils.iqrange(weights, log=True) > 1:
            weights = np.log10(weights)
        ww = weights / np.median(weights)

    # General random y-values for the fuzz
    if random.lower() == 'normal':
        yy = np.random.normal(yave, ystd, size=xx.size)
    elif random.lower() == 'uniform':
        yy = np.random.uniform(yave-ystd, yave+ystd, size=xx.size)
    else:
        raise ValueError("Unrecognized `random` = '{}'!".format(random))

    # Choose an appropriate opacity
    alpha = kwargs.pop('alpha', None)
    if alpha is None:
        alpha = _scatter_alpha(xx)

    # Choose sizes proportional to their deviation (to make outliers more visible)
    size = 300 * ww / np.sqrt(xx.size)
    size = np.clip(size, 5, 100)

    if fancy:
        # Estimate the deviation of each point from the median
        dev = np.fabs(xx - np.median(xx)) / np.std(xx)
        # Extend deviation based on weighting
        dev *= ww
        # Rescale the y-values based on their deviation from median
        yy = (yy - yave) / (np.sqrt(dev) + 1) + yave
        # Choose sizes proportional to their deviation (to make outliers more visible)
        size = (size / 1.5) * (1.5 + dev)

    # Set parameters
    color = kwargs.pop('color', _get_next_color(ax))

    kwargs.setdefault('facecolor', color)
    kwargs.setdefault('edgecolor', 'none')
    kwargs.setdefault('marker', '.')
    kwargs.setdefault('alpha', alpha)
    kwargs.setdefault('s', size)

    extr = utils.minmax(yy)
    trans = [ax.transData, ax.transAxes]
    if shift is not None:
        yy += shift

    if rotate:
        temp = xx
        xx = yy
        yy = temp
        trans = trans[::-1]

    return ax.scatter(xx, yy, **kwargs), extr


def _set_corner_axes_extrema(axes, extrema, rotate, pdf=None):
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


def contour1d(data, ax=None, quantiles=[0.5, 0.9], weights=None, median=True, rotate=False,
              **kwargs):
    """Plot 1D Confidence intervals at the given quantiles.

    For each quantile `q`, a shaded range is plotted that includes a fration `q` of data values
    around the median.

    Parameters
    ----------


    Returns
    -------


    """

    if ax is None:
        ax = plt.gca()

    color = kwargs.pop('color', _get_next_color(ax))
    kwargs['facecolor'] = color
    kwargs['edgecolor'] = 'none'
    kwargs.setdefault('alpha', 0.1)

    # Calculate Cumulative Distribution Function
    if weights is None:
        data = np.sort(data)
        cdf = np.arange(data.size) / (data.size - 1)
    else:
        idx = np.argsort(data)
        data = data[idx]
        weights = weights[idx]
        cdf = np.cumsum(weights) / np.sum(weights)

    # Get both the lower (left) and upper (right) values
    quantiles = np.asarray(quantiles) / 2
    qnts = np.append(0.5 - quantiles, 0.5 + quantiles)
    # Reshape to (sigmas, 2)
    locs = np.interp(qnts, cdf, data).reshape(2, len(quantiles)).T

    if median:
        mm = np.interp(0.5, cdf, data)
        line_func = ax.axhline if rotate else ax.axvline
        line_func(mm, ls='--', color=color, alpha=0.25)

    for lo, hi in locs:
        span_func = ax.axhspan if rotate else ax.axvspan
        handle = span_func(lo, hi, **kwargs)

    return handle


def hist1d(data, edges=None, ax=None, weights=None, density=False, probability=False, **kwargs):
    if ax is None:
        ax = plt.gca()

    hist, edges = utils.histogram(
        data, bins=edges, weights=weights, density=density, probability=probability
    )

    return hist, edges, draw_hist1d(ax, edges, hist, **kwargs)


def draw_hist1d(ax, edges, hist, renormalize=False, nonzero=False, positive=False,
                joints=True, rotate=False, **kwargs):

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
    if renormalize:
        yval = yval / yval[np.isfinite(yval)].max()

    line, = ax.plot(xval, yval, **kwargs)

    return line


def hist2d(data, edges=None, ax=None, weights=None, mask_below=False, **kw):
    if ax is None:
        ax = plt.gca()

    edges = utils.parse_edges(data, edges=edges)
    hist, *_ = np.histogram2d(*data, bins=edges, weights=weights, density=True)
    if mask_below is True:
        mask_below = 0.9 / len(data[0])

    return draw_hist2d(ax, edges, hist, mask_below=mask_below, **kw)


def draw_hist2d(ax, edges, hist, mask_below=None, **kwargs):
    kwargs.setdefault('shading', 'auto')
    # kwargs.setdefault('edgecolors', 'face')
    kwargs.setdefault('edgecolors', [1.0, 1.0, 1.0, 0.0])
    kwargs.setdefault('linewidth', 0.01)
    if mask_below not in [False, None]:
        hist = np.ma.masked_less_equal(hist, mask_below)
    return edges, hist, ax.pcolormesh(*edges, hist.T, **kwargs)


def contour2d(data, edges=None, ax=None, weights=None, **kw):

    if ax is None:
        ax = plt.gca()

    edges = utils.parse_edges(data, edges=edges)
    hist, *_ = np.histogram2d(*data, bins=edges, weights=weights, density=True)
    return draw_contour2d(ax, edges, hist, **kw)


def draw_contour2d(ax, edges, hist, quantiles=None, smooth=None, upsample=None, pad=True,
                   outline=True, reverse=False, **kwargs):

    _PAD = 2
    LW = 1.5

    # ---- (Pre-)Process histogram and bin edges

    # Pad Histogram for Smoother Contour Edges
    if pad not in [False, None]:
        if pad is True:
            pad = _PAD
        edges, hist = _pad_hist(edges, hist, pad)

    # Convert from bin edges to centers as needed
    xx, yy = _match_edges_to_hist(edges, hist)

    # Construct grid from center values
    xx, yy = np.meshgrid(xx, yy, indexing='ij')

    if (upsample not in [None, False]):
        if upsample is True:
            upsample = 2
        xx = sp.ndimage.zoom(xx, upsample)
        yy = sp.ndimage.zoom(yy, upsample)
        hist = sp.ndimage.zoom(hist, upsample)
    if (smooth is not None):
        if upsample is not None:
            smooth *= upsample
        hist = sp.ndimage.filters.gaussian_filter(hist, smooth)

    edges = [xx, yy]

    # ---- Setup parameters
    _, levels, quantiles = _dfm_levels(hist, quantiles=quantiles)
    alpha = kwargs.setdefault('alpha', 0.8)
    lw = kwargs.pop('linewidths', kwargs.pop('lw', LW))
    kwargs.setdefault('linestyles', kwargs.pop('ls', '-'))
    kwargs.setdefault('zorder', 10)

    # ---- Draw contours
    cont = ax.contour(xx, yy, hist, levels=levels, linewidths=lw, **kwargs)

    # ---- Add Outline path effect to contours
    if (outline is True):
        if (not np.isscalar(lw)) and (len(cont.collections) == len(lw)):
            for line, _lw in zip(cont.collections, lw):
                outline = _get_outline_effects(2*_lw, alpha=1 - np.sqrt(1 - alpha))
                plt.setp(line, path_effects=outline)
        elif np.isscalar(lw):
            outline = _get_outline_effects(2*lw, alpha=1 - np.sqrt(1 - alpha))
            plt.setp(cont.collections, path_effects=outline)
        else:
            err = (
                f"kalepy.plot.draw_contour2d() :: ",
                f"Disregarding unexpected `lw`/`linewidths` argument: '{lw}'"
            )
            logging.warning(err)
            outline = _get_outline_effects(2*LW, alpha=1 - np.sqrt(1 - alpha))
            plt.setp(cont.collections, path_effects=outline)

    elif (outline is not False):
        raise ValueError("`outline` must be either 'True' or 'False'!")

    return edges, hist, cont


def draw_scatter(ax, xx, yy, alpha=None, s=4, **kwargs):
    # color = kwargs.pop('color', kwargs.pop('c', None))
    # fc = kwargs.pop('facecolor', kwargs.pop('fc', None))
    # if fc is None:
    #     fc = ax._get_lines.get_next_color()
    # kwargs.setdefault('facecolor', color)
    # kwargs.setdefault('edgecolor', 'none')
    if alpha is None:
        alpha = _scatter_alpha(xx)
    kwargs.setdefault('alpha', alpha)
    kwargs.setdefault('s', s)
    return ax.scatter(xx, yy, **kwargs)


# ====  Utility Methods  ====
# ===========================


'''
def nbshow():
    return utils.run_if_notebook(plt.show, otherwise=lambda: plt.close('all'))
'''


def _match_edges_to_hist(edges, hist):
    esh = tuple([len(ee) for ee in edges])
    esh_p1 = tuple([len(ee) - 1 for ee in edges])
    # If the shape of edges matches the hist, then we're good
    if np.shape(hist) == esh:
        pass
    # If `edges` have one more element each, then convert from edges to centers
    elif np.shape(hist) == esh_p1:
        edges = [utils.midpoints(ee, axis=-1) for ee in edges]
    else:
        err = (
            "Shape of hist [{}=(X,Y)] ".format(np.shape(hist)),
            "does not match edges ({})!".format(esh)
        )
        raise ValueError(err)

    return edges


def _parse_kde_data(kde_data, weights=None):
    if isinstance(kde_data, kale.KDE):
        if weights is not None:
            raise ValueError("`weights` must be used from given `KDE` instance!")
        kde = kde_data
        data = kde.dataset
        weights = None if kde._weights_uniform else kde.weights
    # If the raw data is given, construct a KDE from it
    else:
        try:
            data = kde_data
            kde = KDE(kde_data, weights=weights)
        except:
            err = "Failed to construct `KDE` instance from given data!"
            logging.error(err)
            raise

    return kde, data, weights


def _parse_color_cmap(ax=None, color=None, cmap=None):
    if (color is None) and (cmap is None):
        if ax is None:
            ax = plt.gca()
        color = _get_next_color(ax)
        cmap = _color_to_cmap(color)
    elif (color is None):
        cmap = plt.get_cmap(cmap)
        color = cmap(0.5)
    else:
        cmap = _color_to_cmap(color)

    return color, cmap


'''
def _get_smap(args=[0.0, 1.0], cmap=None, log=False, norm=None, under='w', over='w'):
    args = np.asarray(args)

    if not isinstance(cmap, mpl.colors.Colormap):
        if cmap is None:
            cmap = 'viridis'
        if isinstance(cmap, six.string_types):
            cmap = plt.get_cmap(cmap)

    import copy
    cmap = copy.copy(cmap)
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
    uniform = False
    if isinstance(smap, mpl.cm.ScalarMappable):
        # If `smap` was created with `kalepy.plot._get_smap()` than it should have this attribute
        try:
            smap_is_log = smap._log
        # Otherwise assume it's linear
        # NOTE: this might be wrong.  Better way to check?
        except AttributeError:
            smap_is_log = False

        return smap, smap_is_log, uniform

    if smap is None:
        smap = {}

    if not isinstance(smap, dict):
        raise ValueError("`smap` must either be a dict or ScalarMappable!")

    for kk, vv in defaults.items():
        smap.setdefault(kk, vv)

    smap_is_log = smap['log']
    if cmap is None:
        cmap = _COLOR_CMAP.get(color[0].lower(), None)
        if cmap is None:
            cmap = 'Greys'
            uniform = True

    smap.setdefault('cmap', cmap)

    return smap, smap_is_log, uniform
'''


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


def _dfm_levels(data, quantiles=None, sigmas=None):
    quantiles, sigmas = _default_quantiles(quantiles=quantiles, sigmas=sigmas)

    # Compute the density levels.
    data = np.asarray(data).flatten()
    inds = np.argsort(data)[::-1]
    data = data[inds]
    sm = np.cumsum(data)
    sm /= sm[-1]
    levels = np.empty(len(quantiles))
    for i, v0 in enumerate(quantiles):
        try:
            levels[i] = data[sm <= v0][-1]
        except:
            levels[i] = data[0]

    levels.sort()

    # -- Remove Bad Levels
    # bad = (np.diff(levels) == 0)
    # bad = np.pad(bad, [1, 0], constant_values=False)
    # levels = np.delete(levels, np.where(bad)[0])
    # if np.any(bad):
    #     _levels = quantiles
    #     quantiles = np.array(quantiles)[~bad]
    #     logging.warning("Removed bad levels: '{}' ==> '{}'".format(_levels, quantiles))

    return sigmas, levels, quantiles


def _default_quantiles(quantiles=None, sigmas=None):
    if quantiles is None:
        if sigmas is None:
            sigmas = _DEF_SIGMAS
        # Convert from standard-deviations to CDF values
        quantiles = 1.0 - np.exp(-0.5 * np.square(sigmas))
    elif sigmas is None:
        sigmas = np.sqrt(-2.0 * np.log(1.0 - quantiles))

    return quantiles, sigmas


def _pad_hist(edges, hist, pad):
    hh = np.pad(hist, pad, mode='constant', constant_values=hist.min())
    tf = np.arange(1, pad+1)  # [+1, +2]
    tr = - tf[::-1]    # [-2, -1]
    edges = [
        [ee[0] + tr * np.diff(ee[:2]), ee, ee[-1] + tf * np.diff(ee[-2:])]
        for ee in edges
    ]
    edges = [np.concatenate(ee) for ee in edges]
    return edges, hh


def _scatter_alpha(xx, norm=10.0):
    alpha = norm / np.sqrt(len(xx))
    # NOTE: array values dont work for alpha parameters (added to `colors`)
    # if alpha is None:
    #     aa = 10 / np.sqrt(xx.size)
    #     alpha = aa
    #     # alpha = aa * ww
    #     # alpha = np.clip(alpha, aa/10, aa*10)
    #     # alpha = np.clip(alpha, 1e-4, 1e-1)

    return alpha


def _draw_carpet(*args, **kwargs):
    return carpet(*args, **kwargs)


def _get_outline_effects(lw=2.0, fg='0.75', alpha=0.8):
    outline = ([
        mpl.patheffects.Stroke(linewidth=lw, foreground=fg, alpha=alpha),
        mpl.patheffects.Normal()
    ])
    return outline


def _get_next_color(ax):
    return ax._get_lines.get_next_color()


def _color_to_cmap(col, pow=0.333, sat=0.5, val=0.5):
    rgb = mpl.colors.to_rgb(col)

    # ---- Increase 'value' and 'saturation' of color
    # Convert to HSV
    hsv = mpl.colors.rgb_to_hsv(rgb)
    # Increase '[v]alue'
    par = 2
    hsv[par] = np.interp(val, [0.0, 1.0], [hsv[par], 1.0])
    # Increase '[s]aturation'
    par = 1
    hsv[par] = np.interp(sat, [0.0, 1.0], [hsv[par], 1.0])
    # Convert back to RGB
    rgb = mpl.colors.hsv_to_rgb(hsv)

    # ---- Create edge colors near-white and near-black
    # find distance to white and black
    dw = np.linalg.norm(np.diff(np.vstack([rgb, np.ones_like(rgb)]), axis=0)) / np.sqrt(3)
    db = np.linalg.norm(np.diff(np.vstack([rgb, np.zeros_like(rgb)]), axis=0)) / np.sqrt(3)
    # shift edges towards white and black proportionally to distance
    lo = [np.interp(dw**pow, [0.0, 1.0], [ll, 1.0]) for ll in rgb]
    hi = [np.interp(db**pow, [0.0, 1.0], [ll, 0.0]) for ll in rgb]

    # ---- Construct colormap
    my_colors = [lo, rgb, hi]
    cmap = mpl.colors.LinearSegmentedColormap.from_list("mycmap", my_colors)
    return cmap


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
