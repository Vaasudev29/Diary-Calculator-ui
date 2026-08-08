from __future__ import annotations

from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()


class Preset(Base):
    __tablename__ = 'presets'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    type = Column(String(100))
    payload = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class SQLStore:
    def __init__(self, db_path: Optional[Path] = None):
        dbfile = db_path or Path('data') / 'app.db'
        dbfile.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f'sqlite:///{dbfile}', connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_preset(self, name: str, payload: dict):
        s = self.Session()
        p = s.query(Preset).filter_by(name=name).first()
        if p:
            p.payload = json.dumps(payload)
        else:
            p = Preset(name=name, payload=json.dumps(payload))
            s.add(p)
        s.commit()
        s.close()

    def list_presets(self):
        s = self.Session()
        items = s.query(Preset).all()
        s.close()
        return [json.loads(i.payload) for i in items]

    def append_history(self, record: dict):
        s = self.Session()
        h = History(type=record.get('type'), payload=json.dumps(record))
        s.add(h)
        s.commit()
        s.close()
