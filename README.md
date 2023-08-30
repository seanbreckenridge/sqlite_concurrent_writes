A test to see how concurrent write locking worked with webservers/sqlite3

Based on some of the downsides described in this anthonywritescode video:

<https://www.youtube.com/watch?v=jH39c5-y6kg>

He shows an example of sqlite not being able to handle concurrent writes, which makes sense since he was just spawning a bunch of bash to hit it with the `sqlite3` command on command line

I wondered if the same issue happens with pythons sqlite module, or with Session's in sqlalchemy (I tried looking into it but theres so many damn layers of indirection). Same with sqlite_echo in elixir, does the database pooling do anything here for writes? I know it can handle multiple reads at the same time, but what if two requests tried to write at the same time, does it just error one of them?

So, wrote this tiny server to see if lots of concurrent requests hitting a server writing to the same table would cause crashes

```bash
pip install -r requirements.txt
# Run, in different terminals:
./preventsize &  # just to make sure im not making a giant database, and some debug info
./runserver &
./hammer-server
```

Surprisingly, there were no failures, because of the default timeout in the sqlite module:

<https://docs.python.org/3/library/sqlite3.html#module-functions>

`timeout (float) – How many seconds the connection should wait before raising an OperationalError when a table is locked. If another connection opens a transaction to modify a table, that table will be locked until the transaction is committed. Default five seconds.`

Did some benchmarks with different timeout values, different number of requests, and generally there are no failures till you reduce the timeout to 0 or if you're getting thousands of writes per second:

| sqlite timeout | parallel curl requests | est. failures | db row count after 10 seconds |
|----------------|------------------------|---------------|-------------------------------|
| 5000ms         | 64                     | 0             | 1558                          |
| 5000ms         | 256                    | 0             | 1589                          |
| 1000ms         | 64                     | 0             | 1517                          |
| 1000ms         | 256                    | 0             | 1682                          |
| 0ms            | 64                     | 68            | 1614                          |
| 0ms            | 256                    | 221           | 1601                          |

(To do this I just did a `rm test.db && TIMEOUT=1 ./runserver` in one terminal, and `timeout 10 ./hammer-server 256` in another)

So, it'll just be **much slower** when its getting hit with a bunch of requests since its waiting for the lock to clear, but it won't crash or (typically) fail to write, unless you have so many requests that the 5 second timeout is not enough

Similarly `ecto_sqlite3` has a busy timeout of 2 seconds: <https://hexdocs.pm/ecto_sqlite3/Ecto.Adapters.SQLite3.html#module-provided-options>

So, with this info in mind, (as I dont expect any of my personal project databases to get hammered with hundreds of writes per second), I will continue using sqlite till I need to migrate to something larger

Similarly if you want to read the size from the db, if you just run `sqlite3 'select COUNT(*) FROM test;'` it might fail since the db is locked, but you can use:

```
.timeout 1000;
select COUNT(*) FROM test;
```

to set the timeout to 1000ms, and it'll wait for the lock to clear and then return
