plotly_std_colors = ["blue", "green", "red", "cyan", "magenta", "yellow", "black"]

def get_fibre_color(index):
	return plotly_std_colors[index % len(plotly_std_colors)]