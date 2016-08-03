from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.sql import not_
import db


Base = declarative_base()

class CurrentSpawns(Base):
    __tablename__ = 'vCurrentSpawns'

    id = Column(Integer, primary_key=True)
    pokemon_id = Column(Integer)
    spawn_id = Column(String(32))
    expire_timestamp = Column(Integer)
    normalized_timestamp = Column(Integer)
    lat = Column(String(16))
    lon = Column(String(16))
    minsRemaining = Column(Float)

def getCurrentSpawns(session,pokemon_id=None):
    query = session.query(CurrentSpawns)
    if pokemon_id is not None:
        query = query.filter(CurrentSpawns.pokemon_id == pokemon_id)
    return query.all()