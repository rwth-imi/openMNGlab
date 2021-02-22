## The standard plotly colors in a separate variable
plotly_std_colors = ["blue", "green", "red", "cyan", "magenta", "yellow", "black"]

## Returns a fibre color for a given cluster/fibre index.
def get_fibre_color(index):
    return plotly_std_colors[index % len(plotly_std_colors)]

# Dapsys code
from matplotlib import pyplot as plt
import numpy as np

## Generate colors from continuous matplotlib colormaps
def get_colors(cmap = plt.cm.Greens, length = 100):
    '''
    Generate color list for a particular matplotlib cmap
    
    Parameters
    ----------
    cmap: plt.cm | Matplotlib colormap.
    length: int | Length of the signal

    Returns
    -------
    colors: list | List of colors
    '''       
    cmaplist = [cmap(i) for i in range(cmap.N)]
    colors = []
    for i in np.linspace(0, len(cmaplist)-1, length, dtype='int'):
        colors.append(f'rgb({cmaplist[i][0]},{cmaplist[i][1]},{cmaplist[i][2]})')
    
    return colors