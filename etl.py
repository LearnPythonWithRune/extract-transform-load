import argparse
import json
import logging
from datetime import datetime
from typing import List, Any

import mysql.connector  # type: ignore


logging.basicConfig(encoding='utf-8', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__file__)


class MySqlConnector:
    def __init__(self, host: str):
        self.mydb = mysql.connector.connect(
            host=host,
            user="root",
            password="password"
        )

        self.cur = self.mydb.cursor()
        self.cur.execute("USE DB")

    def fetchall_query(self, sql_stmt: str) -> Any:
        self.cur.execute(sql_stmt)
        return self.cur.fetchall()

    def fetch_query(self, sql_stmt: str) -> Any:
        self.cur.execute(sql_stmt)
        return self.cur.fetchone()

    def commit_query(self, sql_stmt: str):
        self.cur.execute(sql_stmt)
        self.mydb.commit()

    def close(self):
        self.cur.close()
        self.mydb.close()


def extract(db_connect: MySqlConnector, last_read: datetime):
    sql_stmt = f"SELECT ingest_time, ingest_value FROM ingress WHERE ingest_time>'{last_read}'"
    new_rows = db_connect.fetchall_query(sql_stmt)
    return new_rows


def transform(rows_to_process: List):
    transformation_map = {
        '🍎': 'apple',
        '🍐': 'pear',
        '🍌': 'banana'
    }

    transformed_rows = []
    error_log = []
    for ingest_time, ingest_value in rows_to_process:
        try:
            # Here we should do our transformation
            egress_value = transformation_map[ingest_value.strip()]

            transformed_rows.append((ingest_time, egress_value))
        except Exception as e:
            error_msg = f'{type(e).__name__}: {e}'.replace('\'', '"')
            error_log.append((ingest_time, datetime.utcnow(), ingest_value, error_msg))
    return transformed_rows, error_log


def load(db_connect: MySqlConnector, rows_to_load: List, error_log: List, last_successful_ingest_time: datetime):
    for ingest_time, egress_value in rows_to_load:

        sql_stmt = f"INSERT INTO egress(ingest_time, egress_value) VALUES('{ingest_time}', '{egress_value}')"
        try:
            db_connect.commit_query(sql_stmt)
            if ingest_time > last_successful_ingest_time:
                last_successful_ingest_time = ingest_time
        except Exception as e:
            error_msg = f'{type(e).__name__}: {e}'.replace('\'', '"')
            error_log.append((ingest_time, datetime.utcnow(), egress_value, error_msg))

    return error_log, last_successful_ingest_time


def load_error_log(db_connect: MySqlConnector, error_rows_to_log: List):
    for ingest_time, error_time, ingest_value, error_msg in error_rows_to_log:
        sql_stmt = "INSERT INTO error_log(ingest_time, error_time, ingest_value, error_message)" \
                    + f"VALUES('{ingest_time}', '{error_time}', '{ingest_value}', '{error_msg}')"
        db_connect.commit_query(sql_stmt)


def process(mysql_host: str, state_filename: str):
    with open(state_filename) as f:
        content = f.read()
        state = json.loads(content)

    connector = MySqlConnector(mysql_host)

    last_ingest = datetime.strptime(state['last_ingest'], '%Y-%m-%dT%H:%M:%S')
    logger.info(f'processing {last_ingest=}')

    # Extract
    rows = extract(connector, last_ingest)

    # Transform
    rows, error_rows = transform(rows)

    # Load
    error_rows, last_ingest = load(connector, rows, error_rows, last_ingest)
    load_error_log(connector, error_rows)

    # After a successful ETL we store the new state
    with open(state_filename, 'w') as f:
        f.write(
            json.dumps(
                {
                    'last_ingest': last_ingest.strftime('%Y-%m-%dT%H:%M:%S')
                },
                indent=2
            )
        )

    connector.close()
    logger.info(f'processed {len(rows)} rows {last_ingest=}')


def __init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument('--host',
                        help='The MySQL host',
                        default='localhost')

    parser.add_argument('--state_file',
                        help='Json state file',
                        default='state.json')

    return parser


if __name__ == '__main__':
    arg_parser = __init_argparse()
    args, _ = arg_parser.parse_known_args()
    host = args.host
    state_file = args.state_file
    logger.info(f'Config ({host=}, {state_file=})')

    process(host, state_file)
