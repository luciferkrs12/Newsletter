import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'news')
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'database.db'))
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_SECURE = os.getenv('SMTP_SECURE', 'false').strip().lower() in ('true', '1', 'yes')
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER)


def param_style(sql: str) -> str:
    if DB_TYPE == 'mysql':
        return sql.replace('?', '%s')
    return sql


def create_mysql_database():
    try:
        import pymysql
    except ImportError as exc:
        raise ImportError('Install PyMySQL to use MySQL backend') from exc

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    conn.close()


def get_db_connection():
    if DB_TYPE == 'mysql':
        create_mysql_database()
        try:
            import pymysql
        except ImportError as exc:
            raise ImportError('Install PyMySQL to use MySQL backend') from exc

        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor,
            autocommit=False,
        )
        return conn

    import sqlite3

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn
