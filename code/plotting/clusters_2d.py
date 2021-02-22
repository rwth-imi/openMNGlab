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
    def plot(self, actpots, cls_idcs):
        
        fig = go.Figure(layout = {"width": self.width, "height": self.height})
        
        fig.add_trace(
            go.Scatter(
                mode = "markers",
                x = [ap.features["latency"] for ap in actpots],
                y = [ap.onset for ap in actpots],
                marker_color = [get_fibre_color(lbl) for lbl in cls_idcs],
                marker_symbol = [ap.channel_index for ap in actpots],
                hovertemplate = "%{text}",
                text = ClusterPlot2D.make_hover_labels(actpots = actpots, cls_idcs = cls_idcs)
            )
        )
        
        fig.update_layout(
            xaxis_title="Response Latency (s)",
            yaxis_title="Time (s)"
        )
        
        fig.show()
        
        self.fig = fig
        
    ## Helper function to create plotly hover labels for an AP
    # param df Input dataframe containing this particular AP
    @staticmethod
    def make_hover_labels(actpots, cls_idcs):
        labels = []
        for ap, cl_idx in zip(actpots, cls_idcs):
            lbl = "Latency: " + "{:1.2f}".format(ap.features["latency"] * 1000) + "ms<br>"
            lbl += "Energy: " + "{:1.2f}".format(ap.features["energy"]) + "mV^2<br>"
            lbl += "Cluster Index: " + "{:1.0f}".format(cl_idx) + "<br>"
            lbl += "Channel Index: " + "{:1.0f}".format(ap.channel_index) + "<br>"
            
            labels.append(lbl)
            
        return labels