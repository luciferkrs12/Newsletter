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


def ensure_column(cursor, table: str, column: str, column_type: str):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    except Exception:
        pass


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
                month VARCHAR(50),
                year VARCHAR(50),
                chairman TEXT,
                principal TEXT,
                contents TEXT,
                events TEXT,
                training TEXT,
                workshop TEXT,
                achievements TEXT,
                seminar TEXT,
                faculty TEXT,
                dakshaa TEXT,
                guest TEXT,
                celebration TEXT,
                editorial TEXT,
                summary TEXT,
                last_quote TEXT,
                image VARCHAR(255),
                created_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        for column, col_type in [
            ('month', 'VARCHAR(50)'),
            ('year', 'VARCHAR(50)'),
            ('chairman', 'TEXT'),
            ('principal', 'TEXT'),
            ('contents', 'TEXT'),
            ('events', 'TEXT'),
            ('training', 'TEXT'),
            ('workshop', 'TEXT'),
            ('achievements', 'TEXT'),
            ('seminar', 'TEXT'),
            ('faculty', 'TEXT'),
            ('dakshaa', 'TEXT'),
            ('guest', 'TEXT'),
            ('celebration', 'TEXT'),
            ('editorial', 'TEXT'),
            ('summary', 'TEXT'),
            ('last_quote', 'TEXT'),
            ('image', 'VARCHAR(255)'),
            ('created_by', 'VARCHAR(255)'),
            ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ]:
            ensure_column(cursor, 'newsletters', column, col_type)

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
            month TEXT,
            year TEXT,
            chairman TEXT,
            principal TEXT,
            contents TEXT,
            events TEXT,
            training TEXT,
            workshop TEXT,
            achievements TEXT,
            seminar TEXT,
            faculty TEXT,
            dakshaa TEXT,
            guest TEXT,
            celebration TEXT,
            editorial TEXT,
            summary TEXT,
            last_quote TEXT,
            image TEXT,
            created_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for column, col_type in [
        ('month', 'TEXT'),
        ('year', 'TEXT'),
        ('chairman', 'TEXT'),
        ('principal', 'TEXT'),
        ('contents', 'TEXT'),
        ('events', 'TEXT'),
        ('training', 'TEXT'),
        ('workshop', 'TEXT'),
        ('achievements', 'TEXT'),
        ('seminar', 'TEXT'),
        ('faculty', 'TEXT'),
        ('dakshaa', 'TEXT'),
        ('guest', 'TEXT'),
        ('celebration', 'TEXT'),
        ('editorial', 'TEXT'),
        ('summary', 'TEXT'),
        ('last_quote', 'TEXT'),
        ('image', 'TEXT'),
        ('created_by', 'TEXT'),
        ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE newsletters ADD COLUMN {column} {col_type}")
        except Exception:
            pass
    conn.commit()
    cursor.close()
