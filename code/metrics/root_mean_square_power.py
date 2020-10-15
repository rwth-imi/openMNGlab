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
	rms = []
	
	for r, (sweep_idx, sweep) in zip(range(-radius, radius + 1), enumerate(sweeps[center_sweep_idx - radius : center_sweep_idx + radius])):
		# calculate the latency shift in each direction
		t = latency + r * latency_shift
		# calculate the window borders
		t_min_idx = max(floor((t - window_size) * sampling_rate), 0)
		t_max_idx = max(min(floor((t + window_size) * sampling_rate), len(sweep.raw_signal)), 0)
		
		# extract only this part of the sweep's signal
		sig = sweep.raw_signal[t_min_idx : t_max_idx]
		
		# TODO: theoretically, we could "wrap around" the end of beginning and end of the sweeps here.
		# But I'd argue that if the track crosses the border between the sweeps, i.e., the electrical stimulus itself, it might not be a track in the first place
		# Therefore, what we do for now is that we restrict t_min and t_max to [0, len(sweep)] and see what happens.
		'''
		# now, we need to collect the signal values for which we calculate the RMS.
		# if the left border of the window is before the onset of the sweep, we'll need to collect some signal values from the end of the previous sweep as well.
		sig = []
		if t_min < 0:
			# check if this wasn't already the first sweep. If so, we just don't add anything to the signal from the previous sweep.
			if not sweep_idx == 0:
				prev_sweep = sweeps[sweep_idx - 1]
								
				sig.extend(prev_sweep.raw_signal[floor((prev_sweep.duration - t_min) * sampling_rate) : max(floor((prev_sweep.duration - t_max) * sampling_rate), len(prev_sweep.raw_signal))])
				
				
			else:
				# there is no previous sweep, so just add 0
				sig.append(0)
				
				
			# then, we can add the rest of the window which lies in the current sweep
			sig.extend(sweep.raw_signal[0 : floor((
		
		# TODO: Redo this completely
		# reconstruct the signal that we need to analyze with the window. If the window exceeds the left or right border of a sweep, we'll have to "wrap around"
		sig = []
		if t_min < 0:
			sig = sweeps[sweep_idx - 1].raw_signal[floor(t_min * sampling_rate) : -1]
		sig.append(sweep.raw_signal[max(0, t_min) : min(t_max, len(sweep.raw_signal))])
		if t_max > sweep.duration:
			sig.append(sweeps[sweep_idx + 1].raw_signal[0 : floor((t_max - sweep.duration) * sampling_rate)])
		'''
		
		# add the calculated RMS to the list of RMSes in the R-environment
		rms.append(root_mean_square_power(sig))
	
	return median(rms)

## This function calculates the root mean square for a time series of signal values. See also: https://en.wikipedia.org/wiki/Root_mean_square
# @param signal The time series of input signal values
def root_mean_square_power(signal):
	# If the signal is empty, then the energy is just returned as 0.
	# TODO: consider throwing an exception in this case.
	if len(signal) == 0:
		return 0
		#raise ValueError("Tried to calculate RMS for empty signal, something probably went wrong")
	
	n = len(signal)	
	squared_signal = [x * x for x in signal]
	
	return sqrt(sum(squared_signal) / n)