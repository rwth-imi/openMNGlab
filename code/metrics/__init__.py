## @package metrics
# Contains classes to calculate metrics, e.g., for clustering or for correlation analyses.
# TODO: generalize from features, maybe. This could make some of the metrics here more "low-level" and therefore re-usable.

from metrics.normalized_cross_correlation import normalized_cross_correlation
from metrics.root_mean_square_power import median_RMS, root_mean_square_power