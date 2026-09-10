import aiosqlite
import os


DB_PATH = os.getenv("DB_PATH", "bot.db")


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    balance REAL DEFAULT 0
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS number_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    service TEXT NOT NULL,
                    country TEXT,
                    phone TEXT,
                    activation_id TEXT,
                    price REAL DEFAULT 0,
                    status TEXT DEFAULT 'waiting',
                    sms_code TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nakrutka_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT,
                    link TEXT,
                    quantity INTEGER,
                    price REAL DEFAULT 0,
                    panel_order_id TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stars_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS topup_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.commit()

    def get_db(self):
        return aiosqlite.connect(self.path)

    async def get_or_create_user(self, tg_id, username):
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row

            cur = await conn.execute(
                "SELECT * FROM users WHERE tg_id = ?",
                (tg_id,)
            )
            user = await cur.fetchone()

            if user:
                return user

            await conn.execute(
                "INSERT INTO users (tg_id, username, balance) VALUES (?, ?, 0)",
                (tg_id, username)
            )
            await conn.commit()

            cur = await conn.execute(
                "SELECT * FROM users WHERE tg_id = ?",
                (tg_id,)
            )
            return await cur.fetchone()

    async def change_balance(self, tg_id, amount):
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE users SET balance = balance + ? WHERE tg_id = ?",
                (amount, tg_id)
            )
            await conn.commit()

    async def create_number_order(
        self,
        user_id,
        provider,
        service,
        country,
        phone,
        activation_id,
        price
    ):
        async with aiosqlite.connect(self.path) as conn:
            cur = await conn.execute("""
                INSERT INTO number_orders
                (user_id, provider, service, country, phone,
                 activation_id, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
            """, (
                user_id,
                provider,
                service,
                str(country),
                phone,
                str(activation_id),
                price
            ))

            await conn.commit()
            return cur.lastrowid

    async def update_number_order(self, order_id, **fields):
        if not fields:
            return

        allowed = {
            "status",
            "sms_code",
            "phone",
            "price"
        }

        fields = {
            key: value
            for key, value in fields.items()
            if key in allowed
        }

        if not fields:
            return

        set_sql = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values())
        values.append(order_id)

        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                f"UPDATE number_orders SET {set_sql} WHERE id = ?",
                values
            )
            await conn.commit()

    async def create_stars_order(self, user_id, amount):
        async with aiosqlite.connect(self.path) as conn:
            cur = await conn.execute("""
                INSERT INTO stars_orders
                (user_id, amount, status)
                VALUES (?, ?, 'pending')
            """, (user_id, amount))

            await conn.commit()
            return cur.lastrowid

    async def set_stars_order_paid(self, order_id):
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE stars_orders SET status = 'paid' WHERE id = ?",
                (order_id,)
            )
            await conn.commit()


db = Database()
