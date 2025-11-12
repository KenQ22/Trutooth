"""SQLAlchemy database models for persistent storage.

Integrated from fork: provides database persistence for devices and connection history
alongside the existing CSV-based metrics logging.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy
else:
    try:
        from flask_sqlalchemy import SQLAlchemy
    except ImportError:
        # Stub if Flask-SQLAlchemy not installed
        SQLAlchemy = None  # type: ignore


def init_db_models(db: "SQLAlchemy") -> tuple:
    """Initialize and return database model classes.
    
    Args:
        db: Flask-SQLAlchemy instance
        
    Returns:
        Tuple of (BluetoothDeviceDB, ConnectionRecordDB) model classes
    """
    
    class BluetoothDeviceDB(db.Model):  # type: ignore
        """Database model for Bluetooth devices."""
        __tablename__ = "bluetooth_devices"
        
        id = db.Column(db.Integer, primary_key=True)
        device_name = db.Column(db.String(255), nullable=False)
        device_address = db.Column(db.String(255), nullable=False, unique=True)
        connection_status = db.Column(db.Boolean, default=False, nullable=False)
        
        # Relationship to connection records
        connection_history = db.relationship(
            "ConnectionRecordDB",
            backref="device",
            lazy=True,
            cascade="all, delete-orphan"
        )
        
        def connect(self) -> None:
            """Mark device as connected."""
            self.connection_status = True
        
        def disconnect(self) -> None:
            """Mark device as disconnected."""
            self.connection_status = False
        
        def to_dict(self) -> dict:
            """Convert to dictionary representation."""
            return {
                "id": self.id,
                "device_name": self.device_name,
                "device_address": self.device_address,
                "connection_status": self.connection_status,
            }
        
        def __repr__(self) -> str:
            return f"<BluetoothDeviceDB {self.device_name} ({self.device_address})>"
    
    
    class ConnectionRecordDB(db.Model):  # type: ignore
        """Database model for connection history records."""
        __tablename__ = "connection_records"
        
        id = db.Column(db.Integer, primary_key=True)
        device_id = db.Column(
            db.Integer,
            db.ForeignKey("bluetooth_devices.id"),
            nullable=False
        )
        timestamp = db.Column(
            db.DateTime(timezone=True),
            default=datetime.utcnow,
            nullable=False,
        )
        status = db.Column(db.String(50), nullable=False)
        
        def to_dict(self) -> dict:
            """Convert to dictionary representation."""
            return {
                "id": self.id,
                "device_id": self.device_id,
                "device_name": self.device.device_name if self.device else None,
                "timestamp": self.timestamp.isoformat(),
                "status": self.status,
            }
        
        def __repr__(self) -> str:
            return f"<ConnectionRecordDB {self.status} at {self.timestamp}>"
    
    return BluetoothDeviceDB, ConnectionRecordDB


__all__ = ["init_db_models"]
