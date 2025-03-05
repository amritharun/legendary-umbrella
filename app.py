from flask import Flask, render_template, request
import math
from db import db
from lib.sanitizer import sanitize_string
from lib.html_gen import get_html_table, get_html_visualization, get_pagination_html, error_dialog
from db.db import QUERY_TYPE
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

config = {
    "DEBUG": False,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
}

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100000 per day", "1000 per hour"],
    storage_uri="memory://",
)

app.config.from_mapping(config)
cache = Cache(app)


def make_cache_key(*args, **kwargs) -> str:
    """Generate a cache key based on the request path, query string, and body"""
    import hashlib

    path = request.path.encode()
    query = request.query_string
    body = request.get_data()

    return hashlib.md5(path + query + body).hexdigest()


@app.route("/")
@cache.cached(timeout=60)
def home() -> str:
    return render_template("home/index.html")

@app.route("/latest")
@cache.cached(timeout=60)
def latest() -> str:
    return render_template("latest/index.html")


@app.route("/historical")
@cache.cached(timeout=60)
def historical() -> str:
    return render_template("historical/index.html")


@app.route("/search-latest", methods=["POST"])
@cache.cached(timeout=60, key_prefix=make_cache_key)
def search_latest() -> str:
    query_type = QUERY_TYPE.LATEST
    return get_search(query_type)

@app.route("/search-real", methods=["POST"])
@cache.cached(timeout=60, key_prefix=make_cache_key)
def search_real() -> str:
    query_type = QUERY_TYPE.REAL
    return get_search(query_type)


@app.route("/search-historical", methods=["POST"])
@cache.cached(timeout=60, key_prefix=make_cache_key)
def search_historical() -> str:
    query_type = QUERY_TYPE.HISTORICAL
    return get_search(query_type)


def get_search(query_type: QUERY_TYPE) -> str:
    """Get search result partial html response based on the query type"""
    assert request is not None
    assert request.form is not None
    assert query_type in QUERY_TYPE

    data = request.form
    query = sanitize_string(data.get("search"))
    page = data.get("page", 1, type=int)
    per_page = data.get("per_page", 10, type=int)

    result = db.get_search(query, query_type)

    if not result:
        return error_dialog(f'No results found for "{query}"')

    table_html = get_html_table(result, query_type)
    visualization = get_html_visualization(result, query_type)
    if query_type == QUERY_TYPE.REAL:
        return table_html
    
    return  table_html +  visualization


if __name__ == "__main__":
    port = 5000
    http_server = WSGIServer(("", port), app)
    http_server.serve_forever()
