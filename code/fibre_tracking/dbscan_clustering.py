from metrics import clustering_metrics
from sklearn.cluster import DBSCAN
import numpy as np
import pandas as pd

class DBSCANClustering:

	def perform_clustering(actpots, eps, min_samples) -> pd.DataFrame:
		# build feature vectors from the features provided by AP class
		features = np.array([[ap.get_dist_to_prev_reg_el_stimulus(), ap.get_normalized_energy()] for ap in actpots])
		channel_indices = np.array([ap.get_channel_index() for ap in actpots])
		
		labels = DBSCAN(eps = eps, min_samples = min_samples, metric = clustering_metrics.time_dist_and_energy, metric_params = {'energy_importance': 0}).fit_predict(features)
				
		return pd.DataFrame(data = {'Onset': [ap.get_onset() for ap in actpots],
						'Offset': [ap.get_offset() for ap in actpots],
						'Latency': [ap.get_dist_to_prev_reg_el_stimulus() for ap in actpots],
						'Energy': [ap.get_normalized_energy() for ap in actpots],
						'Channel_Index': channel_indices,
						'Cluster_Index': labels}, 
						columns = ['Onset', 'Offset', 'Latency', 'Energy', 'Channel_Index', 'Cluster_Index'])