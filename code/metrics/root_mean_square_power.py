from math import sqrt, floor
from neo.core.analogsignal import AnalogSignal
from quantities.quantity import Quantity
from neo_importers.neo_wrapper import ElectricalStimulusWrapper
from statistics import median
from typing import Iterable
from quantities import ms

## This method implements the median RMS as defined in the Turnquist-Namer paper dealing with track correlation for fibre tracking.
# The paper can be accessed here: https://www.sciencedirect.com/science/article/abs/pii/S0165027016000054
# @param sweeps The list of sweeps in the recording that should be analyzed
# @param center_sweep_idx Index of the sweep around which we extract the sweeps according to radius, also called k in the paper
# @param latency_slope Slope along which the RMS is calculated. Also called m in the paper, so we have the actual latency as t + r * m, where t is the latency and -R <= r <= R is the index in the R-environment around k. In s/sweep!
# @param latency Latency behind the eletrical stimulus in each sweep around which we look for the median RMS, called t in the paper. In s!
# @param radius Radius or number of sweeps which we want to consider during search of the median RMS, labelled r in the paper
# @param window_size Size of the window around the (computed) latency which is used to calculate the RMS. Given in s!
# @param sampling_rate Sampling rate of the recording, required for array access
def median_RMS(raw_signal: AnalogSignal, el_stimuli: Iterable[ElectricalStimulusWrapper], center_stim_idx: int, latency_slope: Quantity, latency: Quantity, \
	radius: int, window_size: float = 2 * ms):
	
	# check if the input is valid
	if center_stim_idx - radius < 0 or center_stim_idx + radius > len(el_stimuli) - 1:
		raise ValueError("The radius for median RMS calculation exceeds either the first or the last position in the array of electrical stimuli. Reduce radius or increase the center sweep index to resolve this issue.")
		
	# restrict only to the sweeps which lie within the radius around the "center sweep"
	rms = []
	
	el_stimulus: ElectricalStimulusWrapper
	for r, (_, el_stimulus) in zip(range(-radius, radius + 1), enumerate(el_stimuli[center_stim_idx - radius : center_stim_idx + radius])):		
		# calculate the latency shift in each direction
		t = el_stimulus.time + latency + r * latency_slope
		# calculate the window borders
		t_min_idx = max(floor((t - (window_size / 2)) * raw_signal.sampling_rate), 0)
		t_max_idx = max(min(floor((t + (window_size / 2)) * raw_signal.sampling_rate), len(raw_signal)), 0)
		
		# extract only this part of the sweep's signal
		sig = raw_signal[t_min_idx : t_max_idx]
		
		# TODO: theoretically, we could "wrap around" the end of beginning and end of the sweeps here.
		# But I'd argue that if the track crosses the border between the sweeps, i.e., the electrical stimulus itself, it might not be a track in the first place
		# Therefore, what we do for now is that we restrict t_min and t_max to [0, len(sweep)] and see what happens.
		
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
	squared_signal = signal**2
	
	return sqrt(sum(squared_signal.magnitude) / n) * signal.units * signal.units