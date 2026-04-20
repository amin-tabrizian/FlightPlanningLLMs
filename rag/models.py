import requests # type: ignore
from typing import Optional
from sqlalchemy.orm import declarative_base, mapped_column, relationship, Mapped
from sqlalchemy import Boolean, Integer, Text, ForeignKey, UniqueConstraint
from pgvector.sqlalchemy import Vector # type: ignore

Base = declarative_base()

class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_hash: Mapped[str] = mapped_column(Text, unique=True)

    polygons: Mapped[list["Polygon"]] = relationship("Polygon", back_populates="scenario", cascade="all, delete-orphan")
    origins: Mapped[list["Origin"]] = relationship("Origin", back_populates="scenario", cascade="all, delete-orphan")
    destinations: Mapped[list["Destination"]] = relationship("Destination", back_populates="scenario", cascade="all, delete-orphan")


class Polygon(Base):
    __tablename__ = "polygons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    name: Mapped[str] = mapped_column(Text)

    # Add a relationship to Scenario
    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="polygons")

    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        secondary="selected_polygons",
        back_populates="polygons"
    )


class ScenarioOutput(Base):
    __tablename__ = "scenario_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    origin_id: Mapped[int] = mapped_column(Integer, ForeignKey("origins.id"))
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"))

    _embedding: Mapped[list[float]] = mapped_column("embedding", Vector(1024))
    _human_preference: Mapped[str] = mapped_column("human_preference", Text)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    has_review: Mapped[bool] = mapped_column(Boolean, default=False)

    solution_waypoints: Mapped[list[list[float]]] = mapped_column(Text, default=lambda: [])
    waypoints_outside_flyzone: Mapped[Optional[list[list[float]]]] = mapped_column(Text, nullable=True, default=None)

    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)
    in_origin: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)
    in_destination: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)

    
    violated_polygons: Mapped[list["Polygon"]] = relationship(
        "Polygon",
        secondary="violated_polygons",
        lazy="joined"
    )
    polygons: Mapped[list["Polygon"]] = relationship(
        "Polygon",
        secondary="selected_polygons",
        back_populates="scenario_outputs",
        lazy="joined"
    )

    @property
    def polygon_names(self):
        return [polygon.name for polygon in self.polygons]
    
    @property
    def violated_polygon_names(self):
        return [polygon.name for polygon in self.violated_polygons]

    origin = relationship(
        "Origin",
        back_populates="scenario_outputs",
        lazy="joined"
    )
    destination = relationship(
        "Destination",
        back_populates="scenario_outputs",
        lazy="joined"
    )
   
    @property
    def human_preference(self) -> str:
        return self._human_preference

    @human_preference.setter
    def human_preference(self, value: str) -> None:
        self._human_preference = value
        self._embedding = self.generate_embedding(value)

    @property
    def embedding(self) -> list[float]:
        return self._embedding
    

    @staticmethod
    def generate_embedding(value: str) -> list[float]:
        url = 'http://localhost:11434/api/embeddings'
        payload = {
            "model": 'mxbai-embed-large',
            "prompt": value
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['embedding']


    @staticmethod
    def validate_same_scenario(session, origin_id: int, destination_id: int) -> None:
        """
        Raises ValueError if the origin and destination locations are not in the same scenario.
        """
        from .models import Location
        origin = session.query(Location).filter_by(id=origin_id).first()
        destination = session.query(Location).filter_by(id=destination_id).first()
        if not origin or not destination:
            raise ValueError("Origin or destination location does not exist.")
        if origin.scenario_id != destination.scenario_id:
            raise ValueError("Origin and destination must be in the same scenario.")



class Origin(Base):
    __tablename__ = "origins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    relative_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Add a UniqueConstraint to ensure relative_id is unique within a scenario
    __table_args__ = (
        UniqueConstraint("scenario_id", "relative_id"),
    )

    # Relationships
    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="origins")
    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        back_populates="origin",
        cascade="all, delete-orphan"
    )


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    relative_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Add a UniqueConstraint to ensure relative_id is unique within a scenario
    __table_args__ = (
        UniqueConstraint("scenario_id", "relative_id"),
    )

    # Relationships
    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="destinations")
    scenario_outputs: Mapped[list["ScenarioOutput"]] = relationship(
        "ScenarioOutput",
        back_populates="destination",
        cascade="all, delete-orphan"
    )



class SelectedPolygon(Base):
    __tablename__ = "selected_polygons"

    id = mapped_column(Integer, primary_key=True)
    
    polygon_id = mapped_column(Integer, ForeignKey("polygons.id"), nullable=False)
    scenario_output_id = mapped_column(Integer, ForeignKey("scenario_outputs.id"), nullable=False)



class ViolatedPolygon(Base):
    __tablename__ = "violated_polygons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_output_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenario_outputs.id"))
    polygon_id: Mapped[int] = mapped_column(Integer, ForeignKey("polygons.id"))