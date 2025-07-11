import numpy as np
import scipy as sp


def compute_radii(training_traces: np.ndarray, centre_trace: np.ndarray) -> np.ndarray:
    """Computes the radii of a set of training traces.

    Args:
        training_traces (np.ndarray): The training traces.
        centre_trace (np.ndarray): The centre trace.

    Returns:
        np.ndarray: Returns the radii.
    """

    return np.max(np.abs(centre_trace[0, 1:4] - training_traces[:, 0, 1:4]), axis=0) + 1e-10


def discrepancy_params(training_traces: np.ndarray, initial_radii: np.ndarray, method: str = "PWGlobal") -> np.ndarray:
    """Calculate the discrepencacy parameters for DryVR

    Args:
        training_traces (np.ndarray): Array of training traces.
        initial_radii (np.ndarray): Array of initial radii.
        method (str, optional): Method to use. Defaults to 'PWGlobal'.

    Returns:
        np.ndarray: Returns an array of discrenpancy parameters.

    Raises:
        ValueError: If traces dont have the same initial time.
    """

    if not np.all(training_traces[0, :, 0] == training_traces[1:, :, 0]):
        raise ValueError("All traces must have the same initial time")

    # Get the length parameters (the dimensions include time)
    _, len_trace, num_dims = training_traces.shape

    # Get the centre trace and initial time
    centre_trace = training_traces[0]
    trace_initial_time = centre_trace[0, 0]

    # Ensure all times are relative to a 0 delta
    x_points = centre_trace[:, 0] - trace_initial_time

    # Get y_points as sensitivities
    y_points = all_sensitivities_calc(training_traces, initial_radii)

    # Prepare points array
    points = np.zeros((num_dims - 1, len_trace, 2))
    points[np.where(initial_radii != 0), 0, 1] = 1.0
    points[:, :, 0] = np.reshape(x_points, (1, x_points.shape[0]))
    points[:, 1:, 1] = y_points

    # Normalise the radii
    initial_radii = normalise_radii(initial_radii)

    df = np.zeros((len_trace, num_dims))

    if method == "PW":
        return points
    elif method == "PWGlobal":
        # Replace zeros with epsilons
        points[:, :, 1] = np.maximum(points[:, :, 1], 1e-10)

        # To fit exponentials make y axis log of sensitivity, This is equal to lnK?
        points[:, :, 1] = np.log(points[:, :, 1])

        # Define dim linear separator
        alldims_linear_separators = []

        for dim_ind in range(1, num_dims):  # For each dimension (without time)
            new_min = min(
                np.min(points[dim_ind - 1, 1:, 1]) + -100,
                -0.25,
            )

            if initial_radii[dim_ind - 1] == 0:
                # Exclude initial set, then add true minimum points
                new_points = np.row_stack(
                    (
                        np.array((points[dim_ind - 1, 1, 0], new_min)),
                        np.array((points[dim_ind - 1, -1, 0], new_min)),
                    )
                )
            else:
                # Start from zero, then add true minimum points
                new_points = np.row_stack(
                    (
                        points[dim_ind - 1, 0, :],
                        np.array((points[dim_ind - 1, 0, 0], new_min)),
                        np.array((points[dim_ind - 1, -1, 0], new_min)),
                    )
                )

                df[0, dim_ind] = initial_radii[dim_ind - 1]
                # Tuple order is start_time, end_time, slope, y-intercept

            cur_dim_points = np.concatenate((points[dim_ind - 1, 1:, :], new_points), axis=0)

            cur_hull = sp.spatial.ConvexHull(cur_dim_points)

            vert_inds = list(zip(cur_hull.vertices[:-1], cur_hull.vertices[1:]))
            vert_inds.append((cur_hull.vertices[-1], cur_hull.vertices[0]))

            linear_separators = []
            for end_ind, start_ind in vert_inds:
                if (
                    cur_dim_points[start_ind, 1] != new_min and cur_dim_points[end_ind, 1] != new_min
                ):  # If not a true minimum
                    slope = (cur_dim_points[end_ind, 1] - cur_dim_points[start_ind, 1]) / (
                        cur_dim_points[end_ind, 0] - cur_dim_points[start_ind, 0]
                    )

                    y_intercept = cur_dim_points[start_ind, 1] - cur_dim_points[start_ind, 0] * slope
                    start_time = cur_dim_points[start_ind, 0]
                    end_time = cur_dim_points[end_ind, 0]

                    assert start_time < end_time

                    if start_time == 0:
                        linear_separators.append((start_time, end_time, slope, y_intercept, 0, end_ind + 1))
                    else:
                        linear_separators.append(
                            (
                                start_time,
                                end_time,
                                slope,
                                y_intercept,
                                start_ind + 1,
                                end_ind + 1,
                            )
                        )

            linear_separators.sort()
            alldims_linear_separators.append(linear_separators)
        return alldims_linear_separators


def all_sensitivities_calc(training_traces: np.ndarray, initial_radii: np.ndarray) -> np.ndarray:
    """Calculates the sensitivities

    Args:
        training_traces (np.ndarray): Array of training traces.
        initial_radii (np.ndarray): Array of initial radii.

    Returns:
        np.ndarray: Returns array of sensitivities
    """

    _, trace_len, ndims = training_traces.shape

    # Normalise the radii
    normalizing_initial_set_radii = normalise_radii(initial_radii)

    y_points = np.zeros((normalizing_initial_set_radii.shape[0], trace_len - 1))

    for cur_dim_ind in range(1, ndims):
        normalized_initial_points = training_traces[:, 0, 1:] / normalizing_initial_set_radii
        initial_distances = sp.spatial.distance.pdist(normalized_initial_points, "chebyshev")
        for cur_time_ind in range(1, trace_len):

            t = (
                sp.spatial.distance.pdist(
                    np.reshape(
                        training_traces[:, cur_time_ind, cur_dim_ind],
                        (training_traces.shape[0], 1),
                    ),
                    "chebychev",
                )
                / normalizing_initial_set_radii[cur_dim_ind - 1]
            ) / initial_distances
            t = t[~np.isnan(t)]

            y_points[cur_dim_ind - 1, cur_time_ind - 1] = np.max(t)
    return y_points


def normalise_radii(radii: np.ndarray) -> np.ndarray:
    """Normalises the radii

    Args:
        radii (np.ndarray): Array of radii.

    Returns:
        np.ndarray: Returns array of normalised radii.
    """

    initial_radii = radii.copy()
    initial_radii[np.where(initial_radii == 0)] = 1.0

    return initial_radii
