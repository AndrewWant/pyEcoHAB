# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import
import os
import numpy as np
import matplotlib.pyplot as plt
from . import utility_functions as utils
from .plotting_functions import single_in_cohort_soc_plot, make_RasterPlot
from .write_to_file import write_binned_data, write_csv_rasters, write_csv_alone

def prepare_mice_intervals(data_mice, address):
    ints = {}
    for mouse in data_mice.keys():
        ints[mouse] = utils.intervals2lists(data_mice[mouse], address)
    return ints


def check_interval(intervals_mouse1, intervals_mouse2, idx, new_idx):
    original_s, original_e = intervals_mouse1[0][idx], intervals_mouse1[1][idx]
    other_s, other_e = intervals_mouse2[0][new_idx], intervals_mouse2[1][new_idx]
    if  other_s > original_e:
        return False
    if original_s >  other_s and original_e > other_e:
        intervals_mouse1[0][idx] = other_e
        return False
    if original_s < other_s and original_e < other_e:
        intervals_mouse1[1][idx] = other_s
        return False
    if original_s >= other_s and original_e <= other_e:
        # delete mouse1 interval
        intervals_mouse1[0].remove(original_s)
        intervals_mouse1[1].remove(original_e)
        return True
    #  cut the original interval in half
    intervals_mouse1[1][idx] = other_s
    if other_e < original_e:
        intervals_mouse1[0].insert(idx + 1, other_e)
        intervals_mouse1[1].insert(idx + 1, original_e)
    if other_s == original_s:
        intervals_mouse1[0].remove(original_s)
        intervals_mouse1[1].remove(other_s)
        return True
    return False

def remove_overlapping_intervals(intervals_mouse1, intervals_mouse2):
    """"
    Eliminate all the intervals, when mouse 1 is with mouse 2
    """
    if len(intervals_mouse1[0]) == 0:
        return
    if len(intervals_mouse2[0]) == 0:
        return
    i = 0
    while i < len(intervals_mouse1[0]):
        new_idx = utils.get_idx_pre(intervals_mouse1[0][i], intervals_mouse2[0])
        if new_idx is None:
            new_idx = utils.get_idx_pre(intervals_mouse1[1][i], intervals_mouse2[0])
            if new_idx is None:
                i = i + 1
                continue
        if intervals_mouse2[1][new_idx] < intervals_mouse1[0][i]:
            new_idx += 1
        if new_idx  >= len(intervals_mouse2[0]):
            break
        removed = check_interval(intervals_mouse1, intervals_mouse2, i, new_idx)
        if not removed:
            i = i + 1


def mouse_alone(data_mice, address):
    ints = prepare_mice_intervals(data_mice, address)
    new_intervals = {}
    result = {}
    for mouse in ints.keys():
        mouse_ints = []
        mouse_ints.append(ints[mouse][0][:])
        mouse_ints.append(ints[mouse][1][:])
        for other_mouse in ints.keys():
            if mouse != other_mouse:
                remove_overlapping_intervals(mouse_ints, ints[other_mouse])
        new_intervals[mouse] = mouse_ints
    for mouse in new_intervals:
        result[mouse] = utils.get_duration(new_intervals[mouse][0], new_intervals[mouse][1])
    return result


def mice_overlap(ints1, ints2):
    """Return time overlap of mice m1 and m2 in cage <address>."""
    total_overlap = 0
    for int1 in ints1:
        for int2 in ints2:
            total_overlap += utils.interval_overlap(int1, int2)
    return total_overlap


def time_fraction_together_one_cage(ints1, ints2, total_time):
    assert total_time > 0
    return mice_overlap(ints1, ints2)/total_time


def expected_time_fraction_together_one_cage(ints1, ints2, total_time):
    durations_m1 = utils.calculate_total_duration(ints1)
    durations_m2 = utils.calculate_total_duration(ints2)
    return durations_m1/total_time*durations_m2/total_time


