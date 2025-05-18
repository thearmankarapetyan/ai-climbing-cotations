import os
from os.path import abspath, dirname, join

from dotenv import load_dotenv

dotenv_path = join(dirname(abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path)

postgresql_config = {
    "host": os.getenv("HNAME"),
    "user": os.getenv("HUSER"),
    "password": os.getenv("HPASSWORD"),
    "database": os.getenv("HDATABASE"),
    "port": os.getenv("HPORT")
}
