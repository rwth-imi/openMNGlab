import numpy as np
from collections.abc import Iterable

from fibre_tracking.track_correlation import track_correlation, get_tc_noise_estimate, search_for_max_tc

## An AP track which means that a for number of sweeps 0 to k, we have latencies t_0, ..., t_k that belong to a latency track.
# A latency track can therefore also be written as a list of entries (i, t_i) where i is the sweep index and t_i the corresponding latency.
# This is what we are trying to achieve with this class.
class APTrack(object):

	## this attribute stores the latencies at the individual sweeps
	# they should be stored as tuples (k, t) where k is the sweep index and t is the latency at the sweep k
	_latencies = None
	
	## Construct an object for an AP track in the recording
	# @param latencies A list of tuples (sweep_idx, latency) where sweep_idx is the index of the sweep (also called k in the paper) and the latency t (in seconds)
	def __init__(self, latencies):
		
		# store the latency tuples in a sorted list
		self._latencies = sorted(latencies, key = lambda latency: latency[0])
	
	## Method to construct an AP track class from some action potentials.
	# @param sweeps List of sweeps
	# @param aps List of action potentials
	@staticmethod
	def from_aps(sweeps: Iterable, aps: Iterable):
		
		# this list is meant to store the lateny tuples that are required to spawn a new AP track
		latencies = []
		
		# go over the aps to find their sweep index
		sweep_idx = 0
		for ap in aps:
			# increase the sweep index until we found the sweep in which the AP was triggered
			while sweep_idx < len(sweeps) - 1 and ap.onset > sweeps[sweep_idx].t_end:
				sweep_idx += 1
				
			# calculate latency and store both as tuples
			latency = ap.onset - sweeps[sweep_idx].t_start + (ap.duration / 2)	
			latencies.append((sweep_idx, latency))
		
		return APTrack(latencies = latencies)
		
	## This method is not yet implemented but should be similar to the extend_downwards function.
	# TODO implement!
	def extend_upwards(self):
		pass
		
	
	## Method to extend an existing latency track in downward direction
	# @param sweeps List of sweeps in the recording
	# @param num_sweeps For how many sweeps should we extend this track
	# @param max_shift Maximum latency shift between one sweep i and the next sweep i + 1
	# @param max_slope Absolute value for the maximum slope that is considered when linearizing the track around the last sweep
	# @param radius Radius of the "window" from which the latencies for track linearization are selected
	# @param window_size Window size that is used to calculate the Root Mean Squared signal power
	# @param slope_penalty_term Penalty term that is used to weight the latencies in the next slope. 'cos' penalty term is the one proposed by Turnquist et al. See also fibre_tracking.track_correlation.search_for_max_tc for more info.
	def extend_downwards(self, sweeps, num_sweeps = 1, max_shift = 0.003, max_slope = 0.003, radius = 2, window_size = 0.001, slope_penalty_term = 'cos', verbose = False):
		
		for i in range(num_sweeps):
			# Get the last R (radius) latencies to fit a line
			sweep_idcs = self.sweep_idcs
			latencies = self.latencies
		
			# fit a line to the existing sweep indices (depending on the chosen radius) and latencies to get estimates for the line parameters
			if len(self._latencies) > 1:
				slope, latency_intercept = np.polyfit(x = sweep_idcs[min(-len(self._latencies), -radius - 1) : ], y = latencies [min(-len(self._latencies), -radius - 1) : ], deg = 1)
			elif len(self._latencies) == 1:
				slope = 0
				latency_intercept = latencies[0]
			else:
				raise RuntimeError("Cannot extend an empty track!")
			
			# using these parameters, predict the latency in the very next sweep
			next_sweep_idx = max(sweep_idcs) + 1
			pred_latency = slope * next_sweep_idx + latency_intercept
			
			# search for the maximum TC in a certain environment around the predicted latency
			max_tc_latency, tc = search_for_max_tc(sweeps = sweeps, sweep_idx = next_sweep_idx, latency = pred_latency, max_shift = max_shift, max_slope = max_slope, \
													slope_penalty_term = slope_penalty_term, established_slope = slope, radius = radius, window_size = window_size)
			
			self.insert_latency(sweep_idx = next_sweep_idx, latency = max_tc_latency)
			
			if verbose == True:
				print("Added AP to track: sweep " + str(next_sweep_idx) + " , latency " + str(max_tc_latency))
		
	## Use this function to add latencies to this track!
	# @param sweep_idx Index of the sweep where you want to add the latency
	# @param latency The latency itself (in seconds)
	def insert_latency(self, sweep_idx, latency):
		
		# go through the existing latencies to insert the new one in the right place
		lst_idx = 0
		while lst_idx < len(self._latencies) and sweep_idx > self._latencies[lst_idx][0]:
			lst_idx += 1
			
		self._latencies.insert(lst_idx, (sweep_idx, latency))
		
	## This function handles calls like len(track)
	def __len__(self):
		return len(self._latencies)
		
	@property
	def sweep_idcs(self):
		return [x[0] for x in self._latencies]
		
	@property
	def latencies(self):
		return [x[1] for x in self._latencies] 