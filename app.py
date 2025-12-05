from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

@app.route("/proxy")
def proxy():
    target_url = request.args.get("q")
    mode = request.args.get("mode", "0")  # default mode 0

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

    # HTML rewriting (for all modes if HTML)
    if "text/html" in content_type:
        soup = BeautifulSoup(r.text, "html.parser")
        attrs_to_rewrite = ["href", "src", "action"]

        for tag in soup.find_all():
            for attr in attrs_to_rewrite:
                if tag.has_attr(attr):
                    original = tag[attr]
                    absolute = urljoin(target_url, original)
                    # Rewrite through proxy, preserve mode
                    tag[attr] = f"https://sealproxy.onrender.com/proxy?q={absolute}&mode={mode}"

        rewritten_html = str(soup)

        if mode == "0":
            return Response(rewritten_html, content_type="text/html")
        elif mode == "1":
            return Response(rewritten_html, content_type="text/plain")
        elif mode == "2":
            return Response(rewritten_html, content_type=content_type)

    # Non-HTML content
    if mode == "2":
        # Return raw content with original Content-Type
        return Response(r.content, content_type=content_type)
    else:
        # For mode 0/1, return raw content as plain text if not HTML
        return Response(r.content, content_type="text/plain")


@app.route("/")
def home():
    return """
    <form action="/proxy" method="get">
        <input name="q" placeholder="https://example.com" style="width:300px">
        <select name="mode">
            <option value="0">Render HTML</option>
            <option value="1">Show raw HTML</option>
            <option value="2">Resource (original content type)</option>
        </select>
        <button>Go</button>
    </form>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
