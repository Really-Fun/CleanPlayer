import asyncio
import logging
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from quantis.adapter import CleanAdapter
from quantis.core import init_app_context
from quantis.services import TrackHistoryService
from quantis.ui import Quantis


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
            # logging.FileHandler("app.log")
        ],
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
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    app_context = init_app_context(loop)

    window = Quantis(loop)
    window.show()

    CleanAdapter(app_context)

    with loop:
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(TrackHistoryService().close())

if __name__ == "__main__":
    main()