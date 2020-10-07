import numpy as np

from signal_artifacts import ActionPotential
from feature_extraction.feature_extractor import FeatureExtractor

## Builds a feature vector that saves the number of action potentials for each sub-interval.
# The sub-intervals are constructed as follows: \n
# 1.) divide the whole interval defined by the timeframe into two equal parts \n
# 2.) then, divide the rightmost part into two equally sized sub-intervals \n
# 3.) repeat for num_splits times \n\n
# This may result in a vector of a shape like this: \n
# 100s with 5 splits results in values for the following pre-AP time frames \n
# intervals |100s|50s|25s|12.5s|6.25s|3.125s| \n
# (15, 7, 4, 2, 1, 3)
class AdaptiveSpikeCount(FeatureExtractor):

	## The list of APs from which to construct the spike count feature
	actpots = None
	## The pre-AP timeframe for subdivision.
	timeframe = None
	## How often the timeframe should be split into smaller intervals (results in num_split + 1 counts)
	num_splits = None

	## constructs this feature extractor.
	# @param actpots List of APs to subdivide
	# @param timeframe Pre-AP timeframe to divide
	# @param How often the timeframe should be split into smaller intervals (results in num_split + 1 counts)
	def __init__(self, actpots, timeframe, num_splits):
		self.actpots = actpots
		self.timeframe = timeframe
		self.num_splits = num_splits
	
	def get_feature_name(self):
		return "adaptive_spike_count"
	
	## returns the adaptive spike count for the given AP
	# @param actpot the AP for which the adaptive spike count is computed
	def get_feature_value(self, actpot):
		t_max = actpot.onset
		t_min = actpot.onset - self.timeframe
		
		# filter only the action potentials between tmax and tmin
		actpots = [ap for ap in self.actpots if ap.onset > t_min and ap.onset < t_max]
		
		# build a feature vector
		counts = np.zeros(self.num_splits + 1)
		
		intv_tmax = t_max
		intv_tmin = t_min
		
		for intv_idx in range(0, self.num_splits + 1):
			# get all the APs between tmax and tmin
			aps = [ap for ap in self.actpots if ap.onset > intv_tmin and ap.onset < intv_tmax]
			counts[intv_idx] = len(aps)
			
			# increase t_min to halve the interval size
			intv_tmin = intv_tmin + (t_max - intv_tmin) / 2
			
		# return the feature vector containing the spike count
		return counts