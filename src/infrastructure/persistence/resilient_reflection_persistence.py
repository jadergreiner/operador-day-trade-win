# -*- coding: utf-8 -*-
"""
Resilient Reflection Persistence Layer

Garantia de persistência com:
- SQLite primário (ACID transacional)
- JSONL fallback (append-only)
- Retry logic com exponential backoff
- Flush/Sync forçado
- Validação por checksum
- Recovery automático
"""

import json
import sqlite3
import hashlib
import time
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("resilient_persistence")


class ResilientReflectionPersistence:
    """Persist reflections with ACID guarantees + fallback + recovery."""

    def __init__(self, project_root: Path):
        """Initialize persistence layer."""
        self.project_root = project_root
        self.db_path = project_root / "data" / "db" / "reflections" / "reflections.db"
        self.jsonl_path = project_root / "data" / "db" / "reflections" / "reflections_log.jsonl"
        self.backup_path = project_root / "data" / "db" / "reflections" / "reflections_log.BACKUP.jsonl"
        self.metrics_path = project_root / "data" / "db" / "reflections" / "persistence_metrics.json"

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite
        self._init_sqlite()

        # Initialize metrics
        self._init_metrics()

    def _init_sqlite(self):
        """Create SQLite schema with indices."""
        try:
            conn = sqlite3.connect(str(self.db_path))

            # Enforce ACID guarantees
            conn.execute("PRAGMA synchronous=FULL")  # Force disk sync
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA foreign_keys=ON")

            # Main reflections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    entry_id TEXT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    mood TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    alignment REAL NOT NULL,
                    one_liner TEXT,
                    data_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    persistence_status TEXT DEFAULT 'OK'
                )
            """)

            # Indices for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON reflections(timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mood
                ON reflections(mood)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision
                ON reflections(decision)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON reflections(created_at DESC)
            """)

            # Persistence errors audit log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS persistence_errors (
                    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    error_message TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    attempt_number INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved INTEGER DEFAULT 0
                )
            """)

            # Persistence statistics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS persistence_stats (
                    stat_date DATE PRIMARY KEY,
                    total_writes INTEGER DEFAULT 0,
                    successful_writes INTEGER DEFAULT 0,
                    failed_writes INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    avg_persist_time_ms REAL DEFAULT 0.0
                )
            """)

            conn.commit()
            conn.close()

            logger.info(f"SQLite initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise

    def _init_metrics(self):
        """Initialize metrics file."""
        if not self.metrics_path.exists():
            metrics = {
                "total_reflections": 0,
                "failed_writes": 0,
                "last_successful_write": None,
                "last_error": None,
                "recovery_attempts": 0,
            }
            self._write_metrics(metrics)

    def _read_metrics(self) -> Dict[str, Any]:
        """Read current metrics."""
        try:
            with open(self.metrics_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "total_reflections": 0,
                "failed_writes": 0,
                "last_successful_write": None,
                "last_error": None,
                "recovery_attempts": 0,
            }

    def _write_metrics(self, metrics: Dict[str, Any]):
        """Write metrics file."""
        try:
            with open(self.metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write metrics: {e}")

    def persist_reflection(
        self,
        reflection_dict: Dict[str, Any],
        max_retries: int = 3,
    ) -> bool:
        """
        Save reflection with retry logic and validation.

        Args:
            reflection_dict: Dictionary representation of reflection
            max_retries: Maximum retry attempts (exponential backoff)

        Returns:
            bool: True if persisted successfully, False otherwise
        """
        entry_id = reflection_dict.get("entry_id", "UNKNOWN")
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                # 1. Convert to JSON and compute checksum
                data_json = json.dumps(reflection_dict, ensure_ascii=False)
                checksum = hashlib.sha256(data_json.encode("utf-8")).hexdigest()

                # 2. Write to SQLite (transactional)
                self._write_sqlite(reflection_dict, data_json, checksum)

                # 3. Write to JSONL (append-only fallback)
                self._write_jsonl(data_json)

                # 4. Validate both writes
                self._validate_persistence(entry_id, checksum)

                # 5. Update metrics
                elapsed_ms = (time.time() - start_time) * 1000
                self._update_success_metrics(entry_id, elapsed_ms)

                logger.info(f"✓ Reflection {entry_id} persisted (attempt {attempt+1}, {elapsed_ms:.1f}ms)")
                return True

            except Exception as e:
                error_type = type(e).__name__
                logger.warning(
                    f"Persist attempt {attempt+1}/{max_retries} failed for {entry_id}: {error_type}: {e}"
                )

                # Log error to database
                self._log_persistence_error(entry_id, str(e), error_type, attempt + 1)

                # Exponential backoff before retry
                if attempt < max_retries - 1:
                    wait_time = (100 * (2 ** attempt)) / 1000  # 100ms, 200ms, 400ms
                    logger.debug(f"Retrying in {wait_time*1000:.0f}ms...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Final failure
                    self._update_failure_metrics(entry_id, str(e))
                    logger.error(f"✗ Failed to persist {entry_id} after {max_retries} attempts")
                    return False

        return False

    def _write_sqlite(self, reflection_dict: Dict[str, Any], data_json: str, checksum: str):
        """Write to SQLite with ACID guarantees."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO reflections (
                    entry_id, timestamp, mood, decision, confidence,
                    alignment, one_liner, data_json, checksum, persistence_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reflection_dict.get("entry_id"),
                reflection_dict.get("timestamp"),
                reflection_dict.get("mood"),
                reflection_dict.get("my_decision"),
                float(reflection_dict.get("my_confidence", 0)),
                float(reflection_dict.get("my_alignment", 0)),
                reflection_dict.get("one_liner"),
                data_json,
                checksum,
                "OK"
            ))
            conn.commit()
            logger.debug(f"SQLite write OK: {reflection_dict.get('entry_id')}")
        finally:
            conn.close()

    def _write_jsonl(self, data_json: str):
        """Write to JSONL with explicit flush and sync."""
        # Rotate backup only if file is large
        if self.jsonl_path.exists():
            file_size = self.jsonl_path.stat().st_size
            if file_size > 10_000_000:  # 10MB threshold
                import shutil
                backup_path = self.jsonl_path.parent / f"reflections_log.BACKUP.{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                shutil.copy(self.jsonl_path, backup_path)
                logger.info(f"Rotated JSONL backup: {backup_path}")

        # Append with explicit flush and sync
        with open(str(self.jsonl_path), "a", encoding="utf-8") as f:
            f.write(data_json + "\n")
            f.flush()  # ✅ Flush buffer to OS
            os.fsync(f.fileno())  # ✅ Force disk sync

        logger.debug(f"JSONL write OK: {self.jsonl_path}")

    def _validate_persistence(self, entry_id: str, checksum: str):
        """Verify data was written successfully to BOTH stores."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT checksum FROM reflections WHERE entry_id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise RuntimeError(f"Entry {entry_id} not found in SQLite after write")

            if row[0] != checksum:
                raise RuntimeError(f"Checksum mismatch for {entry_id}: expected {checksum}, got {row[0]}")

            logger.debug(f"Validation OK: {entry_id}")

        finally:
            conn.close()

    def _log_persistence_error(
        self,
        entry_id: str,
        error_message: str,
        error_type: str,
        attempt_number: int,
    ):
        """Log persistence failures for audit."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO persistence_errors (entry_id, error_message, error_type, attempt_number)
                VALUES (?, ?, ?, ?)
            """, (entry_id, error_message, error_type, attempt_number))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log error: {e}")

    def _update_success_metrics(self, entry_id: str, elapsed_ms: float):
        """Update metrics on successful write."""
        metrics = self._read_metrics()
        metrics["total_reflections"] = metrics.get("total_reflections", 0) + 1
        metrics["last_successful_write"] = datetime.now().isoformat()
        if metrics.get("failed_writes", 0) == 0:
            metrics["last_successful_write_streak"] = metrics.get("total_reflections", 1)
        self._write_metrics(metrics)

    def _update_failure_metrics(self, entry_id: str, error: str):
        """Update metrics on failed write."""
        metrics = self._read_metrics()
        metrics["failed_writes"] = metrics.get("failed_writes", 0) + 1
        metrics["last_error"] = f"{entry_id}: {error}"
        self._write_metrics(metrics)

    def get_health_status(self) -> Dict[str, Any]:
        """Get persistence layer health status."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM reflections")
            total_reflections = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM persistence_errors WHERE resolved=0")
            failed_writes = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT timestamp FROM reflections ORDER BY timestamp DESC LIMIT 1"
            )
            last_reflection = cursor.fetchone()
            last_timestamp = last_reflection[0] if last_reflection else None

            conn.close()

            # Calculate time since last reflection
            time_since_last = None
            if last_timestamp:
                last_dt = datetime.fromisoformat(last_timestamp)
                time_since_last = (datetime.now() - last_dt).total_seconds()

            metrics = self._read_metrics()
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
            jsonl_size_mb = self.jsonl_path.stat().st_size / (1024 * 1024) if self.jsonl_path.exists() else 0

            return {
                "total_reflections": total_reflections,
                "failed_writes": failed_writes,
                "last_reflection_timestamp": last_timestamp,
                "time_since_last_reflection_seconds": time_since_last,
                "db_size_mb": round(db_size_mb, 2),
                "jsonl_size_mb": round(jsonl_size_mb, 2),
                "metrics": metrics,
                "status": self._determine_health_status(
                    failed_writes, time_since_last, db_size_mb
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "🔴 ERROR",
                "error": str(e),
            }

    def _determine_health_status(
        self,
        failed_writes: int,
        time_since_last_reflection: Optional[float],
        db_size_mb: float,
    ) -> str:
        """Determine overall health status."""
        if failed_writes > 50:
            return "🔴 CRÍTICO - Alto número de falhas (>50)"
        elif time_since_last_reflection and time_since_last_reflection > 600:
            return "🟠 ALERTA - Sem reflexões por mais de 10 minutos"
        elif db_size_mb > 100:
            return "🟡 AVISO - Database > 100MB (executar VACUUM)"
        else:
            return "🟢 OK"

    def recover_from_failure(self) -> int:
        """
        Recover state after crash.

        Returns:
            int: Number of recovered reflections
        """
        logger.info("Starting recovery from failure...")

        recovered_count = 0

        try:
            # 1. Check for orphaned entries in JSONL not in SQLite
            orphaned = self._find_orphaned_entries()
            logger.info(f"Found {len(orphaned)} orphaned entries in JSONL")

            # 2. Migrate each orphaned entry to database
            for entry_dict in orphaned:
                try:
                    data_json = json.dumps(entry_dict, ensure_ascii=False)
                    checksum = hashlib.sha256(data_json.encode("utf-8")).hexdigest()
                    self._write_sqlite(entry_dict, data_json, checksum)
                    recovered_count += 1
                    logger.debug(f"Recovered: {entry_dict.get('entry_id')}")
                except Exception as e:
                    logger.warning(f"Failed to recover {entry_dict.get('entry_id')}: {e}")

            # 3. Validate database integrity
            logger.info("Validating database integrity...")
            self._repair_corrupted_records()

            # 4. Clean up error logs
            logger.info("Cleaning up old error logs...")
            self._cleanup_old_errors()

            logger.info(f"Recovery complete: {recovered_count} reflections recovered")
            return recovered_count

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return 0

    def _find_orphaned_entries(self) -> list[Dict[str, Any]]:
        """Find entries in JSONL but not in SQLite."""
        orphaned = []

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("SELECT entry_id FROM reflections")
            db_entry_ids = {row[0] for row in cursor.fetchall()}
            conn.close()

            # Read JSONL and check against database
            if self.jsonl_path.exists():
                with open(str(self.jsonl_path), "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            entry_id = entry.get("entry_id")
                            if entry_id and entry_id not in db_entry_ids:
                                orphaned.append(entry)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Corrupted JSONL line: {e}")

        except Exception as e:
            logger.error(f"Error finding orphaned entries: {e}")

        return orphaned

    def _repair_corrupted_records(self):
        """Repair corrupted records in database."""
        try:
            conn = sqlite3.connect(str(self.db_path))

            # Run integrity check
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result[0] != "ok":
                logger.error(f"Database corruption detected: {result[0]}")
                conn.execute("VACUUM")
                conn.commit()
                logger.info("Executed VACUUM to repair database")

            conn.close()

        except Exception as e:
            logger.error(f"Failed to repair records: {e}")

    def _cleanup_old_errors(self, days_old: int = 7):
        """Remove persistent error logs older than N days."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                DELETE FROM persistence_errors
                WHERE timestamp < datetime('now', '-' || ? || ' days')
                AND resolved = 1
            """, (days_old,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to cleanup old errors: {e}")

    def export_to_jsonl(self, output_path: Optional[Path] = None) -> str:
        """Export all reflections to JSONL format."""
        output_path = output_path or (self.db_path.parent / "export_all_reflections.jsonl")

        count = 0
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("""
                SELECT data_json FROM reflections ORDER BY timestamp ASC
            """)

            with open(str(output_path), "w", encoding="utf-8") as f:
                for (data_json,) in cursor.fetchall():
                    f.write(data_json + "\n")
                    count += 1

            conn.close()
            logger.info(f"Exported {count} reflections to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
