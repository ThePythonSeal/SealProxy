from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

@app.route("/proxy")
def proxy():
    target_url = request.args.get("q")  # using ?q=LINK now
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

    # Mode 1: raw text
    if mode == "1":
        return Response(r.text, content_type="text/plain")

    # Mode 0: HTML rewrite
    if "text/html" in content_type:
        soup = BeautifulSoup(r.text, "html.parser")

        # Attributes we want to rewrite
        attrs_to_rewrite = ["href", "src", "action"]

        for tag in soup.find_all():
            for attr in attrs_to_rewrite:
                if tag.has_attr(attr):
                    original = tag[attr]
                    # Make absolute URL
                    absolute = urljoin(target_url, original)
                    # Rewrite through proxy
                    tag[attr] = f"https://sealproxy.onrender.com/proxy?q={absolute}"

        rewritten = str(soup)
        return Response(rewritten, content_type="text/html")

    # Non-HTML content: passthrough
    return Response(r.content, headers={"Content-Type": content_type})


@app.route("/")
def home():
    return """
    <form action="/proxy" method="get">
        <input name="q" placeholder="https://example.com" style="width:300px">
        <select name="mode">
            <option value="0">Render HTML</option>
            <option value="1">Show raw HTML</option>
        </select>
        <button>Go</button>
    </form>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
