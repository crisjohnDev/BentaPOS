import os
import sys
import threading
import time
import logging
import traceback


# =========================================================
# APPLICATION PATH
# =========================================================

if getattr(sys, "frozen", False):

    # When running the PyInstaller EXE
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS

else:

    # When running normally with Python
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR


# =========================================================
# USER-WRITABLE DATA DIRECTORY
# =========================================================

# Do NOT store writable files such as logs/database
# inside C:\Program Files\BentaPOS\
#
# LOCALAPPDATA is writable by the current Windows user.

DATA_DIR = os.path.join(
    os.environ.get(
        "LOCALAPPDATA",
        os.path.expanduser("~")
    ),
    "BentaPOS"
)

os.makedirs(DATA_DIR, exist_ok=True)


# =========================================================
# ERROR LOGGING
# =========================================================

LOG_FILE = os.path.join(
    DATA_DIR,
    "error.log"
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    encoding="utf-8",
)

logger = logging.getLogger(__name__)


# =========================================================
# EXCEPTION LOGGER
# =========================================================

def log_exception():

    try:

        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write("\n\n")
            file.write("=" * 70)
            file.write("\nAPPLICATION ERROR\n")
            file.write("=" * 70)
            file.write("\n")

            traceback.print_exc(file=file)

    except Exception:

        # Prevent logging failure from causing another crash
        pass


# =========================================================
# MAKE SURE DJANGO CAN FIND THE PROJECT
# =========================================================

os.chdir(APP_DIR)

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


# =========================================================
# DJANGO SETUP
# =========================================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

try:

    import django

    django.setup()

except Exception:

    logger.exception(
        "Django setup failed"
    )

    log_exception()

    raise


# =========================================================
# DJANGO IMPORTS
# =========================================================

try:

    from config.wsgi import application
    from django.core.management import call_command

except Exception:

    logger.exception(
        "Failed to load Django WSGI application"
    )

    log_exception()

    raise


# =========================================================
# PYWEBVIEW / WAITRESS
# =========================================================

import webview

from waitress import serve


# =========================================================
# SERVER CONFIGURATION
# =========================================================

HOST = "127.0.0.1"
PORT = 8000


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    try:

        logger.info(
            "Starting database migration..."
        )

        call_command(
            "migrate",
            interactive=False,
        )

        logger.info(
            "Database migration completed successfully."
        )

    except Exception:

        logger.exception(
            "Database migration failed."
        )

        log_exception()


# =========================================================
# DJANGO SERVER
# =========================================================

def start_server():

    try:

        logger.info(
            f"Starting Waitress server on {HOST}:{PORT}"
        )

        serve(
            application,
            host=HOST,
            port=PORT,
            threads=4,
        )

    except Exception:

        logger.exception(
            "Waitress server failed."
        )

        log_exception()


# =========================================================
# MAIN
# =========================================================

def main():

    try:

        logger.info("=" * 70)
        logger.info("Starting BentaPOS")
        logger.info(f"APP_DIR: {APP_DIR}")
        logger.info(f"BUNDLE_DIR: {BUNDLE_DIR}")
        logger.info(f"DATA_DIR: {DATA_DIR}")
        logger.info(f"LOG_FILE: {LOG_FILE}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info("=" * 70)


        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        initialize_database()


        # -------------------------------------------------
        # START WAITRESS
        # -------------------------------------------------

        server_thread = threading.Thread(
            target=start_server,
            daemon=True,
        )

        server_thread.start()


        # -------------------------------------------------
        # GIVE WAITRESS TIME TO START
        # -------------------------------------------------

        time.sleep(2)


        # -------------------------------------------------
        # PYWEBVIEW WINDOW
        # -------------------------------------------------

        logger.info(
            f"Opening http://{HOST}:{PORT}"
        )

        window = webview.create_window(
            "BentaPOS",
            f"http://{HOST}:{PORT}",
            width=1280,
            height=800,
            min_size=(1000, 650),
            resizable=True,
            fullscreen=False,
        )

        webview.start()

        logger.info(
            "PyWebView closed."
        )


    except Exception:

        logger.exception(
            "Fatal application error."
        )

        log_exception()

        raise


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()