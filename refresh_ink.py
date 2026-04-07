#!/usr/bin/env python3
"""
Crypto price tracker for Waveshare 7.3inch e-Paper HAT (E) — 800x480, 6-color.

Fetches prices from api.maslanka.io and renders them with logos on the e-ink display.
Intended to run via crontab every 10 minutes on a Raspberry Pi.

See README.md for setup instructions, or run: bash setup.sh
"""

import sys
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure waveshare_epd is importable — check common locations if symlink is missing
_waveshare_paths = [
    os.path.join(SCRIPT_DIR, "e-Paper", "RaspberryPi_JetsonNano", "python", "lib"),
    os.path.expanduser("~/e-Paper/RaspberryPi_JetsonNano/python/lib"),
]
for _p in _waveshare_paths:
    if os.path.isdir(os.path.join(_p, "waveshare_epd")) and _p not in sys.path:
        sys.path.insert(0, _p)
        break

try:
    from waveshare_epd import epd7in3e
except ImportError:
    print("ERROR: waveshare_epd library not found.")
    print("Run: bash setup.sh  (or see README.md for manual setup)")
    sys.exit(1)

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = "https://api.maslanka.io"
COINS = ["BTC", "ETH", "SOL", "QUBIC"]
LOGO_DIR = os.path.join(SCRIPT_DIR, "logos")

# Display: 800 x 480
WIDTH = 800
HEIGHT = 480

# Layout: 4 rows, one per coin
ROW_H = 100
TOP_MARGIN = 20
LOGO_SIZE = 64


def fmt_price(ticker, value):
    """Format price string based on magnitude."""
    if ticker == "QUBIC":
        per_billion = value * 1_000_000_000
        return f"${per_billion:.0f}"
    elif value >= 1000:
        return f"${value:.0f}"
    elif value >= 1:
        return f"${value:.2f}"
    else:
        return f"${value:.4f}"


def fetch_prices():
    """Fetch current prices for all coins."""
    prices = {}
    for coin in COINS:
        try:
            resp = requests.get(f"{API_BASE}/{coin}", timeout=10)
            resp.raise_for_status()
            prices[coin] = float(resp.text.strip())
            log.info(f"{coin}: {prices[coin]}")
        except Exception as e:
            log.error(f"Failed to fetch {coin}: {e}")
            prices[coin] = None
    return prices


def load_logo(ticker):
    """Load and resize a coin logo."""
    path = os.path.join(LOGO_DIR, f"{ticker.lower()}.png")
    if not os.path.exists(path):
        log.warning(f"Logo not found: {path}")
        return None
    img = Image.open(path).convert("RGBA")
    img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
    return img


def render(prices):
    """Render the price display image."""
    # Fonts
    try:
        font_ticker = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_price = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        font_ticker = ImageFont.load_default()
        font_price = font_ticker
        font_footer = font_ticker

    canvas = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # e-Paper color constants
    BLACK = 0x000000
    RED = 0xff0000
    ORANGE = 0xff8000
    GREEN = 0x00ff00
    BLUE = 0x0000ff

    # Coin accent colors for the ticker labels
    COIN_COLORS = {
        "BTC": ORANGE,
        "ETH": BLUE,
        "SOL": GREEN,
        "QUBIC": RED,
    }

    for i, coin in enumerate(COINS):
        y = TOP_MARGIN + i * ROW_H

        # Separator line between rows
        if i > 0:
            draw.line([(20, y - 8), (WIDTH - 20, y - 8)], fill=BLACK, width=1)

        # Logo
        logo = load_logo(coin)
        logo_x = 30
        logo_y = y + (ROW_H - LOGO_SIZE) // 2 - 4
        if logo:
            canvas.paste(logo, (logo_x, logo_y), logo)
        else:
            draw.rectangle(
                (logo_x, logo_y, logo_x + LOGO_SIZE, logo_y + LOGO_SIZE),
                outline=BLACK, width=1,
            )

        # Ticker
        ticker_x = logo_x + LOGO_SIZE + 24
        ticker_y = y + ROW_H // 2 - 20
        label = "QUBIC (b)" if coin == "QUBIC" else coin
        draw.text((ticker_x, ticker_y), label, font=font_ticker, fill=COIN_COLORS.get(coin, BLACK))

        # Price
        price = prices.get(coin)
        if price is not None:
            price_str = fmt_price(coin, price)
            # Right-align price
            bbox = draw.textbbox((0, 0), price_str, font=font_price)
            price_w = bbox[2] - bbox[0]
            price_x = WIDTH - 40 - price_w
            price_y = y + ROW_H // 2 - 24
            draw.text((price_x, price_y), price_str, font=font_price, fill=BLACK)
        else:
            draw.text((WIDTH - 200, y + ROW_H // 2 - 14), "N/A", font=font_ticker, fill=RED)

    # Footer
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((20, HEIGHT - 38), f"Updated: {now}", font=font_footer, fill=BLACK)
    draw.text((WIDTH - 240, HEIGHT - 38), "api.maslanka.io", font=font_footer, fill=BLACK)

    return canvas


def main():
    log.info("Fetching prices...")
    prices = fetch_prices()

    log.info("Rendering display...")
    img = render(prices)

    log.info("Initializing e-Paper display...")
    epd = epd7in3e.EPD()
    epd.init()

    log.info("Sending image to display (~12s refresh)...")
    epd.display(epd.getbuffer(img))

    log.info("Putting display to sleep...")
    epd.sleep()
    log.info("Done.")


if __name__ == "__main__":
    main()
