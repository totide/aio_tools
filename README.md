
aiohttp_client： 异步http client


```

import aiohttp_client


async def request_url():
    headers = {"version": "1.0.0"}
    payloads = {"remark": ""}
    img = "D:\\a.png"
    files = {"image": (img, open(img, 'rb'), 'image/png')}
    resp = await aiohttp_client.fetch(url, method="post", data=payloads, headers=headers, files=files, timeout=3)
    return resp


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
