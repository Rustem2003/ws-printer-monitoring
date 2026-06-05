from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class TokenRefreshRequest(BaseModel):
    token: str


# --- User ---
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role_id: int


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role_id: int
    is_active: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Role ---
class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    model_config = {"from_attributes": True}


# --- Printer ---
class PrinterCreate(BaseModel):
    name: str
    ip_address: str
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    snmp_version: str = "2c"
    snmp_community: str = "public"
    snmp_port: int = 161


class PrinterUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    snmp_version: Optional[str] = None
    snmp_community: Optional[str] = None
    snmp_port: Optional[int] = None


class PrinterResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    mac_address: Optional[str]
    vendor: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    firmware_version: Optional[str]
    location: Optional[str]
    is_color: bool
    is_online: bool
    snmp_version: str = "2c"
    snmp_community: str = "public"
    snmp_port: int = 161
    last_seen: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Consumable ---
class ConsumableResponse(BaseModel):
    id: int
    name: str
    current_level: Optional[float]
    max_capacity: Optional[int]
    threshold_warning: float
    threshold_critical: float
    unit: str
    last_updated: Optional[datetime]

    model_config = {"from_attributes": True}


# --- Printer Status ---
class PrinterStatusResponse(BaseModel):
    id: int
    printer_id: int
    status_code: Optional[int]
    status_text: Optional[str]
    page_count: Optional[int]
    error_code: Optional[str]
    error_message: Optional[str]
    recorded_at: datetime

    model_config = {"from_attributes": True}


# --- Events ---
class PrinterEventResponse(BaseModel):
    id: int
    printer_id: int
    event_type: str
    severity: str
    message: Optional[str]
    acknowledged: int
    created_at: datetime
    printer_name: Optional[str] = None
    printer_ip: Optional[str] = None
    printer_location: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Scan ---
class ScanStartRequest(BaseModel):
    subnet: Optional[str] = None
    method: Optional[str] = "snmp_broadcast"


class ScanJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    subnet: Optional[str]
    method: str
    devices_found: int
    devices_added: int
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# --- Statistics ---
class StatisticsResponse(BaseModel):
    total_printers: int
    online_printers: int
    offline_printers: int
    total_events_today: int
    critical_events: int
    low_toner_count: int


class ConsumableStatisticsResponse(BaseModel):
    printer_name: str
    consumable_name: str
    current_level: float
    threshold_warning: float
    threshold_critical: float


# --- Audit ---
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Generic ---
class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
