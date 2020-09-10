#!/usr/bin/env python
# encoding: utf-8
from __future__ import division, absolute_import, print_function
"""
Timeline.py

Created by Szymon Łęski on 2013-02-19.

"""
import os
import numpy as np
import sys
import time
import calendar
import matplotlib as mpl
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.ticker
import matplotlib.dates as mpd
import matplotlib.pyplot as plt
from pyEcoHAB import utility_functions as uf


if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, NoSectionError
else:
    from configparser import RawConfigParser, NoSectionError


class Timeline(RawConfigParser, matplotlib.ticker.Formatter):
    """
    Read in the temporal config of the experiment (timeline of the experiment).

    As a subclass of :py:class:`matplotlib.ticker.Formatter` the class is also
    a time axis formatter in :py:mod:`matplotlib.dates` coordinates.

    The temporal config file is a constrained INI format. Each section defines
    a phase of the experiment and both the section and the phase should have
    the same name. For each section a startdate (in a DD.MM.YYYY format),
    a startime (in a HH:MM format), an enddate (in a DD.MM.YYYY format), and
    an endtime (in a HH:MM format) needs to be specified.
    """
    def __init__(self, path, fname=None):
        RawConfigParser.__init__(self)
        self.path = path
        if fname is None:
            if os.path.isfile(path):
                self.path = path
            elif os.path.isfile(os.path.join(path, 'config.txt')):
                fname = 'config.txt'
                self.path = os.path.join(path, fname)
            else:
                fname = filter(lambda x: x.startswith('config')
                               and x.endswith('.txt'),
                               os.listdir(path))[0]
                self.path = os.path.join(path, fname)
        else:
            fname = fname
            self.path = os.path.join(path, fname)
        self.read(self.path)

    def get_time_from_epoch(self, sec):
        """Convert start and end time and date read from section sec
        (might be a list) of the config file to a tuple of times from epoch."""
        if type(sec) == list:
            starts = []
            ends = []
            for ss in sec:
                st, et = self.get_time_from_epoch(ss)
                starts.append(st)
                ends.append(et)
            return min(starts), max(ends)
        else:
            tstr1 = self.get(sec, 'startdate') + self.get(sec, 'starttime')
            tstr2 = self.get(sec, 'enddate') + self.get(sec, 'endtime')
            t1 = uf.to_struck(tstr1, self.path)
            t2 = uf.to_struck(tstr2, self.path)
            return calendar.timegm(t1), calendar.timegm(t2)

    def __call__(self, x, pos=0):
        x = mpd.num2epoch(x)
        for sec in self.sections():
            t1, t2 = self.get_time_from_epoch(sec)
            if t1 <= x and x < t2:
                return sec
        return 'Unknown'

    def mark(self, sec, ax=None):
        """Mark given phases on the plot"""
        if ax is None:
            ax = plt.gca()
        ylims = ax.get_ylim()
        for tt in self.get_time_from_epoch(sec):
            ax.plot([mpd.epoch2num(tt), ] * 2, ylims, 'k:')
        plt.draw()

    def plot_nights(self, sections, ax=None):
        """Plot night from sections"""
        if ax is None:
            ax = plt.gca()
        ylims = ax.get_ylim()
        xlims = ax.get_xlim()
        if type(sections) == str:
            sections = [sections]
        for sec in sections:
            t1, t2 = self.get_time_from_epoch(sec)
            plt.bar(mpd.epoch2num(t1), ylims[1] - ylims[0],
                    width=mpd.epoch2num(t2) - mpd.epoch2num(t1),
                    bottom=ylims[0], color='0.8', alpha=0.5, zorder=-10)
        ax.set_xlim(xlims)
        plt.draw()

    def plot_sections(self):
        """Diagnostic plot of sections defined in the config file."""
        figg = plt.figure()
        for idx, sec in enumerate(self.sections()):
            t1, t2 = mpd.epoch2num(self.get_time_from_epoch(sec))  # cf2time(cf, sec)
            plt.plot([t1, t2], [idx, idx], 'ko-')
            plt.plot([t2], [idx], 'bo')
            plt.text(t2 + 0.5, idx, sec)
        ax = plt.gca()
        ax.xaxis.set_major_locator(mpd.HourLocator(np.array([00]),
                                                   tz=tzone))
        ax.xaxis.set_major_formatter(mpd.DateFormatter('%d.%m %H:%M',
                                                       tz=tzone))
        ax.autoscale_view()
        ax.get_figure().autofmt_xdate()
        plt.title(self.path)
        plt.draw()
