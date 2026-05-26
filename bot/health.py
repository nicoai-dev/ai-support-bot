from aiohttp import web
from rag.chain import check_ollama_health
import logging


async def health_handler(request):
    """Healthcheck endpoint — возвращает состояние компонентов."""
    checks = {
        "llm": await check_ollama_health(),
        "storage": True,  # TODO: ping postgres/redis
    }
    status = 200 if all(checks.values()) else 503
    return web.json_response(
        {"status": "ok" if status == 200 else "degraded", "checks": checks},
        status=status,
    )


async def start_health_server(port: int = 8080):
    """Запустить HTTP-сервер для healthcheck.
    
    БЕЗОПАСНОСТЬ: Слушаем только на 127.0.0.1 (внутри Docker-сети).
    Для внешнего доступа используется Docker healthcheck через CMD.
    """
    app = web.Application()
    app.router.add_get("/health", health_handler)
    # Prometheus метрики
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        
        async def metrics_handler(request):
            return web.Response(
                body=generate_latest(),
                content_type=CONTENT_TYPE_LATEST,
            )
        
        app.router.add_get("/metrics", metrics_handler)
        logging.info("📊 Prometheus метрики доступны на /metrics")
    except ImportError:
        logging.warning("⚠️ prometheus-client не установлен — метрики отключены")
    runner = web.AppRunner(app)
    await runner.setup()
    # ВАЖНО: Слушаем ТОЛЬКО на localhost, не на 0.0.0.0
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    logging.info(f"⚕️ Healthcheck server запущен на 127.0.0.1:{port}")
    return runner
