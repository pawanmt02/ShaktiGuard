import sqlite3
import json
from typing import List, Optional, Dict, Any
from app.config import settings
from app.models import Contact, EmergencySession, TimelineEvent, NotificationRecord

def get_connection():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Contacts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        relationship TEXT,
        tier INTEGER DEFAULT 1,
        notify_sms INTEGER DEFAULT 1,
        notify_email INTEGER DEFAULT 1,
        notify_call INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    
    # Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        trigger_source TEXT,
        raw_input TEXT,
        location_json TEXT,
        understanding_json TEXT,
        plan_json TEXT,
        battery_level INTEGER,
        is_covert INTEGER DEFAULT 0,
        active_tier INTEGER DEFAULT 1,
        cancellation_reason TEXT,
        resolution_notes TEXT
    )
    """)
    
    # Timeline events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timeline_events (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        relative_seconds REAL DEFAULT 0.0,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        details TEXT NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)
    
    # Notifications log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT,
        recipient_email TEXT,
        channel TEXT NOT NULL,
        message TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        status TEXT NOT NULL,
        acknowledged_at TEXT,
        response_note TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)
    
    conn.commit()
    
    # Pre-seed default emergency contacts if none exist
    cursor.execute("SELECT COUNT(*) as count FROM contacts")
    if cursor.fetchone()["count"] == 0:
        default_contacts = [
            Contact(
                name="Ananya Sharma",
                phone="+91 98765 43210",
                email="ananya.sharma@example.com",
                relationship="Mother",
                tier=1,
                notify_sms=True,
                notify_email=True,
                notify_call=True
            ),
            Contact(
                name="Rohan Verma",
                phone="+91 98111 22334",
                email="rohan.verma@example.com",
                relationship="Brother",
                tier=1,
                notify_sms=True,
                notify_email=True,
                notify_call=False
            ),
            Contact(
                name="Vikram Malhotra",
                phone="+91 97222 33445",
                email="vikram.m@example.com",
                relationship="Close Friend / Roommate",
                tier=2,
                notify_sms=True,
                notify_email=True,
                notify_call=False
            ),
            Contact(
                name="National Emergency Response Support System (ERSS)",
                phone="112",
                email="controlroom@police.gov.in",
                relationship="Police & Dispatch Dispatcher",
                tier=3,
                notify_sms=True,
                notify_email=False,
                notify_call=True
            )
        ]
        for c in default_contacts:
            cursor.execute("""
            INSERT INTO contacts (id, name, phone, email, relationship, tier, notify_sms, notify_email, notify_call, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c.id, c.name, c.phone, c.email, c.relationship, c.tier, int(c.notify_sms), int(c.notify_email), int(c.notify_call), c.created_at))
        conn.commit()
        
    conn.close()

# Contacts Repository
def get_all_contacts() -> List[Contact]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts ORDER BY tier ASC, name ASC")
    rows = cursor.fetchall()
    contacts = [
        Contact(
            id=r["id"],
            name=r["name"],
            phone=r["phone"],
            email=r["email"],
            relationship=r["relationship"],
            tier=r["tier"],
            notify_sms=bool(r["notify_sms"]),
            notify_email=bool(r["notify_email"]),
            notify_call=bool(r["notify_call"]),
            created_at=r["created_at"]
        ) for r in rows
    ]
    conn.close()
    return contacts

def get_contact_by_id(contact_id: str) -> Optional[Contact]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    return Contact(
        id=r["id"],
        name=r["name"],
        phone=r["phone"],
        email=r["email"],
        relationship=r["relationship"],
        tier=r["tier"],
        notify_sms=bool(r["notify_sms"]),
        notify_email=bool(r["notify_email"]),
        notify_call=bool(r["notify_call"]),
        created_at=r["created_at"]
    )

def save_contact(c: Contact) -> Contact:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO contacts (id, name, phone, email, relationship, tier, notify_sms, notify_email, notify_call, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        phone=excluded.phone,
        email=excluded.email,
        relationship=excluded.relationship,
        tier=excluded.tier,
        notify_sms=excluded.notify_sms,
        notify_email=excluded.notify_email,
        notify_call=excluded.notify_call
    """, (c.id, c.name, c.phone, c.email, c.relationship, c.tier, int(c.notify_sms), int(c.notify_email), int(c.notify_call), c.created_at))
    conn.commit()
    conn.close()
    return c

def delete_contact(contact_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# Sessions Repository
def save_session(session: EmergencySession) -> EmergencySession:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sessions (
        id, status, created_at, updated_at, trigger_source, raw_input,
        location_json, understanding_json, plan_json, battery_level, is_covert,
        active_tier, cancellation_reason, resolution_notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status=excluded.status,
        updated_at=excluded.updated_at,
        trigger_source=excluded.trigger_source,
        raw_input=excluded.raw_input,
        location_json=excluded.location_json,
        understanding_json=excluded.understanding_json,
        plan_json=excluded.plan_json,
        battery_level=excluded.battery_level,
        is_covert=excluded.is_covert,
        active_tier=excluded.active_tier,
        cancellation_reason=excluded.cancellation_reason,
        resolution_notes=excluded.resolution_notes
    """, (
        session.id,
        session.status.value if hasattr(session.status, "value") else str(session.status),
        session.created_at,
        session.updated_at,
        session.trigger_source,
        session.raw_input,
        session.location.model_dump_json() if session.location else None,
        session.understanding.model_dump_json() if session.understanding else None,
        session.plan.model_dump_json() if session.plan else None,
        session.battery_level,
        int(session.is_covert),
        session.active_tier,
        session.cancellation_reason,
        session.resolution_notes
    ))
    conn.commit()
    conn.close()
    return session

