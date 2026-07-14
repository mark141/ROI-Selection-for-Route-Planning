# metrics for the evaluation


def roi_metrics(initial_roi, final_roi):
    initial_area = initial_roi.area
    final_area = final_roi.area

    roi_reduction = 1 - final_area / initial_area
    remaining_area = final_area / initial_area

    return (
        initial_area,
        final_area,
        roi_reduction,
        remaining_area,
    )


def constraint_metrics(reachable_df, threshold):
    """
    Metrics are computed only on reachable weather points,
    i.e., one weather observation per location at the estimated
    traversal time.
    """

    reachable_points = len(reachable_df)

    violating_points = (
        reachable_df["precipitation"] > threshold
    ).sum()

    satisfying_points = reachable_points - violating_points

    if reachable_points == 0:
        satisfaction = 1.0
    else:
        satisfaction = satisfying_points / reachable_points

    return (
        reachable_points,
        satisfying_points,
        violating_points,
        satisfaction,
    )