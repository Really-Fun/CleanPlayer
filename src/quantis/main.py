import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from quantis.core.bootstrap import build_application, shutdown_application
from quantis.core.async_bridge import AsyncBridge
from quantis.ui import Quantis


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)
    logger.info(
        """
    --------------
    Quantis v0.1.1
    --------------
        """
    )

    app = QApplication(sys.argv)
    bridge = AsyncBridge()
    bridge.setParent(app)
    bundle = build_application(bridge)
    from quantis.plugins import PluginRegistry

    bridge.schedule(PluginRegistry.instance().load_all(bundle.plugin_host))
    window = Quantis(bundle)
    window.show()

    if os.environ.get("QUANTIS_ENABLE_ADAPTER", "1").lower() in ("1", "true", "yes"):
        from quantis.adapter import CleanAdapter

        try:
            CleanAdapter(
                player=bundle.player,
                event_bus=bundle.event_bus,
                path_provider=bundle.music.provider,
                bridge=bridge,
            )
        except Exception:
            logger.exception("Системная интеграция плеера недоступна")

    try:
        sys.exit(app.exec())
    finally:
        shutdown_application(bundle)
        bridge.shutdown()


if __name__ == "__main__":
    main()
