from math import sqrt, floor
from statistics import median

## This method implements the median RMS as defined in the Turnquist-Namer paper dealing with track correlation for fibre tracking.
# The paper can be accessed here: https://www.sciencedirect.com/science/article/abs/pii/S0165027016000054
# @param sweeps The list of sweeps in the recording that should be analyzed
# @param center_sweep_idx Index of the sweep around which we extract the sweeps according to radius, also called k in the paper
# @param latency_shift Slope along which the RMS is calculated. Also called m in the paper, so we have the actual latency as t + r * m, where t is the latency and -R <= r <= R is the index in the R-environment around k. In s/sweep!
# @param latency Latency behind the eletrical stimulus in each sweep around which we look for the median RMS, called t in the paper. In s!
# @param radius Radius or number of sweeps which we want to consider during search of the median RMS, labelled r in the paper
# @param window_size Size of the window around the (computed) latency which is used to calculate the RMS. Given in s!
# @param sampling_rate Sampling rate of the recording, required for array access
def median_RMS(sweeps, center_sweep_idx, latency_shift, latency, radius, window_size = 0.0015, sampling_rate = 20000):
	
	# check if the input is valid
	if center_sweep_idx - radius < 0 or center_sweep_idx + radius > len(sweeps) - 1:
		raise ValueError("The radius for median RMS calculation exceeds either the first or the last position in the sweep array. Reduce radius or increase the center sweep index to resolve this issue.")
	
	# restrict only to the sweeps which lie within the radius around the "center sweep"
	sweeps = sweeps[center_sweep_idx - radius : center_sweep_idx + radius]
	rms = []
	
	for r, sweep in zip(range(-radius, radius), sweeps):
		t = latency + r * latency_shift
		sig = sweep.raw_signal[floor((t - window_size) * sampling_rate) : floor((t + window_size) * sampling_rate)]
		rms.append(root_mean_square_power(sig))
	
	return median(rms)

## This function calculates the root mean square for a time series of signal values. See also: https://en.wikipedia.org/wiki/Root_mean_square
# @param signal The time series of input signal values
def root_mean_square_power(signal):
	n = len(signal)
	squared_signal = [x * x for x in signal]
	
	return sqrt(sum(squared_signal) / n)