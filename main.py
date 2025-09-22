from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from decimal import Decimal, ROUND_HALF_UP
import os, re, json, requests, time
import grpc
from urllib.parse import urljoin

# gRPC health (requires grpcio-health-checking)
from grpc_health.v1 import health_pb2, health_pb2_grpc

# --- config & globals ---
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend").rstrip("/")
CATALOG_URL  = os.getenv("CATALOG_URL", "http://productcatalogservice:3550").rstrip("/")
ENABLE_SCRAPE = os.getenv("ENABLE_SCRAPE", "true").lower() == "true"
_cache = {"ts": 0, "items": None}

# --- app & router (define api BEFORE include_router) ---
app = FastAPI()
api = APIRouter(prefix="/api")

@app.get("/")
def root():
    return {"ok": True, "service": "ai-agent"}

# --- helpers ---
def _to_cents(v):
    # accepts 109.99, "109.99", "109", "$109.99"
    s = str(v).strip().replace("$", "")
    return int(Decimal(s).scaleb(2).to_integral_value(rounding=ROUND_HALF_UP))

def _abs_url(base, path):
    return urljoin(base.rstrip("/") + "/", str(path))

# --- health endpoints ---
@api.get("/health")
def health():
    return {"status": "ok"}

@api.get("/health/details")
def health_details():
    out = {}

    # 1) Frontend HTML
    try:
        r = requests.get(FRONTEND_URL, timeout=5)
        out["frontend_home"] = {"status": r.status_code, "ok": r.ok}
    except Exception as e:
        out["frontend_home"] = {"error": f"{type(e).__name__}: {e}"}

    # 2) Frontend JSON (Hipster Shop exposes /api/products on the frontend)
    try:
        r = requests.get(f"{FRONTEND_URL}/api/products", timeout=5)
        out["frontend_json"] = {"status": r.status_code, "ok": r.ok}
    except Exception as e:
        out["frontend_json"] = {"error": f"{type(e).__name__}: {e}"}

    # 3) Catalog service: gRPC health (document that HTTP probe is skipped)
    out["catalog_json"] = {"skipped": True, "reason": "catalog is gRPC, no HTTP probe"}
    try:
        # Strip http:// if provided in env
        target = CATALOG_URL.replace("http://", "").replace("https://", "")
        channel = grpc.insecure_channel(target)
        health_stub = health_pb2_grpc.HealthStub(channel)
        resp = health_stub.Check(
            health_pb2.HealthCheckRequest(service=""), timeout=5
        )
        if resp.status == health_pb2.HealthCheckResponse.SERVING:
            out["catalog_grpc"] = {"status": "SERVING", "ok": True}
        else:
            out["catalog_grpc"] = {"status": "NOT_SERVING", "ok": False}
    except Exception as e:
        out["catalog_grpc"] = {"error": f"{type(e).__name__}: {e}"}

    return out

# --- main API ---
@api.get("/recommend/{user_id}")
def recommend(user_id: str):
    sources = [
        ("frontend-json", f"{FRONTEND_URL}/api/products"),
        # Enable only if you add an HTTP/JSON shim for catalog:
        # ("catalog-json",  f"{CATALOG_URL}/products"),
    ]
    products = None
    last_err = None
    source_used = None

    # 1) Prefer JSON sources
    for name, url in sources:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "").lower()
                data = r.json() if "application/json" in ct else json.loads(r.text)
                items = data.get("products", data) if isinstance(data, dict) else data
                if isinstance(items, list) and items:
                    products = items
                    source_used = name
                    break
            else:
                last_err = f"{name} {url} -> HTTP {r.status_code}"
        except Exception as e:
            last_err = f"{name} {url} -> {type(e).__name__}: {e}"

    # 2) Fallback: scrape homepage “Hot Products”
    if not products and ENABLE_SCRAPE:
        now = time.time()
        if _cache["items"] and now - _cache["ts"] < 60:
            products = _cache["items"]
            source_used = "frontend-scrape(cache)"
        else:
            try:
                html = requests.get(
                    FRONTEND_URL, timeout=8, headers={"User-Agent": "ai-agent/1.0"}
                ).text
                pattern = re.compile(
                    r'<a\s+href="/product/([^"]+)"[\s\S]*?<img[^>]+src="([^"]+)"'
                    r'[\s\S]*?class="[^"]*(?:hot-product-card-name|product-name)[^"]*"[^>]*>([^<]+)</[^>]+>'
                    r'[\s\S]*?\$([0-9]+(?:\.[0-9]{2})?)',
                    re.I,
                )
                cards = pattern.findall(html)
                products = [
                    {
                        "id": pid,
                        "name": name.strip(),
                        "priceCents": _to_cents(price),
                        "picture": _abs_url(FRONTEND_URL, img),
                    }
                    for (pid, img, name, price) in cards
                ]
                source_used = "frontend-scrape"
                _cache["ts"], _cache["items"] = now, products
            except Exception as e:
                last_err = f"home-scrape {FRONTEND_URL} -> {type(e).__name__}: {e}"
                products = []

    if not products:
        note = "catalog temporarily unavailable"
        if last_err:
            note += f" ({last_err})"
        return JSONResponse(
            status_code=200,
            content={"user_id": user_id, "recommendations": [], "note": note},
        )

    # Normalize when JSON provided
    if source_used not in ("frontend-scrape", "frontend-scrape(cache)"):
        normalized = []
        for p in products:
            pid  = p.get("id") or p.get("itemId") or p.get("sku")
            name = p.get("name") or p.get("title")
            pic  = p.get("picture") or p.get("image") or p.get("pictureUrl") or ""
            pic  = _abs_url(FRONTEND_URL, pic)
            if "priceUsd" in p:
                price = p["priceUsd"]
                price_cents = int(price) if isinstance(price, int) else _to_cents(price)
            elif "price" in p:
                price_cents = _to_cents(p["price"])
            else:
                price_cents = int(p.get("priceCents", 0))
            if pid and name:
                normalized.append(
                    {"id": pid, "name": name, "priceCents": price_cents, "picture": pic}
                )
    else:
        normalized = products

    recs = [{**p, "priceUsd": p["priceCents"] / 100.0} for p in normalized[:3]]
    return {"user_id": user_id, "recommendations": recs, "source": source_used}

# register routes
app.include_router(api)