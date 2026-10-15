"""DATA-001: minimal provenance and user-owned derived records, not a market archive."""
import uuid
from sqlalchemy import create_engine, Column, String, Text, Boolean, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from .core import settings, now

Base = declarative_base()
def uid():
    return str(uuid.uuid4())
class User(Base):
    __tablename__='users'
    id=Column(String, primary_key=True, default=uid)
    email=Column(String, unique=True, nullable=False)
    password_hash=Column(Text, nullable=False)
    role=Column(String, nullable=False, default='researcher')
    active=Column(Boolean, default=True)
    created_at=Column(DateTime(timezone=True), default=now)
class Run(Base):
    __tablename__='research_runs'
    id=Column(String, primary_key=True, default=uid)
    owner_id=Column(String, ForeignKey('users.id'), nullable=False)
    params=Column(JSON, nullable=False)
    state=Column(String, default='pending')
    result=Column(JSON)
    created_at=Column(DateTime(timezone=True), default=now)
    completed_at=Column(DateTime(timezone=True))
class Registry(Base):
    __tablename__='tool_registry'
    id=Column(String, primary_key=True)
    service=Column(String, nullable=False)
    method=Column(String, nullable=False)
    schema_hash=Column(String, nullable=False)
    input_schema=Column(JSON, nullable=False)
    capability=Column(String)
    enabled=Column(Boolean, default=False)
    validated_at=Column(DateTime(timezone=True), default=now)
    reviewed_config=Column(JSON)
class Invocation(Base):
    __tablename__='tool_invocations'
    id=Column(String, primary_key=True, default=uid)
    run_id=Column(String)
    service=Column(String)
    method=Column(String)
    schema_hash=Column(String)
    duration_ms=Column(Integer)
    status=Column(String)
    error_code=Column(String)
    evidence_ref=Column(String)
    source_as_of=Column(String)
    timestamp=Column(DateTime(timezone=True), default=now)
class Observation(Base):
    __tablename__='market_observations'
    id=Column(String, primary_key=True)
    run_id=Column(String, ForeignKey('research_runs.id'))
    lineage=Column(JSON)
    source_as_of=Column(String)
    fetched_at=Column(String)
class Metric(Base):
    __tablename__='calculated_metrics'
    id=Column(String, primary_key=True, default=uid)
    run_id=Column(String, ForeignKey('research_runs.id'))
    name=Column(String)
    value=Column(JSON)
    formula_version=Column(String)
    input_ids=Column(JSON)
class Report(Base):
    __tablename__='reports'
    id=Column(String, primary_key=True, default=uid)
    run_id=Column(String, ForeignKey('research_runs.id'))
    owner_id=Column(String, ForeignKey('users.id'))
    shared_with=Column(JSON, default=list)
    annotations=Column(JSON, default=list)
    generated_at=Column(DateTime(timezone=True), default=now)
    retention_until=Column(DateTime(timezone=True))
class Audit(Base):
    __tablename__='audit_events'
    id=Column(String, primary_key=True, default=uid)
    actor_id=Column(String)
    action=Column(String)
    entity_id=Column(String)
    status=Column(String)
    timestamp=Column(DateTime(timezone=True), default=now)

engine=create_engine(settings.database_url, connect_args={'check_same_thread':False} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
Session=sessionmaker(bind=engine, expire_on_commit=False)
def get_db():
    with Session() as db:
        yield db
