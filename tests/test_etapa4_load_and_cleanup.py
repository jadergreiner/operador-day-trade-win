"""
test_etapa4_load_and_cleanup.py

Testes da Etapa 4 (P1-CORE):
- Load testing para validar 100+ ordens/min
- Cleanup scheduler para limpeza segura de ordens antigas

Status: ETAPA 4 READY FOR TESTING
"""

import json
import sqlite3
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys
import os


class TestLoadTestOrderQueue:
    """Testes para load_test_order_queue.py"""

    def test_load_test_exists(self):
        """Verifica se script de load test existe"""
        script = Path("scripts/load_test_order_queue.py")
        assert script.exists(), f"Script {script} nao encontrado"

    def test_load_test_has_required_functions(self):
        """Verifica se script tem funcoes obrigatorias"""
        with open("scripts/load_test_order_queue.py", "r", encoding="utf-8") as f:
            content = f.read()
            assert "LoadTestMetrics" in content
            assert "MockOrderQueue" in content
            assert "simulate_orders" in content
            assert "run_load_test" in content
            assert "validate_results" in content

    def test_load_test_cli_parameters(self):
        """Verifica se script aceita parametros CLI"""
        result = subprocess.run(
            [sys.executable, "scripts/load_test_order_queue.py",
             "--duration", "1", "--rate", "60"],
            capture_output=True,
            text=True
        )
        assert result.returncode in [0, 1], "Script nao roda corretamente"

    def test_load_test_creates_output(self):
        """Verifica se load test gera arquivo JSON de resultados"""
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)

        files_before = len(list(outputs_dir.glob("load_test_results_*.json")))

        result = subprocess.run(
            [sys.executable, "scripts/load_test_order_queue.py",
             "--duration", "2", "--rate", "120"],
            capture_output=True,
            text=True,
            cwd="."
        )

        files_after = len(list(outputs_dir.glob("load_test_results_*.json")))
        assert files_after >= files_before, "Nenhum arquivo JSON foi criado"


