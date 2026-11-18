#!/usr/bin/env python3
import argparse
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HOST = "https://app.kiro.dev/"


def cbor_text(value):
    raw = value.encode()
    n = len(raw)
    if n < 24:
        return bytes([0x60 + n]) + raw
    if n < 256:
        return bytes([0x78, n]) + raw
    return bytes([0x79, (n >> 8) & 255, n & 255]) + raw


def cbor_map(items):
    out = bytes([0xA0 + len(items)])
    for key, value in items:
        out += cbor_text(key) + value
    return out


def cbor_array(items):
    return bytes([0x80 + len(items)]) + b"".join(items)


def cookie_value(cookie, name):
    prefix = name + "="
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith(prefix):
            return part[len(prefix):]
    sys.exit(f"missing {name}")


def request(url, cookie, data=None, headers=None, timeout=60):
    hdrs = {"Cookie": cookie, "User-Agent": "Mozilla/5.0"}
    if headers:
        hdrs.update(headers)
    req = Request(url, data=data, headers=hdrs, method="POST" if data is not None else "GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def portal(cookie, csrf, token, op, body, timeout):
    return request(
        HOST + "service/KiroWebPortalService/operation/" + op,
        cookie,
        body,
        {
            "Authorization": "Bearer " + token,
            "X-CSRF-Token": csrf,
            "Content-Type": "application/cbor",
            "Accept": "application/vnd.amazon.eventstream",
            "smithy-protocol": "rpc-v2-cbor",
        },
        timeout,
    )


def meta(html, name):
    match = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
    return match.group(1) if match else ""


def refresh(cookie, csrf):
    code, raw = request(
        HOST + "service/KiroWebPortalService/operation/RefreshToken",
        cookie,
        cbor_map([("csrfToken", cbor_text(csrf))]),
        {
            "X-CSRF-Token": csrf,
            "Content-Type": "application/cbor",
            "Accept": "application/cbor",
            "smithy-protocol": "rpc-v2-cbor",
        },
    )
    text = raw.decode("utf-8", "replace")
    access = re.search(r"aoa[A-Za-z0-9_:+/=-]{20,}", text)
    renewed = re.search(r"aor[A-Za-z0-9_:+/=-]{20,}", text)
    if code != 200 or not access:
        sys.exit(f"refresh failed {code}")
    cookie = re.sub(r"AccessToken=[^;]*", "AccessToken=" + access.group(0), cookie, count=1)
    if renewed:
        cookie = re.sub(r"RefreshToken=[^;]*", "RefreshToken=" + renewed.group(0), cookie, count=1)
    return cookie


def show(raw):
    text = raw.decode("utf-8", "replace")
    outputs = re.findall(r"Output:\\n(.*?)(?:\\n\\n\\nExit Code:|\\nExit Code:)", text)
    if outputs:
        print(outputs[-1].encode().decode("unicode_escape"), end="" if outputs[-1].endswith("\n") else "\n")
        return
    for line in ("HTTP/2 200", "HTTP/2 404", "HTTP/1.1 200", "ERR_ACCESS_DENIED"):
        if line in text:
            print(line)
            return
    print("no-output")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie", default="")
    parser.add_argument("--cookie-file", default="")
    parser.add_argument("--trace", default="")
    parser.add_argument("--prompt", default="Reply with hello.")
    args = parser.parse_args()
    cookie = args.cookie
    if args.cookie_file:
        raw = open(args.cookie_file, encoding="utf-8", errors="replace").read().strip()
        if "\t" in raw:
            pairs = []
            for line in raw.splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    pairs.append(parts[5] + "=" + parts[6])
            cookie = "; ".join(pairs)
        else:
            cookie = raw
    if args.trace:
        trace = open(args.trace, encoding="utf-8", errors="replace").read()
        found = re.search(r"(?m)^> Cookie: (.+)$", trace)
        if not found:
            sys.exit("no cookie in trace")
        cookie = found.group(1).strip()
    if not cookie:
        sys.exit("missing cookie")
    code, page = request(HOST, cookie)
    if code != 200:
        sys.exit(f"page {code}")
    html = page.decode("utf-8", "replace")
    csrf = meta(html, "csrf-token")
    if meta(html, "user-status") == "stale":
        cookie = refresh(cookie, csrf)
        _, page = request(HOST, cookie)
        html = page.decode("utf-8", "replace")
        csrf = meta(html, "csrf-token")
    token = cookie_value(cookie, "AccessToken")
    code, raw = portal(
        cookie,
        csrf,
        token,
        "CreateSpace",
        cbor_map([("csrfToken", cbor_text(csrf)), ("spaceType", cbor_text("VIBE"))]),
        60,
    )
    text = raw.decode("utf-8", "replace")
    space = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    if code != 200 or not space:
        sys.exit(f"create {code}")
    space = space.group(0)
    block = cbor_map([("text", cbor_map([("text", cbor_text(args.prompt))]))])
    code, raw = portal(
        cookie,
        csrf,
        token,
        "StreamSendMessage",
        cbor_map([
            ("csrfToken", cbor_text(csrf)),
            ("spaceId", cbor_text(space)),
            ("sessionId", cbor_text(space)),
            ("routingSessionId", cbor_text(space)),
            ("contentBlocks", cbor_array([block])),
        ]),
        180,
    )
    if code != 200:
        sys.exit(f"send {code}")
    show(raw)


if __name__ == "__main__":
    main()
