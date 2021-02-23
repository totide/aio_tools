# -*- coding: utf-8 -*-
# @Explain  : 
# @Time     : 2021/02/22 10:06 
# @Author   : tide
# @FileName : pool

import time
import logging
import redis
from functools import partial
from threading import Lock
from cachetools import LRUCache
from redis.connection import ConnectionPool
from common.logwriter import trace_full

logger = logging.getLogger(__name__)
_pool_cache = {}
_pool_lock = Lock()
DB_RECONNECT_DELAY = 3
MAX_ACCESS_LIMIT = 10000
MAX_ACCESS_COUNT_SECONDS_RECORD = 3600


class RedisNotReadyException(Exception):
    pass


class RedisCommandCheckError(Exception):
    pass


def _shared_pool(**opts):
    if "host" in opts:
        key = "{}:{}/{}".format(opts["host"], opts["port"], opts["db"])
    else:
        key = "{}/{}".format(opts["path"], opts["db"])
    pool = _pool_cache.get(key)
    if pool is not None:
        return pool
    with _pool_lock:
        pool = _pool_cache.get(key)
        if pool is not None:
            return pool
        pool = ConnectionPool(**opts)
        _pool_cache[key] = pool
        return pool


def db_check(func):
    def decorate(*args, **kwargs):
        self = func.keywords.pop("_cls", None)
        for i in range(3):
            try:
                if not self.redis:
                    raise RedisNotReadyException('[db]connection {} is not ready!!!'.format(self.db_desc()))

                ret = func(*args, **kwargs)
                now_sec = int(time.time())
                next_cnt = self.access_count.get(now_sec, 0) + 1
                self.access_count[now_sec] = next_cnt
                # print("func: {}, args: {}, kwargs: {}".format(func.__name__, args, kwargs))
                if next_cnt > self.access_count_max:
                    self.access_count_max = next_cnt
                    logger.info('[db]connection {} access max={}'.format(self.db_desc(), next_cnt))
                if next_cnt >= MAX_ACCESS_LIMIT:
                    logger.error('[db]connection {} access too fast... wait'.format(self.db_desc()))
                    time.sleep(now_sec + 1 - time.time())
                return ret
            except RedisCommandCheckError as e:
                raise e
            except redis.exceptions.NoScriptError as e:
                raise e
            except redis.exceptions.DataError as e:
                raise e
            except RedisNotReadyException as e:
                self.on_except()
                logger.info("{}".format(e))
                self.connect()
            except Exception as e:
                self.on_except()
                logger.error(trace_full())
                logger.error('[db]exception={} args={}'.format(e, args))
                self.connect()

        raise Exception("request redis is fail!")

    return decorate


class Connection:
    def __init__(self, host="127.0.0.1", port=6379, password=None, db=0):
        self.create_time = 0
        self.access_count = LRUCache(maxsize=MAX_ACCESS_COUNT_SECONDS_RECORD)
        self.access_count_max = 1000
        self.cfg = {"host": host, "port": port, "db": db, "password": password, "socket_keepalive": True}
        self.pool = None
        self.redis = None
        self.reconnecting = False
        self.connect()

    def db_desc(self):
        return "[{}:{}/{}]".format(self.cfg["host"], self.cfg["port"], self.cfg["db"])

    def on_except(self):
        if self.pool:
            self.pool.disconnect()
            self.pool = None

        self.redis = None
        self.reconnecting = False

    def connect(self):
        while self.redis is None:
            while self.reconnecting:
                logger.info('[db]reconnecting to {} is still in process, just wait.'.format(self.db_desc()))
                time.sleep(DB_RECONNECT_DELAY)

            if self.redis:
                return

            try:
                self.reconnecting = True
                while True:
                    dif = abs(time.time() - self.create_time)
                    if dif >= DB_RECONNECT_DELAY:
                        break

                    wait = DB_RECONNECT_DELAY - dif
                    logger.info('[db]reconnect to {} need wait {} seconds'.format(self.db_desc(), wait))
                    time.sleep(wait)

                self.create_time = time.time()
                logger.info('[db]connecting to {}.'.format(self.db_desc()))
                self.pool = _shared_pool(**self.cfg)
                self.redis = redis.StrictRedis(connection_pool=self.pool)
                key = 'redis_db_test_key'
                self.redis.set(key, self.create_time)
                v = self.redis.get('redis_db_test_key')
                if not v:
                    raise Exception("test db error")

                self.reconnecting = False
                print('[db]connect to {} success'.format(self.db_desc()))
            except Exception as e:
                logger.error('[db]connect to {} exception={}'.format(self.db_desc(), e))
                self.on_except()

    def __getattr__(self, name):
        if hasattr(self.redis, name):
            return db_check(partial(getattr(self.redis, name), _cls=self))
        else:
            super().__getattribute__(name)


class ConnectionManager:
    _connections = {}

    @staticmethod
    def get(host="127.0.0.1", port=6379, password=None, db=0):
        _key = "{}:{}/{}".format(host, port, db)
        if _key in ConnectionManager._connections:
            return ConnectionManager._connections[_key]

        _conn = Connection(host=host, port=port, password=password, db=db)
        ConnectionManager._connections[_key] = _conn
        return _conn
