from backend.config import DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def mysql_database_config():
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
        cursorclass=pymysql.cursors.Cursor,
    )
    return conn


def format_sql(sql: str) -> str:
    if DB_TYPE == 'mysql':
        return sql.replace('?', '%s')
    return sql


def create_mysql_database():
    conn = mysql_database_config()
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    conn.commit()
    cursor.close()
    conn.close()


def init_db(conn):
    if DB_TYPE == 'mysql':
        create_mysql_database()
        cursor = conn.cursor()

        cursor.execute(format_sql("""
            CREATE TABLE IF NOT EXISTS users(
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255),
                password VARCHAR(255),
                role VARCHAR(50)
            )
        """))

        cursor.execute(format_sql("""
            CREATE TABLE IF NOT EXISTS newsletters(
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                content TEXT,
                image VARCHAR(255)
            )
        """))

        conn.commit()
        cursor.close()
        return

    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsletters(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            image TEXT
        )
    """)
    conn.commit()
    cursor.close()
