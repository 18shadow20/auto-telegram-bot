import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
BASE_URL = "https://cars.av.by/"