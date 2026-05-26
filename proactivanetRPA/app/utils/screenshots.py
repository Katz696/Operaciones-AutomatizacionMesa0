import os
import time
from app.utils.logger import log

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def take_screenshot(page, name):
    path = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    page.screenshot(path=path)
    log("info", "Screenshot taken", path=path)