A test to see how concurrent write locking worked with webservers/sqlite3

Based on some of the downsides described in this anthonywritescode video:

<https://www.youtube.com/watch?v=jH39c5-y6kg>

He shows an example of sqlite not being able to handle concurrent writes, by spawning a of bash commands in the background to hit it with the `sqlite3` command on command line

I wondered if the same issue happens with [pythons sqlite](https://docs.python.org/3/library/sqlite3.html) module, or with Session's in [sqlalchemy](https://www.sqlalchemy.org/) (I tried looking into it but theres so many damn layers of indirection). Same with [ectos sqlite adapter](https://hexdocs.pm/ecto_sqlite3/Ecto.Adapters.SQLite3.html) in elixir, does the database pooling do anything here for writes? I know it can handle multiple reads at the same time, but what if two requests tried to write at the same time, does it just error one of them?

So, wrote this tiny server to see if lots of concurrent requests hitting a server writing to the same table would cause crashes

```bash
pip install -r requirements.txt
# Run, in different terminals (or in the background with &)
./preventsize &  # just to make sure im not making a giant database, and some debug info
./runserver &
./hammer-server
```

Surprisingly, there were no failures with default values. After looking at the `sqlite3.connect` docs, I found there was a default timeout in the sqlite module:

<https://docs.python.org/3/library/sqlite3.html#module-functions>

`timeout (float) – How many seconds the connection should wait before raising an OperationalError when a table is locked. If another connection opens a transaction to modify a table, that table will be locked until the transaction is committed. Default five seconds.`

Did some benchmarks with different timeout values, different number of requests, and generally there are no failures till you reduce the timeout to 0 or if you're getting thousands of writes per second. Each of these ran for 10 seconds.

| sqlite timeout | parallel clients   | failures | req/second |
| -------------- | ------------------ | -------- | ---------- |
| control, no db | 100                | 0        | 126303     |
| 5000ms         | 100                | 0        | 169        |
| 5000ms         | 500                | 0        | 67         |
| 5000ms         | 1000               | 66       | 58         |
| 1000ms         | 100                | 0        | 168        |
| 1000ms         | 1000               | 101      | 48         |
| 0ms            | 100                | 471      | 217        |
| 0ms            | 1000               | 229      | 121        |

(To do this I just did a `rm test.db && TIMEOUT=1 ./runserver` in one terminal, and `CLIENTS=1000 ./hammer-server` in another)

When there are 1000 concurrent clients, there is significant slowdown, even after `hammer-server` stops, its still processing requests for 5-10 seconds.

So, it'll just be slower when its getting hit with a bunch of requests since its waiting for the lock to clear, but it won't crash or (typically) fail to write, unless you have so many requests that the 5 second timeout is not enough.

Similarly `ecto_sqlite3` has a busy timeout of 2 seconds: <https://hexdocs.pm/ecto_sqlite3/Ecto.Adapters.SQLite3.html#module-provided-options>

So, with this info in mind, (as I dont expect any of my personal project databases to get hammered with hundreds of writes per second), I will continue using sqlite till I need to migrate to something larger

Similarly if you want to read the size from the db, if you just run `sqlite3 'select COUNT(*) FROM test;'` it might fail since the db is locked, but you can use:

```
.timeout 1000;
select COUNT(*) FROM test;
```

to set the timeout to 1000ms, and it'll wait for the lock to clear and then return
