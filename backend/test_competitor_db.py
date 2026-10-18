"""Integration test using session-local temporary tables; no paid Apify runs."""
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

import competitors
import competitor_db
import psycopg
from competitor_db import Database, connect


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'PGPASSWORD': 'test-only', 'PGDATABASE': 'hotel "custom"',
                                          'PGMAINTENANCE_DB': 'postgres'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_bootstrap(self, exists, create_error=None):
        admin, target = MagicMock(), MagicMock()
        admin.__enter__.return_value = admin
        admin.execute.side_effect = [MagicMock(fetchone=MagicMock(return_value=exists))]
        if not exists:
            admin.execute.side_effect = [MagicMock(fetchone=MagicMock(return_value=None)),
                                         create_error or MagicMock()]
        with patch.object(competitor_db.psycopg, 'connect', side_effect=[admin, target]) as driver:
            result = connect(initialize=True)
        self.assertIs(result, target)
        self.assertEqual(driver.call_args_list[0].kwargs['dbname'], 'postgres')
        self.assertTrue(driver.call_args_list[0].kwargs['autocommit'])
        self.assertEqual(driver.call_args_list[1].kwargs['dbname'], 'hotel "custom"')
        self.assertEqual(target.execute.call_count, 2)
        self.assertIn('CREATE TABLE IF NOT EXISTS', target.execute.call_args_list[0].args[0])
        self.assertIn('latest_daily_hotel_prices', target.execute.call_args_list[1].args[0])
        return admin

    def test_missing_database_uses_sql_template_and_quotes_name(self):
        admin = self.run_bootstrap(None)
        statement = admin.execute.call_args_list[1].args[0].as_string()
        self.assertIn('CREATE DATABASE "hotel ""custom"""', statement)
        self.assertIn("TEMPLATE template0", statement)

    def test_existing_database_skips_creation(self):
        admin = self.run_bootstrap((1,))
        self.assertEqual(admin.execute.call_count, 1)

    def test_default_database_and_schema(self):
        os.environ.pop('PGDATABASE')
        target = MagicMock()
        with patch.object(competitor_db, 'ensure_database') as ensure, \
             patch.object(competitor_db.psycopg, 'connect', return_value=target) as driver:
            connect(initialize=True)
        self.assertEqual(driver.call_args.kwargs['dbname'], 'postgres')
        self.assertEqual(driver.call_args.kwargs['options'], '-c search_path=public')
        self.assertEqual(ensure.call_args.args[0]['dbname'], 'postgres')

    def test_concurrent_creation_is_tolerated(self):
        self.run_bootstrap(None, psycopg.errors.DuplicateDatabase())

    def test_permission_failure_stops_before_target_connection(self):
        with patch.object(competitor_db.psycopg, 'connect',
                          side_effect=psycopg.errors.InsufficientPrivilege()) as driver:
            with self.assertRaisesRegex(RuntimeError, 'CREATEDB'):
                connect(initialize=True)
            self.assertEqual(driver.call_count, 1)

    def test_schema_failure_closes_connection(self):
        target = MagicMock()
        with patch.object(competitor_db, 'ensure_database'), \
             patch.object(competitor_db.psycopg, 'connect', return_value=target), \
             patch.object(Database, 'initialize', side_effect=psycopg.errors.SyntaxError()):
            with self.assertRaises(RuntimeError):
                connect(initialize=True)
        target.close.assert_called_once()

    def test_init_command_bootstraps_without_apify(self):
        with patch('sys.argv', ['competitors.py', '--init-db']), \
             patch.object(competitor_db, 'connect') as driver:
            self.assertEqual(competitors.main(), 0)
        driver.assert_called_once_with(initialize=True)

    def test_preview_does_not_connect(self):
        with patch('sys.argv', ['competitors.py', '--limit-runs', '1']), \
             patch.object(competitor_db, 'connect') as driver, \
             patch.object(competitors, 'tokyo_today', return_value=date(2026, 10, 11)), \
             patch('builtins.print'):
            self.assertEqual(competitors.main(), 0)
        driver.assert_not_called()

    def test_execute_initializes_before_paid_request_and_stops_on_failure(self):
        with tempfile.TemporaryDirectory() as output, \
             patch.dict(os.environ, {'APIFY_TOKEN': 'fake'}), \
             patch('sys.argv', ['competitors.py', '--execute', '--limit-runs', '1', '--output', output]), \
             patch.object(competitors, 'tokyo_today', return_value=date(2026, 10, 11)), \
             patch.object(competitor_db, 'connect', side_effect=RuntimeError('init failed')) as driver, \
             patch.object(competitors, 'collect') as collect, patch('builtins.print'):
            with self.assertRaisesRegex(RuntimeError, 'init failed'):
                competitors.main()
        driver.assert_called_once_with(initialize=True)
        collect.assert_not_called()


