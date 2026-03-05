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

import json
import sqlite3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
import sys

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
            "errors": [],
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão SQLite"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def find_old_orders(self, days: int = 7) -> List[Dict]:
        """Encontra ordens mais antigas que N dias"""

        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Tenta tabela 'orders'
            cursor.execute("""
                SELECT id, symbol, quantity, status, created_at
                FROM orders
                WHERE created_at < ?
                ORDER BY created_at ASC
            """, (cutoff_iso,))

            old_orders = [dict(row) for row in cursor.fetchall()]
            self.stats["orders_found"] = len(old_orders)

            logger.info(f"✓ Found {len(old_orders)} orders older than {days} days")
            return old_orders

        except sqlite3.OperationalError as e:
            # Tabela 'orders' pode não existir, tenta 'order_queue'
            logger.warning(f"Table 'orders' not found, trying 'order_queue'...")
            try:
                cursor.execute("""
                    SELECT id, symbol, quantity, status, created_at
                    FROM order_queue
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
                logger.error("Neither 'orders' nor 'order_queue' table exists")
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

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            # Delete from 'orders' if exists
            try:
                cursor.execute(
                    "DELETE FROM orders WHERE created_at < ?",
                    (cutoff_iso,)
                )
                deleted = cursor.rowcount
                self.stats["orders_deleted"] = deleted
                logger.info(f"✓ Deleted {deleted} orders from 'orders' table")

            except sqlite3.OperationalError:
                # Try 'order_queue' table
                try:
                    cursor.execute(
                        "DELETE FROM order_queue WHERE created_at < ?",
                        (cutoff_iso,)
                    )
                    deleted = cursor.rowcount
                    self.stats["orders_deleted"] = deleted
                    logger.info(
                        f"✓ Deleted {deleted} orders from 'order_queue' table"
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

    # Busca ordens antigas
    old_orders = scheduler.find_old_orders(days=args.days)

    if not old_orders:
        logger.info("✓ No cleanup needed")
        return 0

    # Showtime?
    logger.info("-" * 60)
    logger.info("Sample of old orders to be deleted:")
    logger.info("-" * 60)
    for order in old_orders[:5]:  # Mostra primeiras 5
        logger.info(f"  ID: {order['id']}, Status: {order['status']}, "
                   f"Created: {order['created_at']}")
    if len(old_orders) > 5:
        logger.info(f"  ... and {len(old_orders) - 5} more")

    # Dry run?
    if args.dry_run:
        logger.info("-" * 60)
        logger.info("DRY RUN: No changes made")
        logger.info(f"Would delete {len(old_orders)} orders")
        return 0

    # Real deletion
    logger.info("-" * 60)
    success = scheduler.delete_old_orders(
        days=args.days,
        create_backup=args.backup
    )

    if not success:
        logger.error("✗ Cleanup failed")
        return 1

    # Validate
    if scheduler.validate_integrity():
        logger.info("-" * 60)
        logger.info("CLEANUP COMPLETED SUCCESSFULLY")
        logger.info("-" * 60)
        stats = scheduler.get_stats()
        logger.info(f"Orders deleted: {stats['orders_deleted']}")
        logger.info(f"Backup created: {stats['backup_created']}")
        return 0
    else:
        logger.error("✗ Integrity validation failed")
        return 1


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
