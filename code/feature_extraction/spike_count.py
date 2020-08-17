import numpy as np

def get_spike_count(actpot, actpots, timeframe, num_intervals):
	t_max = actpot.onset
	t_min = actpot.onset - timeframe
	
	# filter only the action potentials between tmax and tmin
	actpots = [ap for ap in actpots if ap.onset > t_min and ap.onset < t_max]
	
	# build a feature vector with the number of APs for each "subdivision" of the timeframe
	counts = np.zeros(num_intervals)
	interval_len = float(timeframe) / float(num_intervals)
	
	for interv_idx in range(0, num_intervals):
		# get only the aps for this sub-interval
		interv_aps = [ap for ap in actpots if ap.onset > t_min + interv_idx * interval_len and ap.onset < t_min + (interv_idx + 1) * interval_len]
		# and then save the number of APs in this sub-interval
		counts[interv_idx] = len(interv_aps)
		
	return counts

'''
	Builds a feature vector that saves the number of action potentials for each sub-interval.
	The sub-intervals are constructed as follows:
	1.) divide the whole interval defined by the timeframe into two equal parts
	2.) then, divide the rightmost part into two equally sized sub-intervals
	3.) repeat for num_splits times
	
	This may result in a vector of a shape like this:
	100s with 5 splits results in values for the following pre-AP time frames
	intervals |100s|50s|25s|12.5s|6.25s|3.125s|
	(15, 7, 4, 2, 1, 3)
'''

def get_adaptive_spike_count(actpot, actpots, timeframe, num_splits):
	t_max = actpot.onset
	t_min = actpot.onset - timeframe
	
	# filter only the action potentials between tmax and tmin
	actpots = [ap for ap in actpots if ap.onset > t_min and ap.onset < t_max]
	
	# build a feature vector
	counts = np.zeros(num_splits + 1)
	
	intv_tmax = t_max
	intv_tmin = t_min
	
	for intv_idx in range(0, num_splits + 1):
		# get all the APs between tmax and tmin
		aps = [ap for ap in actpots if ap.onset > intv_tmin and ap.onset < intv_tmax]
		counts[intv_idx] = len(aps)
		
		# increase t_min to halve the interval size
		intv_tmin = intv_tmin + (t_max - intv_tmin) / 2
		
	# return the feature vector containing the spike count
	return counts
		