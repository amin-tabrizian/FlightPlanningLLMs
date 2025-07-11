import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString

def generate_osm_img(coords, waypoints, name, evaluation):
    try:
        # Prepare GeoDataFrames
        polygons = []
        polygon_names = []  # Keep track of polygon names for annotations
        flyzone = None
        origin = None
        destination = None
        lines = []
        violating_lines = []
        out_pts = []

        for key, pts in coords.items():
            if key.startswith("poly"):
                polygons.append(Polygon(pts))
                polygon_names.append(key)  # Store the polygon name
            elif key == "FlyZone":
                flyzone = Polygon(pts)
            elif "Origin" in key:
                origin = Point(pts[0])
            elif "Destination" in key:
                destination = Point(pts[0])
            else:
                # Check if it's another type of polygon (not Origin, Destination, or FlyZone)
                if len(pts) > 2:  # Ensure it's actually a polygon
                    polygons.append(Polygon(pts))
                    polygon_names.append(key)

        # Solution line
        sol_line = LineString(waypoints)
        lines.append(sol_line)

        # Violating segments
        for line_segments in evaluation.segs:
            for line in line_segments:
                violating_lines.append(LineString(line))

        # Out points
        if evaluation.out_pts:
            for wp in evaluation.out_pts:
                out_pts.append(Point(wp))

        # Create GeoDataFrames
        gdf_polys = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
        gdf_flyzone = gpd.GeoDataFrame(geometry=[flyzone], crs="EPSG:4326") if flyzone else None
        gdf_origin = gpd.GeoDataFrame(geometry=[origin], crs="EPSG:4326") if origin else None
        gdf_dest = gpd.GeoDataFrame(geometry=[destination], crs="EPSG:4326") if destination else None
        gdf_lines = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326")
        gdf_violating = gpd.GeoDataFrame(geometry=violating_lines, crs="EPSG:4326")
        gdf_outpts = gpd.GeoDataFrame(geometry=out_pts, crs="EPSG:4326")

        # Convert to Web Mercator for contextily
        gdf_polys = gdf_polys.to_crs(epsg=3857)
        if gdf_flyzone is not None:
            gdf_flyzone = gdf_flyzone.to_crs(epsg=3857)
        if gdf_origin is not None:
            gdf_origin = gdf_origin.to_crs(epsg=3857)
        if gdf_dest is not None:
            gdf_dest = gdf_dest.to_crs(epsg=3857)
        gdf_lines = gdf_lines.to_crs(epsg=3857)
        gdf_violating = gdf_violating.to_crs(epsg=3857)
        gdf_outpts = gdf_outpts.to_crs(epsg=3857)

        # Plot
        fig, ax = plt.subplots(figsize=(10, 8))
        if gdf_flyzone is not None:
            gdf_flyzone.boundary.plot(ax=ax, color='green', linewidth=2, label='FlyZone')
        gdf_polys.plot(ax=ax, color='yellow', edgecolor='black', alpha=0.5, label='Polygons')
        gdf_lines.plot(ax=ax, color='black', linewidth=2, label='Solution')
        gdf_violating.plot(ax=ax, color='red', linewidth=3, label='Violating')
        if gdf_origin is not None:
            gdf_origin.plot(ax=ax, color='green', marker='o', markersize=50, label='Origin')
        if gdf_dest is not None:
            gdf_dest.plot(ax=ax, color='blue', marker='o', markersize=50, label='Destination')
        if not gdf_outpts.empty:
            gdf_outpts.plot(ax=ax, color='red', marker='x', markersize=80, label='Out Points')

        # Add OSM basemap
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

        # Add polygon annotations after all plotting is complete
        for i, polygon_geom in enumerate(gdf_polys.geometry):
            if i < len(polygon_names):  # Safety check
                # Get centroid for X coordinate and bounds for top Y coordinate
                centroid = polygon_geom.centroid
                bounds = polygon_geom.bounds  # (minx, miny, maxx, maxy)
                top_y = bounds[3]  # Maximum Y coordinate (top of polygon)
                
                # Add text annotation with a background box for readability
                ax.annotate(polygon_names[i], 
                           xy=(centroid.x, top_y),
                           xytext=(0, 5),  # Small offset upward from the top edge
                           textcoords='offset points',
                           ha='center', va='bottom',
                           fontsize=8,
                           color='black',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))

        ax.set_axis_off()
        plt.legend()
        plt.tight_layout()
        plt.savefig(name, bbox_inches='tight', pad_inches=0.05)
        plt.close()
        
        return True  # Return success status
        
    except Exception as e:
        print(f"Error generating OSM image: {e}")
        return False

# Usage:
# generate_osm_img(coords, waypoints, "output.png", evaluation) 