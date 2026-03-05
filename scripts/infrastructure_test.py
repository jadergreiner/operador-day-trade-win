#!/usr/bin/env python3
"""
Infrastructure Verification Test
Validates all critical infrastructure for Phase 1 Beta Launch
Date: 05/03/2026
"""

import sqlite3
import os
from pathlib import Path
import shutil

def test_database():
    """Test 1: Database Connectivity"""
    print('TEST 1: Database Connectivity')
    try:
        conn = sqlite3.connect('data/db/trading.db')
        cursor = conn.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"')
        table_count = cursor.fetchone()[0]
        conn.close()
        print(f'✅ Database OK - {table_count} tables found')
        return True
    except Exception as e:
        print(f'❌ Database FAIL - {e}')
        return False

def test_backups():
    """Test 2: Backup Directory Structure"""
    print('\nTEST 2: Backup Directory Structure')
    backup_dir = Path('data/db/backups')
    if backup_dir.exists():
        backups = list(backup_dir.glob('*.db'))
        print(f'✅ Backups OK - {len(backups)} backup files found')
        for b in backups[:3]:
            size_mb = b.stat().st_size / (1024*1024)
            print(f'   - {b.name} ({size_mb:.2f} MB)')
        return True
    else:
        print(f'❌ Backups FAIL - Directory not found')
        return False

def test_logging():
    """Test 3: Logging Configuration"""
    print('\nTEST 3: Logging Configuration')
    log_dir = Path('data/logs')
    if log_dir.exists():
        logs = list(log_dir.glob('*.log'))
        print(f'✅ Logs OK - {len(logs)} log files found')
        for l in logs[:3]:
            print(f'   - {l.name}')
        return True
    else:
        print(f'❌ Logs FAIL - Directory not found')
        return False

def test_model_and_features():
    """Test 4: Model & Features Ready"""
    print('\nTEST 4: Model & Features Ready')
    model_exists = Path('data/models/xgboost_v1.0.pkl').exists()
    features_exist = Path('data/feature_names.json').exists()

    status = True
    if model_exists:
        model_size = Path('data/models/xgboost_v1.0.pkl').stat().st_size / (1024*1024)
        print(f'✅ Model OK - xgboost_v1.0.pkl ({model_size:.2f} MB)')
    else:
        print(f'❌ Model FAIL - xgboost_v1.0.pkl missing')
        status = False

    if features_exist:
        print(f'✅ Features OK - feature_names.json exists')
    else:
        print(f'❌ Features FAIL - feature_names.json missing')
        status = False

    return status

def test_disk_space():
    """Test 5: Disk Space Available"""
    print('\nTEST 5: Disk Space Available')
    try:
        total, used, free = shutil.disk_usage('/')
        free_gb = free / (1024**3)
        used_gb = used / (1024**3)
        total_gb = total / (1024**3)

        if free_gb > 10:
            print(f'✅ Disk OK - {free_gb:.1f} GB free (target: >10GB)')
            print(f'   Total: {total_gb:.1f} GB, Used: {used_gb:.1f} GB')
            return True
        else:
            print(f'⚠️  Disk WARNING - {free_gb:.1f} GB free (target: >10GB)')
            return False
    except Exception as e:
        print(f'⚠️  Disk WARNING - Could not determine: {e}')
        return False

def main():
    print('=' * 60)
    print('INFRASTRUCTURE VERIFICATION - 05/03/2026')
    print('=' * 60)
    print()

    results = []
    results.append(test_database())
    results.append(test_backups())
    results.append(test_logging())
    results.append(test_model_and_features())
    results.append(test_disk_space())

    print()
    print('=' * 60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f'✅ ALL TESTS PASSED ({passed}/{total})')
        print('Status: INFRASTRUCTURE READY FOR DEPLOYMENT')
    else:
        print(f'⚠️  SOME TESTS FAILED ({passed}/{total})')
        print('Status: REVIEW FAILURES BEFORE PROCEEDING')

    print('=' * 60)

    return all(results)

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
