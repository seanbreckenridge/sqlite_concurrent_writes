import os
import sqlite3

from sanic import Sanic
from sanic.response import HTTPResponse

app = Sanic("benchmark")

db = "test.db"


def setup_db():
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)""")
    conn.commit()
    conn.close()


TIMEOUT = int(os.environ.get("TIMEOUT", 5))


class Failures:
    x = 0


failures = Failures()


@app.route("/")
async def basic(request):
    try:
        conn = sqlite3.connect(db, timeout=TIMEOUT)
        c = conn.cursor()
        before = c.execute("SELECT COUNT(*) FROM test").fetchone()[0]
        c.execute("INSERT INTO test VALUES (NULL)")
        conn.commit()
        after = c.execute("SELECT COUNT(*) FROM test").fetchone()[0]
        conn.close()
        print("before: %d, after: %d" % (before, after))
    except sqlite3.OperationalError:
        failures.x += 1
    return HTTPResponse()


# at exit print the number of failures
import atexit

atexit.register(lambda: print("failures: %d" % failures.x))

if __name__ == "__main__":
    setup_db()
    app.run()
