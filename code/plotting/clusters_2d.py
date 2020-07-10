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
	
	def __init__(self, width = 1000, height = 600):
		self.width = width
		self.height = height
				
	def plot(self, clustered_data_df):
		fig = go.Figure(layout = {"width": self.width, "height": self.height})
		
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
		
		self.fig = fig
		
	def make_hover_labels_from_df(df):
		labels = []
		for i, row in df.iterrows():
			lbl = "Latency: " + "{:1.2f}".format(row["Latency"] * 1000) + "ms<br>"
			lbl += "Energy: " + "{:1.2f}".format(row["Energy"]) + "mV^2<br>"
			lbl += "Cluster Index: " + "{:1.0f}".format(row["Cluster_Index"]) + "<br>"
			lbl += "Channel Index: " + "{:1.0f}".format(row["Channel_Index"]) + "<br>"
			
			labels.append(lbl)
			
		return labels