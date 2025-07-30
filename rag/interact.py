from typing import List, Optional, Sequence, Literal, Tuple, Union  # Added Union back for delete_feedback
from sqlalchemy import and_, select, func
from .models import NoFlyZone, Scenario, Origin, Destination, ScenarioOutput
from .db import Session
import hashlib
import xml.etree.ElementTree as ET
import re
import random

 
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
                coordinates_elem = placemark.find('.//kml:coordinates', ns)
                if coordinates_elem is not None:
                    coordinates_text = coordinates_elem.text.strip()
                    # Parse coordinates (assumes format: lon,lat,alt lon,lat,alt ...)
                    coords_lonlat = [
                        tuple(map(float, c.split(',')[:2]))          # (lon, lat)
                        for c in coordinates_text.split()
                    ]
                    if name == 'flyzone':
                        scenario.fly_zone_bounds_lonlat = coords_lonlat
                    else:
                        scenario.no_fly_zones.append(
                            NoFlyZone(name=name, scenario=scenario, bounds_lonlat=coords_lonlat)
                        )
            else:
                assert "origin" in name or "destination" in name, f'Invalid name encountered: "{name}". Expected the name to contain "Origin#" or "Destination#".'
                relative_number = re.search(r'\d+', name)
                assert relative_number is not None, f'Invalid name encountered: "{name}". Expected the name to include a numeric identifier after "Origin" or "Destination".'
                relative_number = int(relative_number.group())
                assert isinstance(relative_number, int), f'Invalid relative number extracted from name: "{name}". Expected a valid integer identifier.'
                
                coordinates_elem = placemark.find('.//kml:coordinates', ns)
                assert coordinates_elem is not None, f'Missing coordinates for {name}.'
                coordinates_text = coordinates_elem.text.strip()
                lonlat = tuple(map(float, coordinates_text.split(',')[:2]))  # Extract (lon, lat)

                if "origin" in name:
                    scenario.origins.append(
                        Origin(scenario=scenario, relative_id=relative_number, lonlat=lonlat)
                    )
                elif "destination" in name:
                    scenario.destinations.append(
                        Destination(scenario=scenario, relative_id=relative_number, lonlat=lonlat)
                    )

        session.add(scenario)

        session.commit()
        session.refresh(scenario)
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

def get_no_fly_zones(scenario: Scenario, names: List[str]):
    """
    Retrieve no-fly zones by their names within a given scenario.

    Args:
        scenario (Scenario): The scenario to which the no-fly zones belong.
        name (List[str]): List of no-fly zone names to retrieve.

    Returns:
        List[NoFlyZone]: A list of no-fly zone objects matching the given names.
    """
    names = [name.lower() for name in names]

    with Session() as session:
        scenario = session.merge(scenario)  # Ensure scenario is attached to the session
        no_fly_zones = session.execute(
            select(NoFlyZone).where(NoFlyZone.scenario_id == scenario.id, NoFlyZone.name.in_(names))
        ).scalars().all()
    return no_fly_zones


def store_output(
        origin: Origin, 
        destination: Destination, 
        no_fly_zones: Sequence[NoFlyZone], 
        human_preference: str, 
        feedback: str,
        solution_waypoints: List[Tuple[float, float]],
    ):
    """
    Store the output of a scenario solution in the database.

    Args:
        origin (Origin): The origin of the scenario.
        destination (Destination): The destination of the scenario.
        no_fly_zones (Sequence[NoFlyZone]): No-fly zones involved in the scenario.
        human_preference (str): Human preference description.
        feedback (str): Feedback provided for the solution.
        solution_waypoints (List[Tuple[float, float]]): Waypoints of the solution, formatted as a list of [lon, lat] pairs.

    Returns:
        ScenarioOutput: The stored feedback object.
    """
    with Session() as session:
        origin = session.merge(origin)
        destination = session.merge(destination)

        no_fly_zones = [session.merge(zone) for zone in no_fly_zones]

        assert origin.scenario == destination.scenario, "The origin and destination must belong to the same scenario."
        feedback = ScenarioOutput(
            origin=origin,
            destination=destination,
            no_fly_zones=no_fly_zones,
            human_preference=human_preference,
            feedback=feedback,
            solution_waypoints=solution_waypoints
        )
        session.add(feedback)

        session.commit()
        session.refresh(feedback)
    return feedback




