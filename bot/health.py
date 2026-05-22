from aiohttp import web
from rag.chain import check_ollama_health

async def health_handler(request):
    checks = {
        "ollama": await check_ollama_health(),
        "storage": True,  # TODO: ping postgres later
    }
    status = 200 if all(checks.values()) else 503
    return web.json_response({"status": "ok" if status == 200 else "degraded", "checks": checks}, status=status)

async def start_health_server(port: int = 8080):
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner
