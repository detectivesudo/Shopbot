import requests
import json
import re
import argparse
import webbrowser
from urllib.parse import urlparse

# -----------------------------------
# Extract store + handle from URL
# -----------------------------------
def get_store_and_handle(url):
    parsed = urlparse(url)
    store_url = f"{parsed.scheme}://{parsed.netloc}"
    handle = parsed.path.split("/")[-1]
    return store_url, handle


# -----------------------------------
# Try Shopify product JSON
# -----------------------------------
def fetch_product_json(store_url, handle):
    url = f"{store_url}/products/{handle}.json"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        try:
            return r.json().get("product")
        except:
            return None
    return None


# -----------------------------------
# Fallback HTML scraper
# -----------------------------------
def fallback_scrape(store_url, handle):
    url = f"{store_url}/products/{handle}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    html = r.text

    # Theme 1
    pattern1 = re.search(r'var\s+product\s*=\s*({.*?});', html, re.DOTALL)

    # Theme 2
    pattern2 = re.search(r'product:\s*({.*?})\s*,\s*currentVariant', html, re.DOTALL)

    data = None
    if pattern1:
        data = pattern1.group(1)
    elif pattern2:
        data = pattern2.group(1)

    if not data:
        raise RuntimeError("Could not extract product JSON from HTML theme.")

    return json.loads(data)


# -----------------------------------
# Build checkout link
# -----------------------------------
def build_checkout_link(store_url, variant_id, qty=1):
    return f"{store_url}/cart/{variant_id}:{qty}"


# -----------------------------------
# POST carting (bot style)
# -----------------------------------
def post_cart(store_url, variant_id, qty=1):
    url = f"{store_url}/cart/add.js"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "id": variant_id,
        "quantity": qty
    }
    r = requests.post(url, headers=headers, data=data)
    try:
        return r.json()
    except:
        return {"error": "Bad response", "raw": r.text}


# -----------------------------------
# Main workflow
# -----------------------------------
def cart_from_product(product_url, qty=1, open_browser=False, use_post=False):
    store_url, handle = get_store_and_handle(product_url)

    product = fetch_product_json(store_url, handle)
    if not product:
        product = fallback_scrape(store_url, handle)

    title = product.get("title", "Product")
    variants = product.get("variants", [])

    if not variants:
        raise RuntimeError("No variants found for product.")

    print(f"\n=== {title} ===\n")

    # Print variant list
    for idx, v in enumerate(variants):
        print(f"{idx+1}. {v['title']}  |  ID: {v['id']}  | Price: {v.get('price')}")

    # Choose a variant
    choice = int(input("\nChoose a variant number: "))
    chosen = variants[choice - 1]
    variant_id = chosen["id"]

    print(f"\nSelected: {chosen['title']} (ID {variant_id})")

    # POST-based bot-style add
    if use_post:
        print("\nSending POST cart request...")
        res = post_cart(store_url, variant_id, qty)
        print("Response:", res)

    # Build checkout link
    link = build_checkout_link(store_url, variant_id, qty)
    print("\nCheckout link:")
    print(link)

    if open_browser:
        print("\nOpening in browser...")
        webbrowser.open(link)

    return link


# -----------------------------------
# CLI
# -----------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopify Carting Script")
    parser.add_argument("url", help="Shopify product URL")
    parser.add_argument("--qty", type=int, default=1, help="Quantity")
    parser.add_argument("--open", action="store_true", help="Open checkout in browser")
    parser.add_argument("--post", action="store_true", help="Use POST add-to-cart")
    args = parser.parse_args()

    cart_from_product(args.url, args.qty, args.open, args.post)
