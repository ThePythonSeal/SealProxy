from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

@app.route("/proxy")
def proxy():
    target_url = request.args.get("url")
    mode = request.args.get("mode", "0")  # default: HTML rendering

    if not target_url:
        return "Missing URL.", 400

    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        return "Invalid scheme.", 400

    try:
        r = requests.get(target_url, timeout=30)
    except Exception as e:
        return f"Failed to fetch: {e}", 500

    content_type = r.headers.get("content-type", "").lower()

    # Raw text mode (mode=1)
    if mode == "1":
        if "text" in content_type or "html" in content_type:
            return Response(r.text, content_type="text/plain")
        return Response(r.content, content_type="text/plain")

    # Normal rewrite mode (mode=0)
    if "text/html" in content_type:
        soup = BeautifulSoup(r.text, "html.parser")

        attrs = ["href", "src", "action"]

        for tag in soup.find_all():
            for attr in attrs:
                if tag.has_attr(attr):
                    original = tag[attr]
                    absolute = urljoin(target_url, original)
                    tag[attr] = "/proxy?url=" + absolute

        rewritten = str(soup)
        return Response(rewritten, content_type="text/html")

    # Non-HTML content just passthrough
    return Response(r.content, headers={"Content-Type": content_type})


@app.route("/")
def home():
    return """
    <form action="/proxy" method="get">
        <input name="url" placeholder="https://example.com" style="width:300px">
        <select name="mode">
            <option value="0">Render HTML</option>
            <option value="1">Show raw HTML</option>
        </select>
        <button>Go</button>
    </form>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
