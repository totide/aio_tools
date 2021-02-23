
aiohttp_client： 异步http client


```
"""aiohttp像requests一样使用"""
import aiohttp_client


async def request_url():
    headers = {"version": "1.0.0"}
    payloads = {"remark": ""}
    img = "D:\\a.png"
    files = {"image": (img, open(img, 'rb'), 'image/png')}
    resp = await aiohttp_client.fetch(url, method="post", data=payloads, headers=headers, files=files, timeout=3)
    return resp

```
```
"""树状结构，获取父节点"""
import numpy
import pandas

a = [[1, 'b', 4, 2], [2, 'a', 3, 2], [3, 'c', 3, 2], [4, 'b', 3, 2], [5, 'b', 3, 2],
     [6, 'a', 5, 3], [7, 'a', 9, 3], [8, 'a', 9, 2], [9, 'a', 9, 3], [10, 'a', 11, 3]]

ps = pandas.DataFrame(a, columns=["id", "bid", "pid", "level"])
f_ps = ps[(ps["bid"] == 'a') & (ps["level"] == 3)]
for index, item in f_ps.iterrows():
    p_node = ps[(ps["id"] == item["pid"]) & (ps["level"] == 2)]
    if not p_node.empty:
        p_array = numpy.array(p_node).tolist()

```

```
"""redis连接类兼性能分析"""
import timeit
import cProfile
from memory_profiler import profile
from common.redis.pool import ConnectionManager

conn = ConnectionManager.get(**{"host": '39.108.49.166', "port": 40002})
# 语句调用栈执行时长性能分析
cProfile.run('conn.keys("demo:x_1")')
# 内存分析
profile(conn.getset)("demo:x_1", "a")
# 语句执行时长
print(timeit.timeit('conn.get("demo:x_1")', setup="""from __main__ import conn""", number=1))

```

