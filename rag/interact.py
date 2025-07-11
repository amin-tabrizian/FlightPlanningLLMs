from typing import List, Optional, Sequence, Union, Literal
from sqlalchemy import and_, select
from .models import Polygon, Scenario, Origin, Destination, ScenarioOutput
from .db import Session
import hashlib
import xml.etree.ElementTree as ET
import re

 
def load_scenario(file_path: str) -> Scenario:
    """
    Load a scenario from a KML file. If the scenario already exists in the database, it is returned.
    Otherwise, a new scenario is created and stored in the database.

    Args:
        file_path (str): Path to the KML file.

    Returns:
        Scenario: The loaded or newly created scenario.
    """
    with Session() as session:
        hash = hashlib.sha512(open(file_path, 'rb').read()).hexdigest()

        # Check if scenario with this hash exists
        scenario = session.execute(
            select(Scenario).where(Scenario.file_hash == hash)
        ).scalar_one_or_none()

        if scenario is not None:
            return scenario
        
        # Otherwise, add new scenario
        scenario = Scenario(file_hash=hash)

        # Read locations from KML file and add them
        # Assumes KML file with <Placemark><name>LocationName</name></Placemark>
        tree = ET.parse(file_path)
        root = tree.getroot()
        # KML files often have namespaces, so handle that
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        # Find all Placemark names
        for placemark in root.findall('.//kml:Placemark', ns):
            name_elem = placemark.find('kml:name', ns)
            if name_elem is None:
                continue

            name = name_elem.text.strip().lower()

            if placemark.find('kml:Polygon', ns) is not None:
                if name == 'flyzone':
                    continue
                
                scenario.polygons.append(
                    Polygon(name=name, scenario=scenario)
                )
            else:
                assert "origin" in name or "destination" in name, f'Invalid name encountered: "{name}". Expected the name to contain "Origin#" or "Destination#".'
                relative_number = re.search(r'\d+', name)
                assert relative_number is not None, f'Invalid name encountered: "{name}". Expected the name to include a numeric identifier after "Origin" or "Destination".'
                relative_number = int(relative_number.group())
                assert isinstance(relative_number, int), f'Invalid relative number extracted from name: "{name}". Expected a valid integer identifier.'
                
                if "origin" in name:
                    scenario.origins.append(
                        Origin(scenario=scenario, relative_id=relative_number)
                    )
                elif "destination" in name:
                    scenario.destinations.append(
                        Destination(scenario=scenario, relative_id=relative_number)
                    )

        session.add(scenario)

        session.flush()  
        session.commit()
        return scenario



def get_origin(scenario: Scenario, id: int):
    """
    Retrieve an origin by its relative ID within a given scenario.

    Args:
        scenario (Scenario): The scenario to which the origin belongs.
        id (int): The relative ID of the origin.

    Returns:
        Origin: The origin object if found, otherwise None.
    """
    with Session() as session:
        scenario = session.merge(scenario) 
        origin = session.execute(
            select(Origin).where(Origin.relative_id == id, Origin.scenario_id == scenario.id)
        ).scalar_one_or_none()
    return origin

def get_destination(scenario: Scenario, id: int):
    """
    Retrieve a destination by its relative ID within a given scenario.

    Args:
        scenario (Scenario): The scenario to which the destination belongs.
        id (int): The relative ID of the destination.

    Returns:
        Destination: The destination object if found, otherwise None.
    """
    with Session() as session:
        scenario = session.merge(scenario)  
        destination = session.execute(
            select(Destination).where(Destination.relative_id == id, Destination.scenario_id == scenario.id)
        ).scalar_one_or_none()
    return destination

def get_polygons(scenario: Scenario, name: List[str]):
    """
    Retrieve polygons by their names within a given scenario.

    Args:
        scenario (Scenario): The scenario to which the polygons belong.
        name (List[str]): List of polygon names to retrieve.

    Returns:
        List[Polygon]: A list of polygon objects matching the given names.
    """
    with Session() as session:
        scenario = session.merge(scenario)  # Ensure scenario is attached to the session
        polygons = session.execute(
            select(Polygon).where(Polygon.scenario_id == scenario.id, Polygon.name.in_(name))
        ).scalars().all()
    return polygons