def mice_together(data_mice, m1, m2, total_time):
    """Return the time spent together by two mice and expected time 
    assuming independence."""
    time_together = 0
    exp_time_together = 0
    for address in [1, 2, 3, 4]:
        ints1 = utils.get_intervals(data_mice[m1], address)
        ints2 = utils.get_intervals(data_mice[m2], address)
        time_together += time_fraction_together_one_cage(ints1,
                                                         ints2,
                                                         total_time)
        exp_time_together += expected_time_fraction_together_one_cage(ints1,
                                                                      ints2,
                                                                      total_time)
    return time_together, exp_time_together



def get_solitude(ehs, cf, res_dir=None, prefix=None):
    if prefix is None:
        prefix = ehs.prefix
    if res_dir is None:
        res_dir = ehs.res_dir
    phases = utils.filter_dark(cf.sections())
    mice = ehs.mice
    output = np.zeros((4, len(mice), len(phases)+1))
    for phase, sec in enumerate(phases):
        times = cf.gettime(sec)
        data = utils.prepare_data(ehs, mice, times)
        for i in range(1, 5):
            alone = mouse_alone(data, i)
            for j, mouse in enumerate(mice):
                output[i-1, j, phase] = alone[mouse]
    phases.append('ALL DARK')
    output[:,:,-1] = output[:,:,:-1].sum(axis=2)  # last column -- sum of activity in all dark phases
    write_csv_alone(output, phases, mice, res_dir, prefix)


def single_phase_results(data, mice, total_time):
    res = np.zeros((len(mice), len(mice)))
    res_exp = np.zeros((len(mice), len(mice)))
    for ii, mouse1 in enumerate(mice):
        for jj in range(ii + 1, len(mice)):
            mouse2 = mice[jj]
            res[ii, jj], res_exp[ii, jj] = mice_together(data,
                                                         mouse1,
                                                         mouse2,
                                                         total_time)
    return res, res_exp


def get_dark_light_data(phase, cf, ehs, mice):

    if phase == "dark" or phase == "DARK" or phase == "Dark":
        phases = utils.filter_dark(cf.sections())
    elif phase == "light" or phase == "LIGHT" or phase == "Light":

        phases = utils.filter_light(cf.sections())
    out_phases = [phase]
    data = {mouse:[] for mouse in mice}
    total_time = 0
    for i, ph in enumerate(phases):
        time = cf.gettime(ph)
        out = utils.prepare_data(ehs, mice, time)
        for mouse in mice:
            data[mouse].extend(out[mouse])
        total_time += (time[1] - time[0])
    return [out_phases], [total_time], [data]

def prepare_fnames_and_totals(ehs, cf, prefix, bins, mice):
    if bins in ["ALL", "all", "All"]:
        phases = [["ALL"]]
        time = cf.gettime("ALL")
        total_time = [[time[1] - time[0]]]
        phase_name = "ALL"
        data = [[utils.prepare_data(ehs, mice, time)]]
        shape = (1, 1, len(mice), len(mice))
        bin_labels = [time[1] - time[0]]
    elif bins in ['dark', "DARK", "Dark", "light", "LIGHT", "Light"]:
        phases, total_time, data = get_dark_light_data(which_phases, cf, ehs)
        phase_name = "_ALL_%s" % bins
        shape = (1, 1, len(mice), len(mice))
        bin_labels = total_time[0]
    elif isinstance(bins, int) or isintance(bins, float):
        phases = []
        data = []
        total_time = []
        phase_name = "whole_bins_%4.2f_h" % bins
        all_phases = utils.filter_dark(cf.sections())
        bin_labels = utils.get_times(binsize)
        for i, phase in enumerate(all_phases):
            t_start, t_end = cf.gettime(phase)
            phases.append("%s_%5.2fh" % (phase, bins))
            total_time.append([])
            data.append([])
            while t_start < t_end:
                time = [t_start, t_start + bins]
                data[i].append(utils.prepare_data(ehs, mice, time))
                total_time[i].append(time[1] - time[0])
                t_start += bins
        shape = (len(all_phases), len(bin_labels), len(mouse), len(mouse))

   
    return phases, total_time, data, shape, bin_labels


