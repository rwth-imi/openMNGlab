from metrics import clustering_metrics
from sklearn.cluster import DBSCAN
import numpy as np
import pandas as pd
from plotting import ClusterPlot2D

## Encapsulates DBSCAN clustering and plotting into a class.
# It currently uses the latency and energy features of the signal_artifacts.action_potential.ActionPotential
class DBSCANClustering:

	## Pandas dataframe, containing the action potentials, their features and the cluster index as found by the DBSCAN algorithm.
	result_df = None

	## Runs DBSCAN clustering on the action potentials and visualizes the results if wanted.
	# @param actpots List of action potentials to cluster
	# @param eps Maximum distance for which a cluster is extended, see also min_samples
	# @param min_samples Minimum samples that need to be closer than eps so that a new cluster is created
	# @param save_fibre_prediction If True, writes the cluster index / fibre prediction into the attribute "implied_fibre_index" of the AP
	# @param plot_results If True, the results are visualized using a 2D scatter plot
	def perform_clustering(self, actpots, eps, min_samples, save_fibre_prediction = True, plot_results = False) -> pd.DataFrame:
		# build feature vectors from the features provided by AP class
		features = np.array([[ap.features["latency"], ap.features["energy"]] for ap in actpots])
		channel_indices = np.array([ap.channel_index for ap in actpots])
		
		labels = DBSCAN(eps = eps, min_samples = min_samples, metric = clustering_metrics.time_dist_and_energy, metric_params = {'energy_importance': 0}).fit_predict(features)
				
		# if desired, store the fibre prediction in the AP class
		if save_fibre_prediction == True:
			for ap, lbl in zip(actpots, labels):
				ap.implied_fibre_index = lbl
				
		self.result_df = pd.DataFrame(data = {'Onset': [ap.onset for ap in actpots],
						'Offset': [ap.offset for ap in actpots],
						'Latency': [ap.features["latency"] for ap in actpots],
						'Energy': [ap.features["energy"] for ap in actpots],
						'Channel_Index': channel_indices,
						'Cluster_Index': labels}, 
						columns = ['Onset', 'Offset', 'Latency', 'Energy', 'Channel_Index', 'Cluster_Index'])
						
		if plot_results == True:
			cl2dplot = ClusterPlot2D()
			cl2dplot.plot(clustered_data_df = self.result_df)
						
		return self.result_df