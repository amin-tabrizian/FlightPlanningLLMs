from typing import List, Tuple
import requests # type: ignore
from sqlalchemy.orm import declarative_base, mapped_column, relationship, Mapped
from sqlalchemy import Boolean, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from pgvector.sqlalchemy import Vector # type: ignore
import shapely # type: ignore
from utils import haversine_distance
from functools import cached_property

Base = declarative_base()

TOLERANCE = 1e-3


class Scenario(Base):
    """
    Represents a flight planning scenario.

    Attributes:
        id (int): Unique identifier for the scenario.
        file_hash (str): Hash of the scenario file for uniqueness.
        no_fly_zones (list[NoFlyZone]): List of no-fly zones associated with the scenario.
        origins (list[Origin]): List of origin points in the scenario.
        destinations (list[Destination]): List of destination points in the scenario.
        fly_zone_bounds_lonlat (List[Tuple[float, float]]): Coordinates defining the fly zone boundary.
    """

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_hash: Mapped[str] = mapped_column(Text, unique=True)

    no_fly_zones: Mapped[list["NoFlyZone"]] = relationship("NoFlyZone", back_populates="scenario", cascade="all, delete-orphan")
    origins: Mapped[list["Origin"]] = relationship("Origin", back_populates="scenario", cascade="all, delete-orphan")
    destinations: Mapped[list["Destination"]] = relationship("Destination", back_populates="scenario", cascade="all, delete-orphan")
    fly_zone_bounds_lonlat: Mapped[List[Tuple[float, float]]] = mapped_column(JSON, nullable=False) 

    @property
    def flyzone_bounds(self):
        """
        Returns the fly zone boundary as a Shapely Polygon.

        Returns:
            shapely.Polygon: The fly zone boundary.
        """
        return shapely.Polygon(self.fly_zone_bounds_lonlat)


class NoFlyZone(Base):
    """
    Represents a no-fly zone within a scenario.

    Attributes:
        id (int): Unique identifier for the no-fly zone.
        scenario_id (int): ID of the associated scenario.
        name (str): Name of the no-fly zone.
        bounds_lonlat (List[Tuple[float, float]]): Coordinates defining the no-fly zone boundary.
    """

    __tablename__ = "no_fly_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    name: Mapped[str] = mapped_column(Text)
    bounds_lonlat: Mapped[List[Tuple[float, float]]] = mapped_column(JSON, nullable=False)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="no_fly_zones")
    selections: Mapped[list["SelectedNoFlyZone"]] = relationship("SelectedNoFlyZone", back_populates="no_fly_zone")

    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        secondary="selected_no_fly_zones",
        back_populates="no_fly_zones",
        overlaps="selections"
    )

    @property
    def bounds(self):
        """
        Returns the no-fly zone boundary as a Shapely Polygon.

        Returns:
            shapely.Polygon: The no-fly zone boundary.
        """
        return shapely.Polygon(self.bounds_lonlat)