def get_incohort_sociability(ehs, cf, res_dir=None,
                             prefix=None, remove_mouse=None,
                             bins=12*3600):
    if prefix is None:
        prefix = ehs.prefix
    if res_dir is None:
        res_dir = ehs.res_dir
    mice = utils.get_mice(ehs.mice, remove_mouse)
    add_info_mice = utils.add_info_mice_filename(remove_mouse)

   
    fname_measured_prefix = "incohort_sociability_measured_time_%s_%s" % (prefix, add_info_mice)
    fname_expected_prefix = "incohort_sociability_expected_time_%s_%s" % (prefix, add_info_mice)
    fname_excess_prefix = "incohort_sociability_excess_time_%s_%s" % (prefix, add_info_mice)
    phases, time, data, shape, bin_labels = prepare_fnames_and_totals(ehs,
                                                                      cf,
                                                                      prefix,
                                                                      bins,
                                                                      mice)

    if time == 0:
        return
    full_results = np.zeros(shape)
    full_results_exp = np.zeros(shape)
    for idx_phase, phase in enumerate(phases):
        phase = phase.replace(' ', '_')
        for i in enumerate(bin_labels):
            full_results[idx_phase, i], full_results_exp[idx_phase, i] = single_phase_results(data[idx][i], mice, time[idx][i])
            
        write_binned_data(full_results[idx_phase],
                          'incohort_sociability_measured_time',
                          mice, bin_labels, phase, res_dir, 
                          'incohort_sociability/histograms',
                          prefix, additional_info=add_info_mice)
        write_binned_data(full_results_exp[idx_phase],
                          'incohort_sociability_expected_time',
                          mice, bin_labels, phase, res_dir, 
                          'incohort_sociability/histograms',
                          prefix, additional_info=add_info_mice)
        write_binned_data(full_results[idx_phase]-full_results_exp[idx_phase],
                          'incohort_sociability_excess_time',
                          mice, bin_labels, phase, res_dir, 
                          'incohort_sociability/histograms',
                          prefix, additional_info=add_info_mice)
        if int(bins) == 12*3600:
            single_in_cohort_soc_plot(full_results[idx_phase, 0],
                                      full_results_exp[idx_phase, 0],
                                      mice,
                                      phase,
                                      fname,
                                      res_dir,
                                      'incohort_sociability/histograms',
                                      prefix+add_info_mice)
        
        fname_measured = "%s_%s.csv" % (fname_measured_prefix, phase)
        fname_excess = "%s_%s.csv" % (fname_excess_prefix, phase)
        fname_expected = "%s_%s.csv" % (fname_expected_prefix, phase)
        write_csv_rasters(mice,
                          bin_labels,
                          full_results[idx_phase],
                          res_dir,
                          'incohort_sociability/raster_plots',
                          fname_measured)
        write_csv_rasters(mice,
                          bin_labels,
                          full_results_exp[idx_phase],
                          res_dir,
                          'incohort_sociability/raster_plots',
                          fname_expected)
        write_csv_rasters(mice,
                          bin_labels,
                          full_results[idx_phase]-full_results_exp[idx_phase],
                          res_dir,
                          'incohort_sociability/raster_plots',
                          fname_excess)
        make_RasterPlot(res_dir,
                        'incohort_sociability/raster_plots',
                        full_results[idx_phase],
                        bin_labels,
                        fname_measured,
                        mice, vmin=0, vmax=1,
                        title='% time together')
        make_RasterPlot(res_dir,
                        'incohort_sociability/raster_plots',
                        full_results_exp[idx_phase],
                        bin_labels,
                        fname_expected,
                        mice,
                        title='% time together')
        make_RasterPlot(res_dir,
                        'incohort_sociability/raster_plots',
                        full_results[idx_phase]-full_results_exp[idx_phase],
                        bin_labels,
                        fname_excess,
                        mice,
                        title='% time together')
