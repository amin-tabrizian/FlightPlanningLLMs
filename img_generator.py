import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

def generate_img(coords, waypoints, name):
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
        elif key == "FlyZone":
            # Plot the flyzone with no fill (only edges)
            flyzone = Polygon(points, closed=True, fill=False, edgecolor='red', linewidth=2)
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

    # Set plot limits, labels, and title for clarity
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('2D Plot of Polygons, FlyZone, Origin, and Destination')

    # Optionally, adjust the axis limits based on the data ranges
    ax.set_xlim(-98.5, -95.5)
    ax.set_ylim(32.0, 34.0)

    # plt.grid(True)
    plt.savefig(name)
