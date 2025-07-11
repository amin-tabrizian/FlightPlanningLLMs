import numpy as np
from matplotlib.patches import Ellipse
from scipy.spatial.distance import mahalanobis
from scipy.stats import norm

from src.OVGeneration.classes import Segment, OV


def spheroidNewConcurr(*args):
    args = args[0]
    return spheroidNewMain(args[0], args[1])


def spheroidNewMain(traces: np.ndarray, n_traces: int = 0.8, coverage=0.95, increment=0.02, use_mean=True):
    # Validate trace size
    if traces.shape[0] < 15:
        raise ValueError("The system requires a minimum of 15 traces")

    idxs = np.random.choice(traces.shape[0], int(n_traces * traces.shape[0]), replace=False)
    training_traces = traces[idxs]

    test_traces = test_traces = traces[np.setdiff1d(np.arange(len(traces)), idxs)]

    ov = OV()

    for i in range(training_traces.shape[1]):

        # Calculate the mean and covariance matrix of the data
        mu = (
            np.mean(training_traces[:, i, 1:3], axis=0)
            if use_mean
            else (np.min(training_traces[:, i, 1:3], axis=0) + np.max(training_traces[:, i, 1:3], axis=0)) / 2
        )

        cov = np.cov(training_traces[:, i, 1:3], rowvar=False)
        """NOTE: With the mu and cov the system now has enough information to build the ellipse. 
        The remainder code is to verify the ellipse is valid and adjust alpha."""

        alpha = adjust_alpha(mu, cov, training_traces[:, i, 1:3], test_traces[:, i, 1:3], coverage, increment)

        ov.insert(Segment(mu, cov, alpha))
    return ov


def adjust_alpha(mu, cov, train_traces, test_traces, coverage, increment):
    # Calculate the inverse covariance matrix
    inv_cov = np.linalg.inv(cov)

    # Calculate the Mahalanobis distances
    # https://en.wikipedia.org/wiki/Mahalanobis_distance
    training_distances = np.asarray([mahalanobis(train_traces[i], mu, inv_cov) for i in range(train_traces.shape[0])])

    testing_distances = np.asarray([mahalanobis(test_traces[i], mu, inv_cov) for i in range(test_traces.shape[0])])

    # Set the threshold distance
    threshold = np.percentile(training_distances, coverage * 100)

    included_percentage = len(testing_distances[testing_distances <= threshold]) / len(testing_distances)

    if included_percentage >= coverage:
        # Valid coverage from testing data
        return abs(norm.ppf((1 - coverage) / 2))

    # Need to expand alpha till coverage is met of testing data
    alpha = 0 + increment

    # Calculate the eigenvalues and eigenvectors of the covariance matrix
    eigenvals, eigenvecs = np.linalg.eigh(cov)

    # Sort the eigenvalues in descending order
    idx = eigenvals.argsort()[::-1]
    eigenvals = eigenvals[idx]
    eigenvecs = eigenvecs[:, idx]

    theta = np.degrees(np.arctan2(*eigenvecs[:, 0][::-1]))

    valid = False

    while not valid and alpha <= 1.0:
        # Calculate the confidence interval for a normal distribution
        z = abs(norm.ppf((1 - coverage) / 2)) + alpha

        width = 2 * np.sqrt(eigenvals[0]) * z
        height = 2 * np.sqrt(eigenvals[1]) * z

        ellipse = Ellipse(xy=mu, width=width, height=height, angle=theta)

        num_inside = sum(
            1 for i in range(len(testing_distances)) if ellipse.contains_point((test_traces[i, 0], test_traces[i, 1]))
        )
        if num_inside / len(testing_distances) < coverage:
            alpha += increment
        else:
            valid = True

    return z
