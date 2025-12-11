from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, Date, DateTime, DECIMAL, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

# 1. АПТЕКИ
class Pharmacy(Base):
    __tablename__ = "pharmacies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    license_expiry_date = Column(Date, nullable=True) # MF-6
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="pharmacy")
    storage_locations = relationship("StorageLocation", back_populates="pharmacy")
    sales = relationship("Sale", back_populates="pharmacy")

# 2. КОРИСТУВАЧІ
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False) # admin, manager, pharmacist
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pharmacy = relationship("Pharmacy", back_populates="users")
    sales = relationship("Sale", back_populates="seller")
    audit_logs = relationship("AuditLog", back_populates="user")

# 3. МІСЦЯ ЗБЕРІГАННЯ
class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_refrigerated = Column(Boolean, default=False)

    pharmacy = relationship("Pharmacy", back_populates="storage_locations")
    batches = relationship("Batch", back_populates="storage_location")
    iot_device = relationship("IoTDevice", back_populates="storage_location", uselist=False)

# 4. НОМЕНКЛАТУРА ЛІКІВ
class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    manufacturer = Column(String)
    description = Column(Text)
    min_temperature = Column(Float, nullable=False) # IoT поріг
    max_temperature = Column(Float, nullable=False) # IoT поріг
    is_prescription = Column(Boolean, default=False)
    requires_smart_lock = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batches = relationship("Batch", back_populates="medicine")

# 5. ПАРТІЇ (Склад)
class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=False)
    batch_number = Column(String, nullable=False)
    initial_quantity = Column(Integer, nullable=False)
    current_quantity = Column(Integer, nullable=False)
    expiration_date = Column(Date, nullable=False)
    arrival_date = Column(DateTime(timezone=True), server_default=func.now())

    medicine = relationship("Medicine", back_populates="batches")
    storage_location = relationship("StorageLocation", back_populates="batches")
    sale_items = relationship("SaleItem", back_populates="batch")

# 6. IOT ПРИСТРОЇ
class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(Integer, primary_key=True, index=True)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.id"), unique=True, nullable=True)
    serial_number = Column(String, unique=True, nullable=False)
    device_type = Column(String, nullable=False) # sensor, smart_lock
    status = Column(String, default="active")
    last_seen = Column(DateTime(timezone=True))

    storage_location = relationship("StorageLocation", back_populates="iot_device")
    readings = relationship("SensorReading", back_populates="device")
    alerts = relationship("Alert", back_populates="device")

# 7. ПОКАЗНИКИ СЕНСОРІВ
class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)
    temperature = Column(Float)
    humidity = Column(Float)
    battery_level = Column(Integer)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("IoTDevice", back_populates="readings")

# 8. АЛЕРТИ (Тривоги)
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)
    severity = Column(String, nullable=False) # warning, critical
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

    device = relationship("IoTDevice", back_populates="alerts")

# 9. ПРОДАЖІ
class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_amount = Column(DECIMAL(10, 2), default=0.00)
    status = Column(String, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pharmacy = relationship("Pharmacy", back_populates="sales")
    seller = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale")

# 10. ПОЗИЦІЇ ЧЕКА
class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_moment = Column(DECIMAL(10, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    batch = relationship("Batch", back_populates="sale_items")

# 11. АУДИТ
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")