@unittest.skipUnless(os.environ.get('TEST_POSTGRES') == '1', 'Set TEST_POSTGRES=1 for local PostgreSQL test')
class DatabaseTests(unittest.TestCase):
    def test_schema_quotes_history_and_atomic_rollback(self):
        with connect() as conn:
            schema = Path(__file__).with_name('sql').joinpath('002_create_tables.sql').read_text(encoding='utf-8')
            schema = schema.replace('CREATE TABLE IF NOT EXISTS', 'CREATE TEMP TABLE IF NOT EXISTS')
            schema = schema.replace('CREATE OR REPLACE VIEW', 'CREATE OR REPLACE TEMP VIEW')
            # Only this session owns these tables. Closing the session removes them.
            conn.execute(schema)
            daily = Path(__file__).with_name('sql').joinpath('003_daily_prices.sql').read_text(encoding='utf-8')
            conn.execute(daily.replace('CREATE OR REPLACE VIEW', 'CREATE OR REPLACE TEMP VIEW'))
            conn.commit()
            db = Database(conn)
            cfg = json.loads(Path(__file__).with_name('competitors.example.json').read_text(encoding='utf-8'))
            with patch.object(competitors, 'tokyo_today', return_value=date(2026, 10, 11)):
                plan = competitors.build_plan(cfg)
            batch = db.start_batch(cfg, plan, competitors.ACTOR)
            query = db.start_query(batch, 1, plan[0])
            db.update_run(query, {'id': 'test-run', 'status': 'SUCCEEDED'})
            raw = {'name': "Family's Hotel", 'type': 'Hotel', 'price': {'currency': 'JPY', 'perNight': 18000},
                   'address': {'full': 'Chuo-ku, Osaka'}, 'scrapedAt': '2026-10-11T00:00:00Z'}
            row = competitors.normalize(raw, plan[0], cfg)
            db.save_quotes(query, [(row, raw), (row, raw)])
            record = conn.execute('SELECT name,nightly_jpy,raw_data FROM competitor_quotes').fetchone()
            self.assertEqual(record[0], "Family's Hotel")
            self.assertEqual(float(record[1]), 18000)
            self.assertEqual(record[2], raw)
            self.assertEqual(conn.execute('SELECT count(*) FROM hotel_quotes').fetchone()[0], 1)
            conn.commit()
            q2 = db.start_query(batch, 2, plan[1])
            invalid = dict(row, name='Invalid', url='https://example.com/other', check_out='2026-01-01')
            with self.assertRaises(Exception):
                db.save_quotes(q2, [(row, raw), (invalid, raw)])
            self.assertEqual(conn.execute('SELECT count(*) FROM hotel_quotes WHERE query_id=%s', (q2,)).fetchone()[0], 0)
            conn.commit()
            # Same date/party at a later collection remains history; latest view selects new quote.
            changed_raw = dict(raw, price={'currency': 'JPY', 'perNight': 25000})
            changed = competitors.normalize(changed_raw, plan[0], cfg)
            db.save_quotes(q2, [(changed, changed_raw)])
            self.assertEqual(conn.execute('SELECT count(*) FROM daily_hotel_prices').fetchone()[0], 2)
            latest = conn.execute('SELECT nightly_jpy,in_target_price_band FROM latest_daily_hotel_prices').fetchone()
            self.assertEqual(float(latest[0]), 25000)
            self.assertFalse(latest[1])
            conn.commit()
            db.finish_batch(batch, 'failed', 'test')
            self.assertEqual(conn.execute('SELECT status FROM collection_batches WHERE id=%s', (batch,)).fetchone()[0], 'failed')


if __name__ == '__main__':
    unittest.main()
