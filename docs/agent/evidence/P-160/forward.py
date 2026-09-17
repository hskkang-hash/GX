"""Tiny TCP forwarder: 0.0.0.0:<port> -> gx-shell:<port> for 3002 and 8000 (probe only, removed after)."""
import asyncio


async def pipe(r, w):
    try:
        while True:
            b = await r.read(65536)
            if not b:
                break
            w.write(b)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def handle(port, cr, cw):
    try:
        sr, sw = await asyncio.open_connection("gx-shell", port)
    except Exception:
        cw.close()
        return
    await asyncio.gather(pipe(cr, sw), pipe(sr, cw))


async def main():
    servers = []
    for port in (3002, 8000):
        servers.append(await asyncio.start_server(lambda r, w, p=port: handle(p, r, w), "0.0.0.0", port))
    await asyncio.gather(*(s.serve_forever() for s in servers))


asyncio.run(main())
