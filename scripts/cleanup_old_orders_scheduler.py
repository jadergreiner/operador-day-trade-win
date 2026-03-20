#!/usr/bin/env python3
"""
Cleanup Scheduler for Old Orders
Remove ordens antigas (>7 dias) automaticamente

Testa:
1. Identifica ordens antigas
2. Remove com segurança (backup antes)
3. Valida integridade após cleanup
4. Gera relatório

Usage:
    python cleanup_old_orders_scheduler.py --dry-run
    python cleanup_old_orders_scheduler.py --days 7 --backup
    python cleanup_old_orders_scheduler.py --help
"""

import argparse
import json
import logging
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class OrderCleanupScheduler:
    """Gerencia limpeza de ordens antigas no SQLite"""

    def __init__(self, db_path: str = "data/db/trading.db"):
        self.db_path = Path(db_path)
        self.stats = {
            "orders_found": 0,
            "orders_deleted": 0,
            "backup_created": False,
            "db_size_before_bytes": None,
            "db_size_after_bytes": None,
            "errors": [],
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão SQLite"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        conn.row_factory = sqlite3.Row
        return conn

    def _get_db_size(self) -> int:
        try:
            return self.db_path.stat().st_size
        except Exception:
            return 0

    def find_old_orders(self, days: int = 7) -> List[Dict]:
        """Encontra ordens mais antigas que N dias"""

        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Prioriza tabela 'order_queue' com executed_at e status final
            cursor.execute("""
                SELECT id, symbol, volume as quantity, status, executed_at
                FROM order_queue
                WHERE status IN ('EXECUTED', 'FAILED')
                AND datetime(executed_at) < datetime(?)
                ORDER BY executed_at ASC
            """, (cutoff_iso,))

            old_orders = [dict(row) for row in cursor.fetchall()]
            self.stats["orders_found"] = len(old_orders)

            logger.info(f"✓ Found {len(old_orders)} orders older than {days} days")
            return old_orders

        except sqlite3.OperationalError as e:
            # Tabela 'order_queue' pode nao existir, tenta 'orders'
            logger.warning("Table 'order_queue' not found, trying 'orders'...")
            try:
                cursor.execute("""
                    SELECT id, symbol, quantity, status, created_at
                    FROM orders
                    WHERE created_at < ?
                    ORDER BY created_at ASC
                """, (cutoff_iso,))

                old_orders = [dict(row) for row in cursor.fetchall()]
                self.stats["orders_found"] = len(old_orders)

                logger.info(
                    f"✓ Found {len(old_orders)} orders older than {days} days"
                )
                return old_orders

            except sqlite3.OperationalError:
                try:
                    cursor.execute("""
                        SELECT id, symbol, quantity, status, created_at
                        FROM orders
                        WHERE created_at < ?
                        ORDER BY created_at ASC
                    """, (cutoff_iso,))

                    old_orders = [dict(row) for row in cursor.fetchall()]
                    self.stats["orders_found"] = len(old_orders)

                    logger.info(
                        f"✓ Found {len(old_orders)} orders older than {days} days"
                    )
                    return old_orders
                except sqlite3.OperationalError:
                    logger.error("Neither 'order_queue' nor 'orders' table exists")
                self.stats["errors"].append(
                    "Database schema incompatible - no orders table"
                )
                return []

        finally:
            conn.close()

    def create_backup(self) -> Path:
        """Cria backup do database antes de deletar"""

        backup_dir = Path("data/db/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"trading_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✓ Backup created: {backup_path}")
            self.stats["backup_created"] = True
            return backup_path

        except Exception as e:
            error_msg = f"Failed to create backup: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            raise

    def delete_old_orders(self, days: int = 7, create_backup: bool = True) -> bool:
        """Delete ordens antigas (com backup opcional)"""

        logger.info("-" * 60)
        logger.info("Starting Cleanup Process...")
        logger.info("-" * 60)

        # Encontra ordens antigas
        old_orders = self.find_old_orders(days)

        if not old_orders:
            logger.info("✓ No old orders found - nothing to cleanup")
            return True

        # Cria backup
        if create_backup:
            try:
                self.create_backup()
            except Exception as e:
                logger.error(f"Backup failed - aborting cleanup: {e}")
                return False

        with sqlite_write_lock(self.db_path):
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_iso = cutoff_date.isoformat()

                # Delete from 'order_queue' if exists
                try:
                    cursor.execute(
                        """
                        DELETE FROM order_queue
                        WHERE status IN ('EXECUTED', 'FAILED')
                        AND datetime(executed_at) < datetime(?)
                        """,
                        (cutoff_iso,)
                    )
                    deleted = cursor.rowcount
                    self.stats["orders_deleted"] = deleted
                    logger.info(f"✓ Deleted {deleted} orders from 'order_queue' table")

                except sqlite3.OperationalError:
                    # Try 'orders' table
                    try:
                        cursor.execute(
                            "DELETE FROM orders WHERE created_at < ?",
                            (cutoff_iso,)
                        )
                        deleted = cursor.rowcount
                        self.stats["orders_deleted"] = deleted
                        logger.info(
                            f"✓ Deleted {deleted} orders from 'orders' table"
                        )

                    except sqlite3.OperationalError:
                        error_msg = "Failed to delete orders - table not found"
                        logger.error(error_msg)
                        self.stats["errors"].append(error_msg)
                        return False

                # Commit
                conn.commit()
                logger.info("✓ Changes committed")

                # Vacuum (compacta database)
                cursor.execute("VACUUM")
                logger.info("✓ Database vacuumed")

                return True

            except Exception as e:
                logger.error(f"Error during deletion: {e}")
                conn.rollback()
                self.stats["errors"].append(str(e))
                return False

            finally:
                conn.close()

    def validate_integrity(self) -> bool:
        """Valida integridade do database após cleanup"""

        logger.info("-" * 60)
        logger.info("Validating Database Integrity...")
        logger.info("-" * 60)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Pragma integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result[0] == "ok":
                logger.info("✓ Integrity check passed")
                return True
            else:
                logger.error(f"✗ Integrity check failed: {result[0]}")
                self.stats["errors"].append(f"Integrity check failed: {result[0]}")
                return False

        except Exception as e:
            logger.error(f"Error validating integrity: {e}")
            self.stats["errors"].append(str(e))
            return False

        finally:
            conn.close()

    def get_stats(self) -> Dict:
        """Retorna estatísticas da limpeza"""
        return self.stats


def cleanup_command(args) -> int:
    """Executa comando cleanup"""

    logger.info("=" * 60)
    logger.info("ORDER QUEUE CLEANUP SCHEDULER (P1-CORE Etapa 4)")
    logger.info("=" * 60)
    logger.info(f"Database: {args.db}")
    logger.info(f"Days threshold: {args.days}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Create backup: {args.backup}")
    logger.info("-" * 60)

    scheduler = OrderCleanupScheduler(db_path=args.db)
    scheduler.stats["db_size_before_bytes"] = scheduler._get_db_size()

    # Busca ordens antigas
    old_orders = scheduler.find_old_orders(days=args.days)

    if not old_orders:
        logger.info("✓ No cleanup needed")
        report_path = _write_cleanup_report(scheduler, args, dry_run=True)
        logger.info(f"Report saved: {report_path}")
        return 0

    # Showtime?
    logger.info("-" * 60)
    logger.info("Sample of old orders to be deleted:")
    logger.info("-" * 60)
    for order in old_orders[:5]:  # Mostra primeiras 5
        order_time = order.get("executed_at") or order.get("created_at")
        logger.info(
            f"  ID: {order['id']}, Status: {order['status']}, "
            f"Created: {order_time}"
        )
    if len(old_orders) > 5:
        logger.info(f"  ... and {len(old_orders) - 5} more")

    # Dry run?
    if args.dry_run:
        logger.info("-" * 60)
        logger.info("DRY RUN: No changes made")
        logger.info(f"Would delete {len(old_orders)} orders")
        report_path = _write_cleanup_report(scheduler, args, dry_run=True)
        logger.info(f"Report saved: {report_path}")
        return 0

    # Real deletion
    logger.info("-" * 60)
    success = scheduler.delete_old_orders(
        days=args.days,
        create_backup=args.backup
    )

    if not success:
        logger.error("✗ Cleanup failed")
        report_path = _write_cleanup_report(scheduler, args, dry_run=False)
        logger.info(f"Report saved: {report_path}")
        return 1

    # Validate
    if scheduler.validate_integrity():
        logger.info("-" * 60)
        logger.info("CLEANUP COMPLETED SUCCESSFULLY")
        logger.info("-" * 60)
        stats = scheduler.get_stats()
        logger.info(f"Orders deleted: {stats['orders_deleted']}")
        logger.info(f"Backup created: {stats['backup_created']}")
        report_path = _write_cleanup_report(scheduler, args, dry_run=False)
        logger.info(f"Report saved: {report_path}")
        return 0
    else:
        logger.error("✗ Integrity validation failed")
        report_path = _write_cleanup_report(scheduler, args, dry_run=False)
        logger.info(f"Report saved: {report_path}")
        return 1


def _write_cleanup_report(scheduler: OrderCleanupScheduler, args, dry_run: bool) -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True, parents=True)
    scheduler.stats["db_size_after_bytes"] = scheduler._get_db_size()
    payload = {
        "timestamp": datetime.now().isoformat(),
        "db": args.db,
        "days": args.days,
        "dry_run": dry_run,
        "backup": args.backup,
        "stats": scheduler.get_stats(),
    }
    report_path = output_dir / f"cleanup_report_{int(datetime.now().timestamp())}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup old orders from database"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/db/trading.db",
        help="Database path (default: data/db/trading.db)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Delete orders older than N days (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without making changes",
    )
    parser.add_argument(
        "--no-backup",
        dest="backup",
        action="store_false",
        default=True,
        help="Skip creating backup (NOT RECOMMENDED)",
    )

    args = parser.parse_args()

    return cleanup_command(args)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
