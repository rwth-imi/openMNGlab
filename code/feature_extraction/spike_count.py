import numpy as np

from signal_artifacts import ActionPotential
from feature_extraction.feature_extractor import FeatureExtractor

## Calculate the "spike count" feature.
# Subdivide the timeframe before the action potential into several small fragments, then count the number of APs in each of these fragments.
class SpikeCount(FeatureExtractor):

	## The list of APs from which to construct the spike count feature
	actpots = None
	## The pre-AP timeframe for subdivision.
	timeframe = None
	## The number of intervals into which the timeframe is divided
	num_intervals = None

	## constructs this feature extractor.
	# @param actpots List of APs to subdivide
	# @param timeframe Pre-AP timeframe to divide
	# @param num_intervals Number of intervals to divide the timeframe into
	def __init__(self, actpots, timeframe, num_intervals):
		self.actpots = actpots
		self.timeframe = timeframe
		self.num_intervals = num_intervals

	def get_feature_name(self):
		return "spike_count"
		
	def get_feature_value(self, actpot):
		# get the tmax and tmin of the interval to consider
		t_max = actpot.onset
		t_min = actpot.onset - self.timeframe
		
		# filter only the action potentials between tmax and tmin
		actpots = [ap for ap in self.actpots if ap.onset > t_min and ap.onset < t_max]
		
		# build a feature vector with the number of APs for each "subdivision" of the timeframe
		counts = np.zeros(self.num_intervals)
		interval_len = float(self.timeframe) / float(self.num_intervals)
		
		for interv_idx in range(0, self.num_intervals):
			# get only the aps for this sub-interval
			interv_aps = [ap for ap in self.actpots if ap.onset > t_min + interv_idx * interval_len and ap.onset < t_min + (interv_idx + 1) * interval_len]
			# and then save the number of APs in this sub-interval
			counts[interv_idx] = len(interv_aps)
			
		return counts