def get_session(session_id: str) -> Optional[EmergencySession]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    
    loc = json.loads(r["location_json"]) if r["location_json"] else None
    und = json.loads(r["understanding_json"]) if r["understanding_json"] else None
    pln = json.loads(r["plan_json"]) if r["plan_json"] else None
    
    return EmergencySession(
        id=r["id"],
        status=r["status"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        trigger_source=r["trigger_source"],
        raw_input=r["raw_input"] or "",
        location=loc,
        understanding=und,
        plan=pln,
        battery_level=r["battery_level"],
        is_covert=bool(r["is_covert"]),
        active_tier=r["active_tier"],
        cancellation_reason=r["cancellation_reason"],
        resolution_notes=r["resolution_notes"]
    )

def get_all_sessions(limit: int = 50) -> List[EmergencySession]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        loc = json.loads(r["location_json"]) if r["location_json"] else None
        und = json.loads(r["understanding_json"]) if r["understanding_json"] else None
        pln = json.loads(r["plan_json"]) if r["plan_json"] else None
        results.append(EmergencySession(
            id=r["id"],
            status=r["status"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            trigger_source=r["trigger_source"],
            raw_input=r["raw_input"] or "",
            location=loc,
            understanding=und,
            plan=pln,
            battery_level=r["battery_level"],
            is_covert=bool(r["is_covert"]),
            active_tier=r["active_tier"],
            cancellation_reason=r["cancellation_reason"],
            resolution_notes=r["resolution_notes"]
        ))
    return results

# Timeline Events Repository
def add_timeline_event(event: TimelineEvent) -> TimelineEvent:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO timeline_events (id, session_id, timestamp, relative_seconds, event_type, title, details, metadata_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.id,
        event.session_id,
        event.timestamp,
        event.relative_seconds,
        event.event_type,
        event.title,
        event.details,
        json.dumps(event.metadata) if event.metadata else "{}"
    ))
    conn.commit()
    conn.close()
    return event

def get_timeline_events(session_id: str) -> List[TimelineEvent]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM timeline_events WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        TimelineEvent(
            id=r["id"],
            session_id=r["session_id"],
            timestamp=r["timestamp"],
            relative_seconds=r["relative_seconds"],
            event_type=r["event_type"],
            title=r["title"],
            details=r["details"],
            metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {}
        ) for r in rows
    ]

# Notifications Repository
def add_notification(n: NotificationRecord) -> NotificationRecord:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO notifications (
        id, session_id, recipient_id, recipient_name, recipient_phone,
        recipient_email, channel, message, sent_at, status, acknowledged_at, response_note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status=excluded.status,
        acknowledged_at=excluded.acknowledged_at,
        response_note=excluded.response_note
    """, (
        n.id, n.session_id, n.recipient_id, n.recipient_name, n.recipient_phone,
        n.recipient_email, n.channel, n.message, n.sent_at, n.status,
        n.acknowledged_at, n.response_note
    ))
    conn.commit()
    conn.close()
    return n

def get_notifications(session_id: str) -> List[NotificationRecord]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE session_id = ? ORDER BY sent_at ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        NotificationRecord(
            id=r["id"],
            session_id=r["session_id"],
            recipient_id=r["recipient_id"],
            recipient_name=r["recipient_name"],
            recipient_phone=r["recipient_phone"],
            recipient_email=r["recipient_email"],
            channel=r["channel"],
            message=r["message"],
            sent_at=r["sent_at"],
            status=r["status"],
            acknowledged_at=r["acknowledged_at"],
            response_note=r["response_note"]
        ) for r in rows
    ]

def get_recent_notifications(limit: int = 30) -> List[NotificationRecord]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications ORDER BY sent_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        NotificationRecord(
            id=r["id"],
            session_id=r["session_id"],
            recipient_id=r["recipient_id"],
            recipient_name=r["recipient_name"],
            recipient_phone=r["recipient_phone"],
            recipient_email=r["recipient_email"],
            channel=r["channel"],
            message=r["message"],
            sent_at=r["sent_at"],
            status=r["status"],
            acknowledged_at=r["acknowledged_at"],
            response_note=r["response_note"]
        ) for r in rows
    ]
