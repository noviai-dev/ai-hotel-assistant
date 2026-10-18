"""PostgreSQL storage for immutable collection history."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


SQL_DIR = Path(__file__).with_name('sql')


def ensure_database(settings):
    # CREATE DATABASE must run outside a transaction, against an existing DB.
    with psycopg.connect(**dict(settings, dbname=os.environ.get('PGMAINTENANCE_DB', 'postgres')),
                         autocommit=True) as admin:
        exists = admin.execute('SELECT 1 FROM pg_database WHERE datname = %s',
                               (settings['dbname'],)).fetchone()
        if exists:
            return
        statement = sql.SQL((SQL_DIR / '001_create_database.sql').read_text(encoding='utf-8')).format(
            database=sql.Identifier(settings['dbname']))
        try:
            admin.execute(statement)
        except psycopg.errors.DuplicateDatabase:
            # Another process may have created it after our existence check.
            pass


def connect(*, initialize=False):
    password = os.environ.get('PGPASSWORD')
    if not password:
        raise ValueError('请设置 PGPASSWORD 环境变量')
    settings = dict(
            host=os.environ.get('PGHOST', 'localhost'),
            port=int(os.environ.get('PGPORT', '5432')),
            user=os.environ.get('PGUSER', 'postgres'), password=password,
            dbname=os.environ.get('PGDATABASE', 'postgres'), connect_timeout=5,
            options='-c search_path=public',
    )
    conn = None
    try:
        if initialize:
            ensure_database(settings)
        conn = psycopg.connect(**settings)
        if initialize:
            Database(conn).initialize()
        return conn
    except BaseException as exc:
        if conn is not None:
            conn.close()
        if not isinstance(exc, psycopg.Error):
            raise
        if isinstance(exc, psycopg.errors.InsufficientPrivilege):
            message = 'PostgreSQL权限不足：首次建库需要CREATEDB权限，初始化表结构需要目标库的建表权限'
        else:
            message = 'PostgreSQL连接或初始化失败，请检查服务、PG连接变量、维护库和sql脚本（SQLSTATE: ' + (exc.sqlstate or 'unknown') + '）'
        raise RuntimeError(message) from None


def hotel_key(row):
    url = urlsplit(str(row.get('url') or ''))
    identity = urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path, '', ''))
    if not identity:
        identity = json.dumps([row.get('name'), row.get('address')], ensure_ascii=False)
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()


class Database:
    def __init__(self, conn):
        self.conn = conn

    def initialize(self):
        self.conn.execute((SQL_DIR / '002_create_tables.sql').read_text(encoding='utf-8'))
        self.conn.execute((SQL_DIR / '003_daily_prices.sql').read_text(encoding='utf-8'))
        self.conn.commit()

    def start_batch(self, config, plan, actor):
        batch = uuid4()
        self.conn.execute('INSERT INTO collection_batches(id,own_hotel,actor,config,queries) VALUES (%s,%s,%s,%s,%s)',
                          (batch, config['own_hotel'], actor, Jsonb(config), Jsonb(plan)))
        self.conn.commit()
        return batch

    def start_query(self, batch, index, query):
        result = self.conn.execute('INSERT INTO collection_queries(batch_id,query_index,input) VALUES (%s,%s,%s) RETURNING id',
                                   (batch, index, Jsonb(query))).fetchone()[0]
        self.conn.commit()
        return result

    def update_run(self, query_id, run):
        self.conn.execute('UPDATE collection_queries SET apify_run_id=%s,run_metadata=%s,status=%s WHERE id=%s',
                          (run['id'], Jsonb(run), run['status'], query_id))
        self.conn.commit()

    def save_quotes(self, query_id, pairs):
        # A complete query is committed atomically; previous queries remain after failure.
        with self.conn.transaction():
            for row, raw in pairs:
                values = dict(row)
                values['property_type'] = values.pop('type')
                values['areas'] = [v for v in values['areas'].split(',') if v]
                values['reasons'] = [v for v in values['reasons'].split(',') if v]
                values['query_id'] = query_id
                values['hotel_key'] = hotel_key(row)
                for key in ('amenities', 'room_offers'):
                    values[key] = Jsonb(values[key])
                values['raw_data'] = Jsonb(raw)
                try:
                    parsed = datetime.fromisoformat(values['scraped_at'])
                    values['scraped_at'] = parsed if parsed.tzinfo else None
                except (TypeError, ValueError):
                    values['scraped_at'] = None
                columns = list(values)
                # Column names are only from normalize(), never from upstream keys.
                sql = 'INSERT INTO hotel_quotes (' + ','.join(columns) + ') VALUES (' + ','.join(['%s']*len(columns)) + ') ON CONFLICT (query_id,hotel_key) DO NOTHING'
                self.conn.execute(sql, tuple(values[k] for k in columns))
            self.conn.execute("UPDATE collection_queries SET status='stored' WHERE id=%s", (query_id,))

    def finish_batch(self, batch, status, error=None):
        self.conn.rollback()
        self.conn.execute('UPDATE collection_batches SET status=%s,finished_at=now(),error_message=%s WHERE id=%s', (status, error, batch))
        self.conn.commit()
