"""This generates OVs for a given set of traces
"""

import numpy as np

from src.OVGeneration.DryVR.helperFunctions import compute_radii, discrepancy_params, normalise_radii

# Dunders
__author__ = "Ellis Thompson"


def dryvrConcurr(*args):
    args = args[0]
    return dryvrMain(args[0], args[1])


def dryvrMain(
    traces: np.ndarray,
    n_traces: int = 20,
):
    if traces.shape[0] < 15:
        raise ValueError("The system requires a minimum of 15 traces")

    if 15 <= traces.shape[0] < n_traces:
        print(
            f"[WARNING]: Running the generation with {traces.shape[0]} which is above the minimum 15 but less than"
            + f"specified {n_traces} traces!"
        )

    if traces.shape[0] <= n_traces:
        training_traces = traces
    else:
        idxs = np.random.choice(traces.shape[0], n_traces, replace=False)
        training_traces = traces[idxs]

    training_traces = training_traces[:, :, 0:4]

    center = (training_traces.max(axis=0) + training_traces.min(axis=0)) / 2

    training_traces = np.append([center], training_traces, axis=0)

    return dryvrRun(training_traces)


def dryvrRun(training_traces: np.ndarray, centre_idx: int = 0) -> np.ndarray:
    """Runs DryVR for a given set of training traces.

    Args:
        training_traces (np.ndarray): An array of training traces.
        centre_idx (int, optional): The index of the center trace. Defaults to 0.

    Returns:
        np.ndarray: An array of reachtube bounds for the given training traces.
    """
    # Assert that the training traces are valid
    if len(training_traces) < 2:
        raise ValueError("There must be at least 2 training traces.")

    # Get the centre trace
    centre_trace = training_traces[centre_idx]

    # Compute the initial radii and discrepancy parameters
    initial_radii = compute_radii(training_traces, centre_trace)
    discrepancy_parameters = discrepancy_params(training_traces, initial_radii)

    result = compute_reachtube(centre_trace, initial_radii, discrepancy_parameters, method="PWGlobal")

    # Ensure 100% training accuracy (all trajectories are contained)
    for trace_ind in range(training_traces.shape[0]):
        try:
            assert np.all(result[:, 0, :] <= training_traces[trace_ind, 1:, :])
            assert np.all(result[:, 1, :] >= training_traces[trace_ind, 1:, :])
        except AssertionError:
            raise ValueError(f"Trace #{trace_ind} of this initial set is not contained in the initial set") from None

    return result


def compute_reachtube(
    centre_trace: np.ndarray, initial_radii: np.ndarray, d_params: np.ndarray, method: str = "PWGlobal"
) -> np.ndarray:
    """Computes a reachtube for a set of traces, radii and parameters.

    Args:
        centre_trace (np.ndarray): The centre trace.
        initial_radii (np.ndarray): Array of initial radii.
        d_params (np.ndarray): The descrepency parameters.
        method (str, optional): Method to use. Defaults to 'PWGlobal'.

    Returns:
        np.ndarray: Returns the array reachtube
    """

    normalised_initial_radii = normalise_radii(initial_radii)

    trace_len, num_dims = centre_trace.shape  # This includes time

    if method != "PWGlobal":
        raise ValueError(f"Discrepancy computation method, '{method}', is not supported!")

    df = np.zeros((trace_len, num_dims))
    alldims_linear_separators = d_params
    num_dims = centre_trace.shape[1]
    for dim_ind in range(1, num_dims):
        prev_val = 0
        prev_ind = 1 if initial_radii[dim_ind - 1] == 0 else 0
        linear_separators = alldims_linear_separators[dim_ind - 1]
        if initial_radii[dim_ind - 1] != 0:
            df[0, dim_ind] = initial_radii[dim_ind - 1]
        for linear_separator in linear_separators:
            _, _, slope, y_intercept, start_ind, end_ind = linear_separator
            assert prev_ind == start_ind
            assert start_ind < end_ind
            start_ind, end_ind = int(start_ind), int(end_ind)

            segment_t = centre_trace[start_ind : end_ind + 1, 0]  # noqa: E203

            segment_df = normalised_initial_radii[dim_ind - 1] * np.exp(y_intercept + slope * segment_t)
            segment_df[0] = max(segment_df[0], prev_val)

            df[start_ind : end_ind + 1, dim_ind] = segment_df  # noqa: E203

            prev_val = segment_df[-1]
            prev_ind = end_ind
    assert np.all(df >= 0)
    reachtube_segment = np.zeros((trace_len - 1, 2, num_dims))
    reachtube_segment[:, 0, :] = np.minimum(centre_trace[1:, :] - df[1:, :], centre_trace[:-1, :] - df[:-1, :])
    reachtube_segment[:, 1, :] = np.maximum(centre_trace[1:, :] + df[1:, :], centre_trace[:-1, :] + df[:-1, :])

    return reachtube_segment
