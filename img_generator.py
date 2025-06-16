import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import logging
def generate_img(coords, waypoints, name, evaluation):
    data = coords
    data['sol'] = waypoints
    fig, ax = plt.subplots(figsize=(8, 6))

    # Iterate over the keys in the dictionary and plot accordingly
    for key, coords in data.items():
        # Extract only the (longitude, latitude) for plotting
        points = [(pt[0], pt[1]) for pt in coords]
        
        if key.startswith("poly"):
            # Plot polygons with yellow fill and full opacity
            polygon = Polygon(points, closed=True, facecolor='yellow', edgecolor='black', alpha=1.0)
            ax.add_patch(polygon)
            # Calculate centroid and add label above the polygon
            centroid_x = sum(pt[0] for pt in points) / len(points)
            centroid_y = sum(pt[1] for pt in points) / len(points)
            # Get maximum y-coordinate of the polygon
            max_y = max(pt[1] for pt in points)
            # Place label above the polygon with offset
            label_offset = 0.05  # Adjust this value to move label up/down
            ax.text(centroid_x, centroid_y, key, 
                   fontsize=12, ha='center', va='bottom',
                   bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
        elif key == "FlyZone":
            # Plot the flyzone with no fill (only edges)
            flyzone = Polygon(points, closed=True, fill=False, edgecolor='green', linewidth=2)
            ax.add_patch(flyzone)
        elif "Origin" in key:
            # Plot the origin as a point and label it
            x, y = points[0]
            ax.plot(x, y, marker='o', color='green', markersize=4)
            ax.text(x, y, 'Origin', fontsize=8, verticalalignment='bottom', horizontalalignment='right')
        elif "Destination" in key:
            # Plot the destination as a point and label it
            x, y = points[0]
            ax.plot(x, y, marker='o', color='blue', markersize=4)
            ax.text(x, y, 'Destination', fontsize=8, verticalalignment='bottom', horizontalalignment='left')
        elif key == "sol":
            # Plot the solution waypoints as a line
            x = [pt[0] for pt in points]
            y = [pt[1] for pt in points]
            ax.plot(x, y, color='black', linewidth=3)
            x_violating = []
            y_violating = []
            for line_segments in evaluation.segs:
                for line in line_segments:
                    start_waypoint = line[0]
                    end_waypoint = line[1]
                    x_violating.append(start_waypoint[0])
                    x_violating.append(end_waypoint[0])
                    y_violating.append(start_waypoint[1])
                    y_violating.append(end_waypoint[1])
            # for line in evaluation.violating_waypoints:
            #     for point in line:
            #         if x - point[0] < 1e-2 and y - point[1] < 1e-2:
            #             ax.plot(x, y, color='red', linewidth=3)
            # else:
            
            ax.plot(x_violating, y_violating, color='red', linewidth=3)
            if evaluation.out_pts:
                for wp in evaluation.out_pts:
                    logging.info(f"Waypoint outside flyzone: {wp}")
                    ax.plot(wp[0], wp[1], marker='o', color='red', markersize=6)


    # Set plot limits, labels, and title for clarity
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    # ax.set_title('2D Plot of Polygons, FlyZone, Origin, and Destination')
    ax.set_title(name)

    # Optionally, adjust the axis limits based on the data ranges
    ax.set_xlim(-98.5, -95.5)
    ax.set_ylim(32.0, 34.0)

    # plt.grid(True)
    plt.savefig(name)
