from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base


engine = create_engine("postgresql+psycopg://postgres:@localhost:5432/rag")

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