class ScenarioOutput(Base):
    """
    Represents the output of a scenario solution.

    Attributes:
        id (int): Unique identifier for the scenario output.
        origin_id (int): ID of the origin point.
        destination_id (int): ID of the destination point.
        _embedding (list[float]): Embedding vector for the human preference.
        _human_preference (str): Human preference description.
        feedback (str): Feedback provided for the solution.
        solution_waypoints (List[Tuple[float, float]]): Waypoints of the solution.
    """

    __tablename__ = "scenario_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    origin_id: Mapped[int] = mapped_column(Integer, ForeignKey("origins.id"))
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"))

    _embedding: Mapped[list[float]] = mapped_column("embedding", Vector(1024))
    _human_preference: Mapped[str] = mapped_column("human_preference", Text)
    feedback: Mapped[str] = mapped_column(Text)

    @property
    def solution_waypoints(self) -> List[Tuple[float, float]]:
        return self._solution_waypoints

    @solution_waypoints.setter
    def solution_waypoints(self, value: List[Tuple[float, float]]) -> None:
        self._solution_waypoints = value
        self._is_valid = self.in_origin and self.in_destination and self.in_flyzone and self.has_valid_segments

    _solution_waypoints: Mapped[List[Tuple[float, float]]] = mapped_column("solution_waypoints", JSON, nullable=False)
    is_valid: Mapped[bool] = mapped_column("is_valid", Boolean, nullable=False, server_default="false") # cache for querying 



    @property
    def in_flyzone(self):
        """
        Checks if the flight path is within the fly zone.

        Returns:
            bool: True if the flight path is within the fly zone, False otherwise.
        """
        return len(self.waypoints_outside_flyzone) == 0

    @cached_property
    def waypoints_outside_flyzone(self) -> list[Tuple[float]]:
        """
        Returns a list of waypoints that are outside the flyzone.
        """
        flyzone = self.origin.scenario.flyzone_bounds
        return [waypoint for waypoint in self.solution_waypoints if not shapely.Point(waypoint).within(flyzone)]

    @property
    def has_valid_segments(self):
        """
        Checks if the flight path has valid segments.

        Returns:
            bool: True if all flight segments are valid, False otherwise.
        """
        return len(self.violating_segments) == 0



    @cached_property
    def _segment_violations(self):
        """
        Helper method to identify violating segments and violated no-fly zones.
        Returns a tuple of (violating_segments, violated_no_fly_zones).
        """
        violating_segments = []
        violated_zones = set()

        for i in range(len(self.solution_waypoints) - 1):
            segment = shapely.LineString([
                self.solution_waypoints[i],
                self.solution_waypoints[i + 1]
            ])

            for zone in self.no_fly_zones:
                if segment.intersects(zone.bounds):
                    violating_segments.append((
                        self.solution_waypoints[i], self.solution_waypoints[i + 1]
                    ))
                    violated_zones.add(zone.name)

        return violating_segments, list(violated_zones)

    @property
    def violating_segments(self) -> list[List[Tuple[Tuple[float, float], Tuple[float, float]]]]:
        """
        Returns a list of violating flight segments based on the selected no-fly zones.
        """
        return self._segment_violations[0]

    @property
    def violated_no_fly_zones(self) -> list[str]:
        """
        Returns a list of names of no-fly zones that are violated by the flight segments.
        """
        return self._segment_violations[1]

    @property
    def in_origin(self):
        """
        Checks if the first waypoint is within the origin point.

        Returns:
            bool: True if the first waypoint is within the origin, False otherwise.
        """
        origin_error = haversine_distance(self.solution_waypoints[0], self.origin.lonlat)
        return origin_error <= TOLERANCE

    @property
    def in_destination(self):
        """
        Checks if the last waypoint is within the destination point.

        Returns:
            bool: True if the last waypoint is within the destination, False otherwise.
        """
        destination_error = haversine_distance(self.solution_waypoints[-1], self.destination.lonlat)
        return destination_error <= TOLERANCE

    no_fly_zones: Mapped[list["NoFlyZone"]] = relationship(
        "NoFlyZone",
        secondary="selected_no_fly_zones",
        back_populates="scenario_outputs",
        lazy="joined",
        overlaps="selections"
    )

    @property
    def no_fly_zone_names(self):
        """
        Returns a list of names of the no-fly zones associated with the scenario output.

        Returns:
            list[str]: List of no-fly zone names.
        """
        return [zone.name for zone in self.no_fly_zones]

    origin: Mapped["Origin"] = relationship(
        "Origin",
        back_populates="scenario_outputs",
        lazy="joined"
    )
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="scenario_outputs",
        lazy="joined"
    )

    selected_polygon_links: Mapped[list["SelectedNoFlyZone"]] = relationship(
        "SelectedNoFlyZone",
        back_populates="scenario_output",
        lazy="joined",
        overlaps="no_fly_zones,scenario_outputs"
    )

    @property
    def human_preference(self) -> str:
        """
        Gets the human preference description.

        Returns:
            str: The human preference description.
        """
        return self._human_preference

    @human_preference.setter
    def human_preference(self, value: str) -> None:
        """
        Sets the human preference description and generates the corresponding embedding.

        Args:
            value (str): The human preference description.
        """
        self._human_preference = value
        self._embedding = self.generate_embedding(value)

    @property
    def embedding(self) -> list[float]:
        """
        Gets the embedding vector for the human preference.

        Returns:
            list[float]: The embedding vector.
        """
        return self._embedding

    @staticmethod
    def generate_embedding(value: str) -> list[float]:
        """
        Generates an embedding vector for the given human preference description.

        Args:
            value (str): The human preference description.

        Returns:
            list[float]: The generated embedding vector.
        """
        url = 'http://localhost:11434/api/embeddings'
        payload = {
            "model": 'mxbai-embed-large',
            "prompt": value
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['embedding']



class Origin(Base):
    """
    Represents an origin point within a scenario.

    Attributes:
        id (int): Unique identifier for the origin.
        scenario_id (int): ID of the associated scenario.
        relative_id (int): Relative ID of the origin within the scenario.
        lonlat (Tuple[float, float]): Coordinates of the origin point.
    """

    __tablename__ = "origins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    relative_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lonlat: Mapped[Tuple[float, float]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("scenario_id", "relative_id"),
    )

    @property
    def point(self):
        """
        Returns the origin point as a Shapely Point.

        Returns:
            shapely.Point: The origin point.
        """
        return shapely.Point(self.lonlat)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="origins")
    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        back_populates="origin",
        cascade="all, delete-orphan"
    )


class Destination(Base):
    """
    Represents a destination point within a scenario.

    Attributes:
        id (int): Unique identifier for the destination.
        scenario_id (int): ID of the associated scenario.
        relative_id (int): Relative ID of the destination within the scenario.
        lonlat (Tuple[float, float]): Coordinates of the destination point.
    """

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    relative_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lonlat: Mapped[Tuple[float, float]] = mapped_column(JSON, nullable=False)

    @property
    def point(self):
        """
        Returns the destination point as a Shapely Point.

        Returns:
            shapely.Point: The destination point.
        """
        return shapely.Point(self.lonlat)

    __table_args__ = (
        UniqueConstraint("scenario_id", "relative_id"),
    )

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="destinations")
    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        back_populates="destination",
        cascade="all, delete-orphan"
    )


class SelectedNoFlyZone(Base):
    """
    Represents a selected no-fly zone for a scenario output.

    Attributes:
        id (int): Unique identifier for the selected no-fly zone.
        no_fly_zone_id (int): ID of the associated no-fly zone.
        scenario_output_id (int): ID of the associated scenario output.
    """

    __tablename__ = "selected_no_fly_zones"

    id = mapped_column(Integer, primary_key=True)
    
    no_fly_zone_id = mapped_column(Integer, ForeignKey("no_fly_zones.id"), nullable=False)
    scenario_output_id = mapped_column(Integer, ForeignKey("scenario_outputs.id"), nullable=False)

    no_fly_zone: Mapped["NoFlyZone"] = relationship(
        "NoFlyZone",
        back_populates="selections",
        overlaps="no_fly_zones,scenario_outputs"
    )
    scenario_output: Mapped["ScenarioOutput"] = relationship(
        "ScenarioOutput",
        back_populates="selected_polygon_links",
        overlaps="no_fly_zones,scenario_outputs"
    )