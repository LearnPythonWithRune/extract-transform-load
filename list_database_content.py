import mysql.connector  # type: ignore
from mysql.connector.cursor_cext import CMySQLCursor


def print_table_content(cursor: CMySQLCursor, table: str):
    sql_stmt = f'SELECT * FROM {table}'
    cursor.execute(sql_stmt)
    rows = cursor.fetchall()

    print(f'{table}:')
    for row in rows:
        print(f'  {row}')


mydb = mysql.connector.connect(
    host='localhost',
    user="root",
    password="password"
)

cur = mydb.cursor()
cur.execute("USE DB")

print_table_content(cur, 'ingress')
print_table_content(cur, 'egress')
print_table_content(cur, 'error_log')

cur.close()
mydb.close()
