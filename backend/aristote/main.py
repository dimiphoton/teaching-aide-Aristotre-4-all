"""Application FastAPI du kiosque : API, WebSocket et interface (fichiers statiques).

Lancement : `aristote serve` (ou `uvicorn aristote.main:app`).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from . import __version__
from .api.context import KioskContext, build_context
from .api.routes import router, ws_router
from .config import Config, load_config
from .hardware.base import ButtonPress
from .tutor.curriculum import course_summary

log = logging.getLogger(__name__)


async def _housekeeping(c: KioskContext) -> None:
    """Fin de session sur inactivité (toutes les 15 s) et purge du corpus d'évaluation (toutes les 24 h)."""
    ticks = 0
    while True:
        await asyncio.sleep(15)
        try:
            c.manager.check_idle()
            ticks += 1
            if ticks % (24 * 240) == 1:
                await asyncio.to_thread(c.corpus.purge)
        except Exception:  # noqa: BLE001 - la boucle de maintenance ne doit jamais mourir
            log.exception("maintenance")


def create_app(config: Config | None = None, context: KioskContext | None = None) -> FastAPI:
    config = config or load_config()
    c = context or build_context(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        c.bus.bind_loop(loop)

        def on_press(press: ButtonPress) -> None:  # appelé depuis un thread gpiozero
            loop.call_soon_threadsafe(c.manager.handle_press, press)

        c.hardware.buttons.start(on_press)
        c.hardware.leds.set_active(None)
        c.store.write_kiosk_status({
            "version": __version__, "demarrage": datetime.now().astimezone().isoformat(timespec="seconds"),
            "cours": c.curriculum.id, "llm": c.config.llm.model if c.llm_mode == "api" else c.llm_mode,
            "ocr": c.ocr.name, "stt": c.stt.name, "camera": c.hardware.camera is not None,
            "imprimante": c.printer.available, "micro": c.hardware.microphone is not None,
        })
        c.store.write_note("cours.md", *course_summary(c.curriculum))
        task = asyncio.create_task(_housekeeping(c))
        log.info("kiosque %s prêt (%s)", c.config.kiosk.id, c.llm_mode)
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            c.manager.shutdown()
            c.hardware.close()
            aclose = getattr(c.llm, "aclose", None)
            if aclose:
                await aclose()

    app = FastAPI(title="Aristote 4 All", version=__version__, lifespan=lifespan)
    app.state.ctx = c
    app.include_router(router)
    app.include_router(ws_router)

    dist = config.frontend.dist_dir
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = (dist / path).resolve()
        if path and target.is_file() and dist.resolve() in target.parents:
            return FileResponse(target)
        if index.exists():
            return FileResponse(index)  # application monopage : toutes les routes renvoient index.html
        return JSONResponse({"detail": "Interface non compilée : lancer `make frontend`."}, status_code=503)

    return app


def __getattr__(name: str):
    # `uvicorn aristote.main:app` : l'application n'est construite qu'à la demande.
    if name == "app":
        return create_app()
    raise AttributeError(name)

