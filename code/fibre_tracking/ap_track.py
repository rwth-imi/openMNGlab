from fibre_tracking.track_correlation import track_correlation, get_tc_noise_estimate

class APTrack:

	## this attribute stores the latencies at the individual sweeps
	# they should be stored as tuples (k, t) where k is the sweep index and t is the latency at the sweep k
	latencies = None
	
	## Construct an object for an AP track in the recording
	# @param latencies
	def __init__(self, latencies):
		
		# store the latency tuples in a sorted list
		self.latencies = sorted(latencies, key = lambda latency: latency[0])
	
	def extend_upwards(self, eps = 0.05):
		pass
		
	
	def extend_downwards(self):
		pass
		
	def insert_latency(self, sweep_idx, latency):
		
		# go through the existing latencies to insert the new one in the right place
		lst_idx = 0
		while lst_idx < len(self.latencies) and sweep_idx > self.latencies[lst_idx][0]:
			lst_idx += 1
			
		self.latencies.insert(lst_idx, (sweep_idx, latency))