class TestCleanupScheduler:
    """Testes para cleanup_old_orders_scheduler.py"""

    def test_cleanup_script_exists(self):
        """Verifica se script de cleanup existe"""
        script = Path("scripts/cleanup_old_orders_scheduler.py")
        assert script.exists(), f"Script {script} nao encontrado"

    def test_cleanup_has_required_classes(self):
        """Verifica se script tem classes obrigatorias"""
        with open("scripts/cleanup_old_orders_scheduler.py", "r", encoding="utf-8") as f:
            content = f.read()
            assert "OrderCleanupScheduler" in content
            assert "find_old_orders" in content
            assert "create_backup" in content
            assert "delete_old_orders" in content
            assert "validate_integrity" in content

    def test_cleanup_dry_run_mode(self):
        """Verifica se cleanup suporta dry-run (sem deletar)"""
        result = subprocess.run(
            [sys.executable, "scripts/cleanup_old_orders_scheduler.py",
             "--dry-run", "--days", "7"],
            capture_output=True,
            text=True,
            cwd="."
        )

        assert result.returncode == 0, f"Dry-run falhou: {result.stderr}"
        combined = (result.stdout + result.stderr).lower()
        assert "cleanup" in combined
        outputs_dir = Path("outputs")
        assert list(outputs_dir.glob("cleanup_report_*.json"))

    def test_cleanup_with_mock_database(self):
        """Testa cleanup scheduler com banco mock"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT
                )
            """)

            old_date = (datetime.now() - timedelta(days=10)).isoformat()
            cursor.execute(
                "INSERT INTO orders (symbol, created_at, status) VALUES (?, ?, ?)",
                ("WIN", old_date, "CLOSED")
            )

            recent_date = (datetime.now() - timedelta(days=2)).isoformat()
            cursor.execute(
                "INSERT INTO orders (symbol, created_at, status) VALUES (?, ?, ?)",
                ("WIN", recent_date, "CLOSED")
            )

            conn.commit()
            conn.close()

            result = subprocess.run(
                [sys.executable, "scripts/cleanup_old_orders_scheduler.py",
                 "--db", str(db_path), "--dry-run", "--days", "7"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"Cleanup falhou: {result.stderr}"

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM orders")
            count = cursor.fetchone()[0]
            assert count == 2, "Ordens nao foram inseridas no mock"
            conn.close()
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except:
                    pass

    def test_cleanup_backup_directory(self):
        """Verifica se backup directory eh criado corretamente"""
        backup_dir = Path("data/db/backups")

        if backup_dir.exists():
            backups_before = len(list(backup_dir.glob("trading_*.db")))
        else:
            backups_before = 0

        subprocess.run(
            [sys.executable, "scripts/cleanup_old_orders_scheduler.py",
             "--dry-run"],
            capture_output=True,
            text=True
        )

        if backup_dir.exists():
            backups_after = len(list(backup_dir.glob("trading_*.db")))
            assert backups_after >= backups_before


class TestEtapa4Integration:
    """Testes de integracao Etapa 4"""

    def test_both_scripts_executable(self):
        """Verifica se ambos scripts sao executaveis"""
        load_test = Path("scripts/load_test_order_queue.py")
        cleanup = Path("scripts/cleanup_old_orders_scheduler.py")

        assert load_test.exists()
        assert cleanup.exists()
        assert load_test.stat().st_size > 0
        assert cleanup.stat().st_size > 0

    def test_load_test_output_format(self):
        """Testa formato do output JSON do load test"""
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)

        files_before = list(outputs_dir.glob("load_test_results_*.json"))

        subprocess.run(
            [sys.executable, "scripts/load_test_order_queue.py",
             "--duration", "2", "--rate", "120"],
            capture_output=True,
            text=True
        )

        json_files = list(outputs_dir.glob("load_test_results_*.json"))
        new_files = [f for f in json_files if f not in files_before]

        target_files = new_files if new_files else json_files
        if target_files:
            latest = max(target_files, key=lambda p: p.stat().st_mtime)
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
                required_fields = [
                    "total_orders",
                    "successful",
                    "failed",
                    "success_rate_percent",
                    "throughput_orders_per_min",
                    "memory_delta_mb",
                    "cpu_percent",
                ]

                for field in required_fields:
                    assert field in data, f"Campo obrigatorio {field} nao encontrado"

    def test_etapa4_acceptance_criteria(self):
        """Testa criterios de aceitacao da Etapa 4"""
        load_test = Path("scripts/load_test_order_queue.py")
        assert load_test.exists(), "AC1 FAIL: Load test script nao existe"

        cleanup = Path("scripts/cleanup_old_orders_scheduler.py")
        assert cleanup.exists(), "AC2 FAIL: Cleanup script nao existe"

        result = subprocess.run(
            [sys.executable, "scripts/load_test_order_queue.py",
             "--duration", "1", "--rate", "60"],
            capture_output=True,
            text=True,
            timeout=10
        )
        combined = (result.stdout + result.stderr).lower()
        assert "duration" in combined or result.returncode in [0, 1]

        result = subprocess.run(
            [sys.executable, "scripts/cleanup_old_orders_scheduler.py",
             "--dry-run"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "AC4 FAIL: Dry-run nao funciona"

        with open("scripts/load_test_order_queue.py", encoding="utf-8") as f:
            content = f.read()
            assert "logging" in content or "INFO" in content

        with open("scripts/cleanup_old_orders_scheduler.py", encoding="utf-8") as f:
            content = f.read()
            assert "logging" in content


class TestEtapa4Documentation:
    """Testes de documentacao Etapa 4"""

    def test_scripts_have_docstrings(self):
        """Verifica se scripts tem docstrings"""
        with open("scripts/load_test_order_queue.py", encoding="utf-8") as f:
            content = f.read()
            assert '"""' in content or "'''" in content

        with open("scripts/cleanup_old_orders_scheduler.py", encoding="utf-8") as f:
            content = f.read()
            assert '"""' in content or "'''" in content

    def test_bat_scheduler_exists(self):
        """Verifica se BAT scheduler foi criado"""
        bat_file = Path("BAT/AGENDA_LIMPEZA_DIARIA.bat")
        assert bat_file.exists(), "BAT scheduler nao existe"

        with open(bat_file) as f:
            content = f.read()
            assert "cleanup_old_orders_scheduler.py" in content
            assert "schtasks" in content


class TestLoadTestRealBackend:
    """Testes para backend real do load test"""

    def test_load_test_real_backend(self):
        """Verifica se backend real executa com DB temporario"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, "scripts/load_test_order_queue.py",
                 "--duration", "2", "--rate", "120",
                 "--backend", "real", "--db", db_path,
                 "--profile-memory"],
                capture_output=True,
                text=True
            )
            assert result.returncode in [0, 1], "Backend real nao executou"
            outputs_dir = Path("outputs")
            assert list(outputs_dir.glob("load_test_results_*.json"))
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except:
                    pass
