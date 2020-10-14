import numpy as np
import random as rnd

from metrics import median_RMS

def track_correlation(sweeps, center_sweep_idx, latency, radius = 2, window_size = 0.0015):
	
	# build a linear space of float values between the minimum and maximum latency shift, i.e. the slope of the linear approximation of the track
	shifts = np.linspace(start = -0.01, stop = 0.01, num = 21)
	rms = [median_RMS(sweeps, center_sweep_idx = 7, latency_shift = shift, latency = latency, radius = radius, window_size = window_size) for shift in shifts]
	
	# get the maximum shift, i.e. the optimal slope
	max_shift = shifts[np.argmax(rms)]
	# return it together with the track correlation
	return max(rms), max_shift

## This function returns an estimate of the track correlation noise.
# It samples a number of random points from the sweeps (we need to control for bias here!) and calculates the track correlation for each of these points.
def get_tc_noise_estimate(sweeps, num_samples = 1000):
	
	# get the maximum and minimum time from all the sweeps in the recording
	t_min = min([sweep.t_start for sweep in sweeps])
	t_max = max([sweep.t_end for sweep in sweeps])
	
	# get num_samples random timestamps from where to sample the TC
	# sort them in ascending order s.t. we don't have to iterate over the sweeps multiple times
	sample_times = [rnd.uniform(t_min, t_max) for i in range(num_samples)]
	sample_times = sorted(sample_times)
	
	# start with the first sweep
	sweep_idx = 0
	tcs = []
	for t in sample_times:
		# iterate through the sweeps until we found the one in which the sampled time t lies
		while sweeps[sweep_idx].t_end < t:
			sweep_idx += 1
			
		latency = t - sweeps[sweep_idx].t_start 
		tcs.append(track_correlation(sweeps, center_sweep_idx = sweep_idx, latency = latency))
	
	return tcs