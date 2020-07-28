import multiprocessing
from os import environ as env


PORT = int(env.get("PORT", 8088))
DEBUG_MODE = int(env.get("DEBUG_MODE", 1))

# Gunicorn config
bind = ":" + str(PORT)
workers = multiprocessing.cpu_count() * 2 + 1
workers = 1
threads = 2 * multiprocessing.cpu_count()
threads = 2
