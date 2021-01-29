# aio_tools
异步工具库


############################################ aiohttp支持了requests库大部分参数####################################################################

import aiohttp_client


async def request_url():
    headers = {"version": "1.0.0"}
    payloads = {"remark": ""}
    img = "D:\\a.png"
    files = {"image": (img, open(img, 'rb'), 'image/png')}
    resp = await aiohttp_client.fetch(url, method="post", data=payloads, headers=headers, files=files, timeout=3)
    return resp


