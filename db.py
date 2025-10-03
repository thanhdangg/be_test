"""
Database Module for Access Process Backend
Handles storage and retrieval of tag data including last CNT and timestamp
"""

import sqlite3
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TagDatabase:
    def __init__(self, db_path: str = "tags.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create registered_tags table for tag registration
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS registered_tags (
                        id TEXT PRIMARY KEY,
                        description TEXT NOT NULL,
                        registered_at TEXT NOT NULL
                    )
                """)
                
                # Create tags table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tags (
                        tag_id TEXT PRIMARY KEY,
                        last_cnt INTEGER NOT NULL,
                        last_timestamp TEXT NOT NULL,
                        first_seen TEXT NOT NULL,
                        total_updates INTEGER DEFAULT 1,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (tag_id) REFERENCES registered_tags (id)
                    )
                """)
                
                # Create tag_history table for audit trail
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tag_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tag_id TEXT NOT NULL,
                        cnt INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL,
                        FOREIGN KEY (tag_id) REFERENCES tags (tag_id)
                    )
                """)
                
                # Create index for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tag_history_tag_id 
                    ON tag_history (tag_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tag_history_received_at 
                    ON tag_history (received_at)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def register_tag(self, tag_id: str, description: str) -> bool:
        """
        Register a new tag
        
        Args:
            tag_id: Tag identifier
            description: Tag description
            
        Returns:
            bool: True if registration successful, False if tag already exists
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    registered_at = datetime.now().isoformat()
                    
                    # Check if tag already exists
                    cursor.execute(
                        "SELECT id FROM registered_tags WHERE id = ?",
                        (tag_id,)
                    )
                    
                    if cursor.fetchone():
                        logger.warning(f"Tag {tag_id} is already registered")
                        return False
                    
                    cursor.execute("""
                        INSERT INTO registered_tags (id, description, registered_at)
                        VALUES (?, ?, ?)
                    """, (tag_id, description, registered_at))
                    
                    conn.commit()
                    logger.info(f"Tag {tag_id} registered successfully: {description}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to register tag: {e}")
                return False
    
    def is_tag_registered(self, tag_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM registered_tags WHERE id = ?",
                    (tag_id,)
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check tag registration: {e}")
            return False
    
    def get_registered_tags(self) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        rt.id,
                        rt.description,
                        rt.registered_at,
                        t.last_cnt,
                        t.last_timestamp,
                        t.total_updates
                    FROM registered_tags rt
                    LEFT JOIN tags t ON rt.id = t.tag_id
                    ORDER BY rt.registered_at DESC
                """)
                
                results = cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "description": row[1],
                        "registered_at": row[2],
                        "last_cnt": row[3] if row[3] is not None else None,
                        "last_seen": row[4] if row[4] is not None else None,
                        "total_updates": row[5] if row[5] is not None else 0,
                        "status": "active" if row[3] is not None else "registered"
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to get registered tags: {e}")
            return []
    
    def get_registered_tag_status(self, tag_id: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        rt.id,
                        rt.description,
                        rt.registered_at,
                        t.last_cnt,
                        t.last_timestamp,
                        t.total_updates
                    FROM registered_tags rt
                    LEFT JOIN tags t ON rt.id = t.tag_id
                    WHERE rt.id = ?
                """, (tag_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "description": result[1],
                        "registered_at": result[2],
                        "last_cnt": result[3] if result[3] is not None else None,
                        "last_seen": result[4] if result[4] is not None else None,
                        "total_updates": result[5] if result[5] is not None else 0,
                        "status": "active" if result[3] is not None else "registered"
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get registered tag status: {e}")
            return None
    
    def store_tag_data(self, tag_id: str, cnt: int, timestamp: str) -> bool:
        """
        Store or update tag data - only for registered tags
        
        Args:
            tag_id: Tag identifier
            cnt: Counter value
            timestamp: Tag timestamp
            
        Returns:
            bool: True if CNT changed (new update), False if same CNT or tag not registered
        """
        with self.lock:
            try:
                # Check if tag is registered
                if not self.is_tag_registered(tag_id):
                    logger.warning(f"Tag {tag_id} is not registered - ignoring data")
                    return False
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    received_at = datetime.now().isoformat()
                    
                    # Check if tag exists and get last CNT
                    cursor.execute(
                        "SELECT last_cnt, total_updates FROM tags WHERE tag_id = ?",
                        (tag_id,)
                    )
                    result = cursor.fetchone()
                    
                    cnt_changed = True
                    
                    if result:
                        last_cnt, total_updates = result
                        cnt_changed = (cnt != last_cnt)
                        
                        if cnt_changed:
                            cursor.execute("""
                                UPDATE tags 
                                SET last_cnt = ?, last_timestamp = ?, 
                                    total_updates = total_updates + 1
                                WHERE tag_id = ?
                            """, (cnt, timestamp, tag_id))
                        else:
                            logger.debug(f"CNT unchanged for tag {tag_id}: {cnt}")
                            
                    else:
                        cursor.execute("""
                            INSERT INTO tags 
                            (tag_id, last_cnt, last_timestamp, first_seen, 
                             total_updates, created_at)
                            VALUES (?, ?, ?, ?, 1, ?)
                        """, (tag_id, cnt, timestamp, timestamp, received_at))
                        
                        logger.info(f"First data received for registered tag: {tag_id}")
                    
                    # Insert into history for audit trail
                    cursor.execute("""
                        INSERT INTO tag_history 
                        (tag_id, cnt, timestamp, received_at)
                        VALUES (?, ?, ?, ?)
                    """, (tag_id, cnt, timestamp, received_at))
                    
                    conn.commit()
                    
                    if cnt_changed:
                        logger.info(f"Tag {tag_id}: CNT updated to {cnt} at {timestamp}")
                    
                    return cnt_changed
                    
            except Exception as e:
                logger.error(f"Failed to store tag data: {e}")
                return False
    
    def get_tag_data(self, tag_id: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tag_id, last_cnt, last_timestamp, first_seen, 
                           total_updates, created_at
                    FROM tags WHERE tag_id = ?
                """, (tag_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "tag_id": result[0],
                        "last_cnt": result[1],
                        "last_timestamp": result[2],
                        "first_seen": result[3],
                        "total_updates": result[4],
                        "created_at": result[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tag data: {e}")
            return None
    
    def get_all_tags(self) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tag_id, last_cnt, last_timestamp, first_seen, 
                           total_updates, created_at
                    FROM tags ORDER BY created_at DESC
                """)
                
                results = cursor.fetchall()
                return [
                    {
                        "tag_id": row[0],
                        "last_cnt": row[1],
                        "last_timestamp": row[2],
                        "first_seen": row[3],
                        "total_updates": row[4],
                        "created_at": row[5]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to get all tags: {e}")
            return []
    
    def get_tag_history(self, tag_id: str, limit: int = 100) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT cnt, timestamp, received_at
                    FROM tag_history 
                    WHERE tag_id = ?
                    ORDER BY received_at DESC
                    LIMIT ?
                """, (tag_id, limit))
                
                results = cursor.fetchall()
                return [
                    {
                        "cnt": row[0],
                        "timestamp": row[1],
                        "received_at": row[2]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to get tag history: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Database connections closed")


_db_instance = None
_db_lock = threading.Lock()

def get_database(db_path: str = "tags.db") -> TagDatabase:
    """
    Get singleton database instance
    
    Args:
        db_path: Path to database file
        
    Returns:
        TagDatabase instance
    """
    global _db_instance
    
    with _db_lock:
        if _db_instance is None:
            _db_instance = TagDatabase(db_path)
        return _db_instance


if __name__ == "__main__":
    # Test the database module
    db = TagDatabase("test_tags.db")
    
    # Test data
    test_data = [
        ("fa451f0755d8", 197, "20251003140059.456"),
        ("ab123c4567ef", 42, "20251003140105.123"),
        ("cd789e0123fg", 88, "20251003140112.789"),
        ("fa451f0755d8", 198, "20251003140120.456"),  
        ("fa451f0755d8", 198, "20251003140125.456"),  
    ]
    
    print("Testing database operations...")
    
    for tag_id, cnt, timestamp in test_data:
        cnt_changed = db.store_tag_data(tag_id, cnt, timestamp)
        print(f"Stored {tag_id}: CNT={cnt}, Changed={cnt_changed}")
    
    print("\nAll tags:")
    for tag in db.get_all_tags():
        print(f"  {tag}")    
    
    print("\nHistory for fa451f0755d8:")
    history = db.get_tag_history("fa451f0755d8")
    for record in history:
        print(f"  {record}")