def store_output(
        origin: Origin, 
        destination: Destination, 
        polygons: Sequence[Polygon], 
        human_preference: str, 
        feedback: str,
        solution_waypoints: List[List[float]],
        is_valid: bool,
        in_origin: bool,
        in_destination: bool,
        waypoints_outside_flyzone: List[List[float]] = [],
        violated_polygons: List[List[Polygon]] = []
    ):
    """
    Store the output of a scenario solution in the database.

    Args:
        origin (Origin): The origin of the scenario.
        destination (Destination): The destination of the scenario.
        polygons (Sequence[Polygon]): Polygons involved in the scenario.
        human_preference (str): Human preference description.
        feedback (str): Feedback provided for the solution.
        solution_waypoints (List[List[float]]): Waypoints of the solution.
        is_valid (bool): Whether the solution is valid.
        in_origin (bool): Whether the solution starts in the origin.
        in_destination (bool): Whether the solution ends in the destination.
        waypoints_outside_flyzone (List[List[float]], optional): Waypoints outside the flyzone. Defaults to [].
        violated_polygons (List[List[Polygon]], optional): Polygons violated by the solution. Defaults to [].

    Returns:
        ScenarioOutput: The stored feedback object.
    """
    with Session() as session:
        origin = session.merge(origin)
        destination = session.merge(destination)

        # Ensure polygon instances are attached to this session
        polygons = [session.merge(p) for p in polygons]

        assert origin.scenario == destination.scenario, "The origin and destination must belong to the same scenario."
        feedback = ScenarioOutput(
            origin=origin,
            destination=destination,
            polygons=polygons,
            human_preference=human_preference,
            feedback=feedback,
            solution_waypoints=solution_waypoints,
            is_valid=is_valid,
            in_origin=in_origin,
            in_destination=in_destination,
            waypoints_outside_flyzone=waypoints_outside_flyzone,
            violated_polygons=violated_polygons,
        )
        session.add(feedback)

        session.flush()  
        session.commit()
    return feedback

def query_similar_feedback(
    origin: Origin,
    destination: Destination,
    polygons: Sequence[Polygon],
    human_preference: str,
    metric: str = 'cosine_distance',  
    order: Literal['inc', 'dec'] = 'inc',
    threshold: Optional[float] = None,  
    threshold_op: Literal['>=', '<=', '>', '<', '==', '!='] = '>=',  # Operation for threshold comparison
    n: Optional[int] = None
):
    """
    Query similar feedbacks from the database based on the given parameters.

    Args:
        origin (Origin): The origin of the scenario.
        destination (Destination): The destination of the scenario.
        polygons (Sequence[Polygon]): Polygons involved in the scenario.
        human_preference (str): Human preference description.
        metric (str, optional): Metric to calculate similarity (e.g., cosine_distance). Defaults to 'cosine_distance'.
        order (Literal['inc', 'dec'], optional): Sorting order of results ('inc' for ascending, 'dec' for descending). Defaults to 'inc'.
        threshold (Optional[float], optional): Threshold value for filtering results based on similarity. Defaults to None.
        threshold_op (Literal['>=', '<=', '>', '<', '==', '!='], optional): Comparison operator for the threshold. Defaults to '>='.
        n (Optional[int], optional): Maximum number of results to return. If None, returns all matching results. Defaults to None.

    Returns:
        Tuple[List[ScenarioOutput], List[float]]: A tuple containing a list of similar feedbacks and their corresponding distances.
    """
    with Session() as session:
        origin = session.merge(origin)
        destination = session.merge(destination)

        # Ensure polygon instances are attached to this session
        polygons = [session.merge(p) for p in polygons]

        assert origin.scenario == destination.scenario, "The origin and destination must belong to the same scenario."

        embedding = ScenarioOutput.generate_embedding(human_preference)

        try:
            distance_expr = getattr(ScenarioOutput._embedding, metric)(embedding).label("distance")
        except AttributeError:
            raise ValueError(f"Unsupported metric: {metric}. Ensure it is a valid pgvec metric.")

        # Determine the sorting order
        if order == 'inc':
            order_by_clause = distance_expr.asc()
        elif order == 'dec':
            order_by_clause = distance_expr.desc()
        else:
            raise ValueError(f"Unsupported order: {order}. Use 'inc' or 'dec'.")

        # Dynamically construct the threshold filter
        threshold_filter = True  # Default to no filtering
        if threshold is not None:
            threshold_ops = {
                '>=': distance_expr >= threshold,
                '<=': distance_expr <= threshold,
                '>': distance_expr > threshold,
                '<': distance_expr < threshold,
                '==': distance_expr == threshold,
                '!=': distance_expr != threshold
            }
            threshold_filter = threshold_ops.get(threshold_op)
            if threshold_filter is None:
                raise ValueError(f"Unsupported threshold operation: {threshold_op}. Use one of '>=', '<=', '>', '<', '==', '!='.")

        stmt = (
            select(ScenarioOutput, distance_expr)
            .where(
                and_(*[ScenarioOutput.polygons.any(Polygon.id == p.id) for p in polygons]),
                ScenarioOutput.origin == origin,
                ScenarioOutput.destination == destination,
                threshold_filter
            )
            .order_by(order_by_clause)
        ).limit(n)

        # Execute the query and fetch feedbacks with distances
        similar_feedbacks = session.execute(stmt).unique().all()

        # Separate the results into two lists: feedbacks and distances
        feedbacks, distances = zip(*similar_feedbacks) if similar_feedbacks else ([], [])

    return list(feedbacks), list(distances)