def query_similar_feedback(
    origin: Origin,
    destination: Destination,
    no_fly_zones: Sequence[NoFlyZone],
    human_preference: str,
    metric: str = 'cosine_distance',  
    order: Literal['inc', 'dec'] = 'inc',
    threshold: Optional[float] = None,  
    threshold_op: Literal['>=', '<=', '>', '<', '==', '!='] = '>=',  
    filter_by_validity: Optional[bool] = None, 
    n: Optional[int] = None
):
    """
    Query similar feedbacks from the database based on the given parameters.

    Args:
        origin (Origin): The origin of the scenario.
        destination (Destination): The destination of the scenario.
        no_fly_zones (Sequence[NoFlyZone]): No-fly zones involved in the scenario.
        human_preference (str): Human preference description.
        metric (str, optional): Metric to calculate similarity (e.g., cosine_distance). Defaults to 'cosine_distance'.
        order (Literal['inc', 'dec'], optional): Sorting order of results ('inc' for ascending, 'dec' for descending). Defaults to 'inc'.
        threshold (Optional[float], optional): Threshold value for filtering results based on similarity. Defaults to None.
        threshold_op (Literal['>=', '<=', '>', '<', '==', '!='], optional): Comparison operator for the threshold. Defaults to '>='.
        filter_by_validity (Optional[bool], optional): Filter results based on validity. Defaults to None.
        n (Optional[int], optional): Maximum number of results to return. If None, returns all matching results. Defaults to None.

    Returns:
        Tuple[List[ScenarioOutput], List[float]]: A tuple containing a list of similar feedbacks and their corresponding distances.
    """
    with Session() as session:
        origin = session.merge(origin)
        destination = session.merge(destination)

        no_fly_zones = [session.merge(zone) for zone in no_fly_zones]

        assert origin.scenario == destination.scenario, "The origin and destination must belong to the same scenario."

        embedding = ScenarioOutput.generate_embedding(human_preference)

        try:
            distance_expr = getattr(ScenarioOutput._embedding, metric)(embedding).label("distance")
        except AttributeError:
            raise ValueError(f"Unsupported metric: {metric}. Ensure it is a valid pgvec metric.")

        if order == 'inc':
            order_by_clause = distance_expr.asc()
        elif order == 'dec':
            order_by_clause = distance_expr.desc()
        else:
            raise ValueError(f"Unsupported order: {order}. Use 'inc' or 'dec'.")

        threshold_filter = True  
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

        validity_filter = True
        if filter_by_validity is not None:
            validity_filter = ScenarioOutput.is_valid == filter_by_validity

        stmt = (
            select(ScenarioOutput, distance_expr)
            .where(
                and_(*[ScenarioOutput.no_fly_zones.any(NoFlyZone.id == zone.id) for zone in no_fly_zones]),
                ScenarioOutput.origin == origin,
                ScenarioOutput.destination == destination,
                threshold_filter,
                validity_filter
            )
            .order_by(order_by_clause)
        ).limit(n)

        similar_feedbacks = session.execute(stmt).unique().all()

        feedbacks, distances = zip(*similar_feedbacks) if similar_feedbacks else ([], [])

    return list(feedbacks), list(distances)


def query_similar_feedback_without_preference(
    origin: Origin,
    destination: Destination,
    no_fly_zones: Sequence[NoFlyZone],
    filter_by_validity: Optional[bool] = None,
    n: Optional[int] = None,
    shuffle: bool = True
):
    """
    Query similar feedbacks from the database based only on the given origin, destination, and no-fly zones.
    Does not use embedding-based similarity or human preference matching.
    The returned results are randomly shuffled by default.

    Args:
        origin (Origin): The origin of the scenario.
        destination (Destination): The destination of the scenario.
        no_fly_zones (Sequence[NoFlyZone]): No-fly zones involved in the scenario.
        filter_by_validity (Optional[bool], optional): Filter results based on validity. Defaults to None.
        n (Optional[int], optional): Maximum number of results to return. If None, returns all matching results. Defaults to None.
        shuffle (bool, optional): Whether to shuffle the results randomly. Defaults to True.

    Returns:
        List[ScenarioOutput]: A list of similar feedbacks matching the parameters (no embedding similarity), optionally shuffled.
    """
    with Session() as session:
        origin = session.merge(origin)
        destination = session.merge(destination)
        no_fly_zones = [session.merge(zone) for zone in no_fly_zones]
        assert origin.scenario == destination.scenario, "The origin and destination must belong to the same scenario."

        validity_filter = True
        if filter_by_validity is not None:
            validity_filter = ScenarioOutput.is_valid == filter_by_validity

        stmt = (
            select(ScenarioOutput)
            .where(
                and_(*[ScenarioOutput.no_fly_zones.any(NoFlyZone.id == zone.id) for zone in no_fly_zones]),
                ScenarioOutput.origin == origin,
                ScenarioOutput.destination == destination,
                validity_filter
            )
        )
        if shuffle:
            stmt = stmt.order_by(func.random())
        stmt = stmt.limit(n)

        similar_feedbacks = session.execute(stmt).scalars().unique().all()
    return similar_feedbacks


def query_latest_feedback(n):
    """
    Query the latest n ScenarioOutput records from the database.
    
    Args:
        n (int): Number of latest records to return.
        shuffle (bool, optional): Whether to shuffle the results randomly. Defaults to False.
    
    Returns:
        List[ScenarioOutput]: A list of the latest ScenarioOutput records.
    """
    with Session() as session:
        stmt = select(ScenarioOutput)
        
        stmt = stmt.order_by(ScenarioOutput.id.desc())
        stmt = stmt.limit(n)
        
        latest_feedbacks = session.execute(stmt).scalars().unique().all()
    return latest_feedbacks


def delete_feedback(feedback: Union[int, ScenarioOutput]) -> bool:
    """
    Delete a feedback record from the database.
    
    Args:
        feedback (Union[int, ScenarioOutput]): Either the ID of the ScenarioOutput record 
                                              or the ScenarioOutput object itself to delete.
        
    Returns:
        bool: True if the feedback was successfully deleted, False if not found.
    """
    with Session() as session:
        # Always get the ID and fetch fresh from the current session
        feedback_id = feedback.id if isinstance(feedback, ScenarioOutput) else feedback
        
        # Query for the feedback record in the current session
        obj = session.execute(
            select(ScenarioOutput).where(ScenarioOutput.id == feedback_id)
        ).unique().scalar_one_or_none()
        
        if obj is None:
            return False
            
        # Delete the feedback record
        session.delete(obj)
        session.commit()
        
        return True
        