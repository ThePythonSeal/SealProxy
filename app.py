from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

app = Flask(__name__)

@app.route("/proxy")
def proxy():
    target_url = request.args.get("q")
    mode = request.args.get("mode", "0")

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

    # Only rewrite HTML
    if "text/html" in content_type:
        soup = BeautifulSoup(r.text, "html.parser")
        attrs_to_rewrite = ["href", "src", "action"]

        for tag in soup.find_all():
            # Links and forms keep mode
            if tag.name == "a" and tag.has_attr("href"):
                absolute = urljoin(target_url, tag["href"])
                tag["href"] = f"https://sealproxy.onrender.com/proxy?q={absolute}&mode={mode}"
            elif tag.name == "form" and tag.has_attr("action"):
                absolute = urljoin(target_url, tag["action"])
                tag["action"] = f"https://sealproxy.onrender.com/proxy?q={absolute}&mode={mode}"
            else:
                # All other src/href/action → force mode=2
                for attr in ["src", "href", "action"]:
                    if tag.has_attr(attr):
                        absolute = urljoin(target_url, tag[attr])
                        tag[attr] = f"https://sealproxy.onrender.com/proxy?q={absolute}&mode=2"

        # Rewrite URLs inside <script> blocks
        for script in soup.find_all("script"):
            if script.string:
                # Match http(s) URLs or relative URLs in quotes
                def replace_url(match):
                    orig_url = match.group(1)
                    # Resolve relative URLs
                    absolute = urljoin(target_url, orig_url)
                    # Force mode=2 for scripts/resources
                    return f'"https://sealproxy.onrender.com/proxy?q={absolute}&mode=2"'

                script.string = re.sub(r'"(https?://[^"]+)"', replace_url, script.string)
                # Optionally, also handle single quotes
                script.string = re.sub(r"'(https?://[^']+)'", replace_url, script.string)

        rewritten_html = str(soup)

        if mode == "0":
            return Response(rewritten_html, content_type="text/html")
        elif mode == "1":
            return Response(rewritten_html, content_type="text/plain")
        elif mode == "2":
            return Response(rewritten_html, content_type=content_type)

    # Non-HTML content
    if mode == "2":
        return Response(r.content, content_type=content_type)
    else:
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
