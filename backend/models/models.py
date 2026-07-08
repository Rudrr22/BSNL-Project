# models.py — Database table definitions
# Each class = one table in PostgreSQL

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class LogEntry(Base):
    """
    Stores every log line received from simulator or uploaded file
    
    Table: log_entries
    """
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Log details
    timestamp = Column(String, nullable=False)
    severity = Column(String, nullable=False)    # CRITICAL/WARNING/INFO
    component = Column(String, nullable=False)   # BTS_042, Router_7
    region = Column(String, nullable=True)       # Jaipur, Delhi
    event_type = Column(String, nullable=True)   # Signal_Drop, Handover_Failed
    metric = Column(String, nullable=True)       # RSSI, Latency_ms
    value = Column(Float, nullable=True)         # -95, 340
    raw = Column(Text, nullable=False)           # full raw log line
    
    # Source tracking
    source = Column(String, default="live")      # "live" or "upload"
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    
    # When we received it
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationship to anomalies
    anomalies = relationship("Anomaly", back_populates="log_entry")


class Analysis(Base):
    """
    Stores each analysis session (one per uploaded file or daily summary)
    
    Table: analyses
    """
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    
    # File info
    filename = Column(String, nullable=True)     # uploaded filename
    source = Column(String, default="upload")    # "upload" or "live"
    
    # Log counts
    total_logs = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    
    # AI Generated content
    summary = Column(Text, nullable=True)        # AI summary
    recommendations = Column(Text, nullable=True) # AI recommendations
    
    # Status
    status = Column(String, default="processing") # processing/complete/failed
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    anomalies = relationship("Anomaly", back_populates="analysis")


class Anomaly(Base):
    """
    Stores each anomaly detected by AI agents
    
    Table: anomalies
    """
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    log_entry_id = Column(Integer, ForeignKey("log_entries.id"), nullable=True)
    
    # Anomaly details
    severity = Column(String, nullable=False)       # CRITICAL/WARNING
    component = Column(String, nullable=False)      # which tower/router
    region = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    
    # AI Generated explanations
    description = Column(Text, nullable=True)       # what happened
    root_cause = Column(Text, nullable=True)        # why it happened
    suggested_action = Column(Text, nullable=True)  # what to do
    
    # Status
    acknowledged = Column(Boolean, default=False)   # engineer acknowledged?
    
    # Timestamps
    detected_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    analysis = relationship("Analysis", back_populates="anomalies")
    log_entry = relationship("LogEntry", back_populates="anomalies")