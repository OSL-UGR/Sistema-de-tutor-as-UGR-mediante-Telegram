import mysql.connector
import sys
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
import logging

logger = logging.getLogger("db")

# Connect to MariaDB Platform
try:
    conn = mysql.connector.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=3306,
        database=DB_NAME,
        autocommit=True,
    )
except mysql.connector.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

#Copia el schema a la BD
fd = open('./db/schema.sql', 'r')
sqlFile = fd.read()
fd.close()
sqlCommands = sqlFile.split(';')

cursor = conn.cursor(dictionary=True)
for command in sqlCommands[:-1]:
    try:
        cursor.execute(command)
    except Exception as e:
        print("Table skipped: ", e)


def get_cursor():
    return conn.cursor(dictionary=True)

def rollback():
    conn.rollback()

def commit():
    conn.commit()

def close_connection():
    conn.close()