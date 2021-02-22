## This function returns the absolute of the time distance between two points.
# It is currently used to calculate the distance between an AP and a stimulus, but could generally also be used for any vector with time in its first component.
def latency_difference(x, y):
    time_diff = abs(x[0] - y[0])
    
    return time_diff