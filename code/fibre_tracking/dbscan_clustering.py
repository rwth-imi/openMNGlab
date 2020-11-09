from metrics import clustering_metrics
from sklearn.cluster import DBSCAN
import numpy as np
import pandas as pd
from plotting import ClusterPlot2D

from typing import Iterable

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
	@staticmethod
	def perform_clustering(actpots, eps, min_samples, plot_results = False) -> Iterable[int]:
		# build feature vectors from the features provided by AP class
		features = np.array([[ap.features["latency"]] for ap in actpots])
		# channel_indices = np.array([ap.channel_index for ap in actpots])
		
		cls_idcs = DBSCAN(eps = eps, min_samples = min_samples, metric = clustering_metrics.latency_difference).fit_predict(features)

		# plot the results if desired
		if plot_results == True:
			cl2dplot = ClusterPlot2D()
			cl2dplot.plot(actpots = actpots, cls_idcs = cls_idcs)
						
		return cls_idcs