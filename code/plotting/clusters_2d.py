import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

'''
	**********************************
	A class to wrap a 2D plot of AP clusters
	**********************************
'''
class ClusterPlot2D:
	
	def __init__(self, width = 15, height = 10):
		self.width = width
		self.height = height
				
	def plot(self, clustered_data_df):
		# fig = px.scatter(clustered_data_df, x = "Latency", y = "Energy", color = "Cluster_Index", maker_symbol = "Channel_Index", showscale = False)
		# fig.show()
		
		fig = go.Figure()
		
		fig.add_trace(
			go.Scatter(
				mode = "markers",
				x = clustered_data_df["Latency"],
				y = clustered_data_df["Energy"],
				marker_color = clustered_data_df["Cluster_Index"],
				marker_symbol = clustered_data_df["Channel_Index"],
				hovertemplate = "%{text}",
				text = ClusterPlot2D.make_hover_labels_from_df(df = clustered_data_df)
			)
		)
		
		fig.update_layout(
			xaxis_title="Distance to previous regular stimulus (s)",
			yaxis_title="Normalized signal energy (mV^2)"
		)
		
		fig.show()
		
	def make_hover_labels_from_df(df):
		labels = []
		for i, row in df.iterrows():
			lbl = "Latency: " + "{:1.2f}".format(row["Latency"] * 1000) + "ms<br>"
			lbl += "Energy: " + "{:1.2f}".format(row["Energy"]) + "mV^2<br>"
			lbl += "Cluster Index: " + "{:1.0f}".format(row["Cluster_Index"]) + "<br>"
			lbl += "Channel Index: " + "{:1.0f}".format(row["Channel_Index"]) + "<br>"
			
			labels.append(lbl)
			
		return labels
		
	'''
	def plot(self, actpots, feature_vectors, cluster_labels, markers = ['o', 'x', 's', 'D'], cluster_colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'gray'], xlabel = "Distance to stimulus (s)", ylabel = "Normalized AP energy (mV^2)", xscale = 'linear'):
		# retrieve the channel index for each of the APs
		channel_indices = np.array([ap.get_channel_index() for ap in actpots])
		
		fig = plt.figure(figsize = (self.width, self.height))
		
		# iterate over the channels and choose marker according to channel 
		channel_index = 0
		while channel_index <= max(channel_indices):
			# get a mask for all APs from this channel
			indices = (channel_indices == channel_index)
			
			# get the 'cut' list of features and the colors corresponding to their cluster membership
			channel_features = feature_vectors[indices, :]
			colors = np.array([cluster_colors[label % len(cluster_colors)] for label in cluster_labels])
			colors = colors[indices]
			
			# plot APs with marker according to channel index
			plt.scatter(x = channel_features[:, 0], y = channel_features[:, 1], c = colors, marker = markers[channel_index], label = "Template " + str(channel_index))
				
			channel_index = channel_index + 1
		
		# print the names of the clusters
		cluster_index = 0
		while cluster_index < max(cluster_labels):
			# get mask for cluster
			indices = (cluster_index == cluster_labels)
			
			cluster_points = feature_vectors[indices]
			cluster_center = np.mean(cluster_points, axis = 0)
			
			plt.text(x = cluster_center[0], y = cluster_center[1], s = str(cluster_index), fontsize = 12)
			
			cluster_index = cluster_index + 1
			
		plt.xlabel(xlabel)
		plt.xscale(xscale)
		plt.ylabel(ylabel)
		plt.legend()
		
		plt.show()
		
		self.fig = fig
	'''

	def save_to_file(self, filename):
		self.fig.savefig(fname = filename, dpi = 400)
		print("Figure saved.")