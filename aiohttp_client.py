# -*- coding: utf-8 -*-
# @Explain  : http client异步库
# @Time     : 2021/01/21 14:30 
# @Author   : tide
# @FileName : client

import os
import ssl

import aiohttp
import json as _json
from collections.abc import Mapping
from urllib3.fields import RequestField
from urllib3.filepost import encode_multipart_formdata
from requests.utils import super_len


basestring = (bytes, str)


class cached_property(object):
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, type=None):
        if instance is None:
            return self

        res = instance.__dict__[self.name] = self.func(instance)
        return res


class FetcherContent(object):
    def __init__(self, kwargs):
        self.content = None
        self.status = 500
        self.__dict__.update(kwargs)

    @cached_property
    def json(self):
        return _json.loads(self.content)

    @property
    def text(self):
        return self.content.decode()

    @property
    def status_code(self):
        return self.status

    def is_json(self):
        try:
            _ = self.json
            return True
        except _json.decoder.JSONDecodeError:
            return False


def to_key_val_list(value):
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError('cannot encode objects that are not 2-tuples')

    if isinstance(value, Mapping):
        value = value.items()

    return list(value)


def guess_filename(obj):
    """Tries to guess the filename of the given object."""
    name = getattr(obj, 'name', None)
    if (name and isinstance(name, basestring) and name[0] != '<' and
            name[-1] != '>'):
        return os.path.basename(name)


def _encode_files(files, data):
    """Build the body for a multipart/form-data request.

    The tuples may be 2-tuples (filename, fileobj), 3-tuples (filename, fileobj, contentype)
    or 4-tuples (filename, fileobj, contentype, custom_headers).
    """
    if not files:
        raise ValueError("Files must be provided.")
    elif isinstance(data, basestring):
        raise ValueError("Data must not be a string.")

    new_fields = []
    fields = to_key_val_list(data or {})
    files = to_key_val_list(files or {})

    for field, val in fields:
        if isinstance(val, basestring) or not hasattr(val, '__iter__'):
            val = [val]
        for v in val:
            if v is not None:
                if not isinstance(v, bytes):
                    v = str(v)

                new_fields.append(
                    (field.decode('utf-8') if isinstance(field, bytes) else field,
                     v.encode('utf-8') if isinstance(v, str) else v))

    for (k, v) in files:
        # support for explicit filename
        ft = None
        fh = None
        if isinstance(v, (tuple, list)):
            if len(v) == 2:
                fn, fp = v
            elif len(v) == 3:
                fn, fp, ft = v
            else:
                fn, fp, ft, fh = v
        else:
            fn = guess_filename(v) or k
            fp = v

        if isinstance(fp, (str, bytes, bytearray)):
            fdata = fp
        elif hasattr(fp, 'read'):
            fdata = fp.read()
        elif fp is None:
            continue
        else:
            fdata = fp

        rf = RequestField(name=k, data=fdata, filename=fn, headers=fh)
        rf.make_multipart(content_type=ft)
        new_fields.append(rf)

    body, content_type = encode_multipart_formdata(new_fields)

    return body, content_type


def prepare_content_length(body, method, headers):
    """Prepare Content-Length header based on request method and body"""
    _method = method.upper()
    if body is not None:
        length = super_len(body)
        if length:
            headers['Content-Length'] = str(length)
    elif _method not in ('GET', 'HEAD') and headers.get('Content-Length') is None:
        headers['Content-Length'] = '0'


async def fetch(url, method="get", params=None, data=None, json=None, files=None, auth=None, cert=None, cookies=None,
                headers=None, timeout=None, try_count=3):
    """异步发送http请求
    params: http query string
    body: 值为dict类型，会自动json dumps
    timeout: 值为元组时，兼容 requests的timeout  let: (conn_timeout, read_timeout)
    try_count: http状态码不在200-207之间，进行尝试次数，默认3次

    Example::
        async def send_request():
            url = "http://localhost:9004/"
            headers = {'content-type': 'application/text'}
            body = {"a": 1, "b": 2}
            resp = await fetch(url, method="post", json=body, headers=headers, timeout=(3, 6))
            return resp

    """
    # 支持files参数
    content_type = None
    headers = headers if headers else {}
    data = data if data else None
    session_params = {}
    if files:
        (body, content_type) = _encode_files(files, data)
        prepare_content_length(body, method=method, headers=headers)
        data = body

    if content_type and ('content-type' not in headers):
        headers['Content-Type'] = content_type

    # auth 实现 BasicAuth
    if auth:
        auth_username, auth_password = auth
        session_params["auth"] = aiohttp.BasicAuth(login=auth_username, password=auth_password)

    # ssl cert证书
    if cert:
        cert_file, key_file = cert
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        session_params["connector"] = aiohttp.TCPConnector(ssl_context=ssl_context)

    # 过滤空值
    _kwargs = {"params": params, "data": data, "json": json, "cookies": cookies,
               "headers": headers, "timeout": timeout}
    _kwargs = {k: v for k, v in _kwargs.items() if v}

    # 由于aiohttp timeout参数不支持元组，需特殊处理
    if isinstance(timeout, (tuple, list)):
        conn_timeout, read_timeout = timeout
        session_params["timeout"] = aiohttp.ClientTimeout(sock_connect=conn_timeout, sock_read=read_timeout)
        _kwargs.pop("timeout", None)

    # 异步处理请求http
    async with aiohttp.ClientSession(**session_params) as session:
        fetch_func = getattr(session, method.lower())
        success_codes = tuple(range(200, 207))
        obj = {"status": 500}
        for i in range(try_count):
            async with fetch_func(url, **_kwargs) as response:
                content = await response.content.read()
                obj.update({"status": response.status, "headers": response.headers, "content": content})
                if response.status not in success_codes:
                    continue

                break

        return FetcherContent(obj)
