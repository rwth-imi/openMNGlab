import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from plotting import get_fibre_color

## Provides functionality to plot a 2D cluster plot.
# This is a scatter plot we can use to visualize clustering of 2D data points.
class ClusterPlot2D:
	
	## Constructs a plot with the provided size
	def __init__(self, width = 1000, height = 600):
		self.width = width
		self.height = height
				
	## Plots the data provided in a pandas dataframe.
	# @param clustered_data_df A pandas dataframe resulting from clustering, see also fibre_tracking.dbscan_clustering.DBScanClustering
	def plot(self, clustered_data_df):
		fig = go.Figure(layout = {"width": self.width, "height": self.height})
		
		fig.add_trace(
			go.Scatter(
				mode = "markers",
				x = clustered_data_df["Latency"],
				y = clustered_data_df["Energy"],
				marker_color = [get_fibre_color(idx) for idx in clustered_data_df["Cluster_Index"]],
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
		
		self.fig = fig
		
	## Helper function to create plotly hover labels for an AP
	# param df Input dataframe containing this particular AP
	def make_hover_labels_from_df(df):
		labels = []
		for i, row in df.iterrows():
			lbl = "Latency: " + "{:1.2f}".format(row["Latency"] * 1000) + "ms<br>"
			lbl += "Energy: " + "{:1.2f}".format(row["Energy"]) + "mV^2<br>"
			lbl += "Cluster Index: " + "{:1.0f}".format(row["Cluster_Index"]) + "<br>"
			lbl += "Channel Index: " + "{:1.0f}".format(row["Channel_Index"]) + "<br>"
			
			labels.append(lbl)
			
		return labels