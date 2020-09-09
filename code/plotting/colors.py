## The standard plotly colors in a separate variable
plotly_std_colors = ["blue", "green", "red", "cyan", "magenta", "yellow", "black"]

## Returns a fibre color for a given cluster/fibre index.
def get_fibre_color(index):
	return plotly_std_colors[index % len(plotly_std_colors)]