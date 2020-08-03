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