import os
import mimetypes
import base64

DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

MIME_MAP = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".map": "application/json"
}

def get_content_type(file_path):
    _, ext = os.path.splitext(file_path)
    return MIME_MAP.get(ext.lower(), mimetypes.guess_type(file_path)[0] or "application/octet-stream")

def lambda_handler(event, context):
    """
    Serves Single-Page Application (SPA) static frontend files directly through API Gateway.
    Handles root path, assets, and fallback routing to index.html.
    """
    raw_path = event.get("rawPath") or event.get("path") or "/"
    
    # Strip stage prefix if present (e.g., /prod or /dev)
    if raw_path.startswith("/prod"):
        raw_path = raw_path[5:] or "/"
    elif raw_path.startswith("/dev"):
        raw_path = raw_path[4:] or "/"

    # Normalize clean relative path
    rel_path = raw_path.lstrip("/")
    
    # If empty or root, serve index.html
    if not rel_path:
        rel_path = "index.html"
        
    target_file = os.path.join(DIST_DIR, rel_path)
    
    # Fallback to index.html for SPA client-side routing if file doesn't exist
    if not os.path.isfile(target_file):
        target_file = os.path.join(DIST_DIR, "index.html")
        rel_path = "index.html"
        
    if not os.path.isfile(target_file):
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "text/plain"},
            "body": "Frontend dist/index.html not found. Please build the frontend first."
        }
        
    content_type = get_content_type(target_file)
    is_binary = any(content_type.startswith(b) for b in ["image/", "font/", "audio/", "video/", "application/octet-stream", "application/vnd.ms-fontobject"])
    
    # Cache headers: long cache for fingerprinted assets, no-cache for index.html
    cache_control = "public, max-age=31536000, immutable" if "/assets/" in rel_path or "assets" in rel_path else "no-cache, no-store, must-revalidate"
    
    headers = {
        "Content-Type": content_type,
        "Cache-Control": cache_control,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS"
    }
    
    if is_binary:
        with open(target_file, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        return {
            "statusCode": 200,
            "headers": headers,
            "isBase64Encoded": True,
            "body": b64_data
        }
    else:
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {
            "statusCode": 200,
            "headers": headers,
            "isBase64Encoded": False,
            "body": content
        }
