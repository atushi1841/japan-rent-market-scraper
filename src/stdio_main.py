#!/usr/bin/env python3
"""MCP stdio server for io.github.atushi1841/japan-rent-market-mcp."""
import json
import sys

ACTOR_URL = "https://apify.com/fruitful_quintessence/japan-rent-market-scraper"
GUMROAD_URL = "https://atushi5.gumroad.com/l/kutuxe"

SERVER_INFO = {"name": "io.github.atushi1841/japan-rent-market-mcp", "version": "1.0.0"}
TOOLS = [{
    "name": "japan_rent_market_mcp_search",
    "description": "3-site rental cross-shop comparison (SUUMO + at home + LIFULL HOME'S).",
    "inputSchema": {"type": "object", "properties": {}}
}]


def send_msg(obj):
    msg = json.dumps(obj, ensure_ascii=False)
    header = f"Content-Length: {len(msg.encode())}\\r\\n\\r\\n"
    sys.stdout.buffer.write((header + msg).encode())
    sys.stdout.buffer.flush()


def main():
    buf = b""
    while True:
        data = sys.stdin.buffer.read(4096)
        if not data: break
        buf += data
        while b"{" in buf:
            start = buf.find(b"{")
            depth = 0
            end = -1
            for i in range(start, len(buf)):
                if buf[i:i+1] == b"{":
                    depth += 1
                elif buf[i:i+1] == b"}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > 0:
                raw = buf[start:end]
                buf = buf[end:]
                try:
                    req = json.loads(raw)
                    m = req.get("method", "")
                    resp = {}
                    if m == "initialize":
                        resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
                    elif m == "tools/list":
                        resp = {"tools": TOOLS}
                    elif m == "tools/call":
                        tname = req["params"].get("name", "")
                        args = req["params"].get("arguments", {})
                        if tname == "japan_rent_market_mcp_search":
                            resp = {"content": [{"type": "text", "text": f"Apify actor: {ACTOR_URL}\\nArguments: {json.dumps(args, ensure_ascii=False)}\\nGumroad: {GUMROAD_URL}"}]}
                    if "id" in req and resp:
                        send_msg({"jsonrpc": "2.0", "id": req["id"], "result": resp})
                except Exception:
                    pass
            else:
                break


if __name__ == "__main__":
    main()
