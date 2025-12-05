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
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Proxy Client</title>
<style>
body { font-family: sans-serif; margin: 10px; }
#frameWrap { width: 100%; height: 400px; margin-top: 10px; border: 1px solid #ccc; }
iframe { width: 100%; height: 100%; border: none; }
#htmlBox { width: 100%; height: 150px; margin-top: 10px; display: none; }
#renderBtn { margin-top: 5px; display: none; }
</style>
</head>
<body>

<div>
URL:<br>
<input id="urlInput" type="text" placeholder="https://example.com" style="width: 300px;">
</div>

<div>
Mode:<br>
<select id="modeInput" onchange="checkMode()">
<option value="0">Normal</option>
<option value="1">Blocked</option>
<option value="2">Fetch Directly</option>
</select>
</div>

<button onclick="spawn()">Load</button>
<button onclick="openNewTab()">Open in New Tab</button>

<textarea id="htmlBox" placeholder="Paste HTML here for mode 1"></textarea>
<button id="renderBtn" onclick="renderBlob()">Render</button>

<div id="frameWrap"></div>

<script>
let spawned = false;
let currentBlobUrl = null;

function checkMode() {
const mode = document.getElementById('modeInput').value;
const htmlBox = document.getElementById('htmlBox');
const renderBtn = document.getElementById('renderBtn');

if (mode === "1") {
htmlBox.style.display = "block";
renderBtn.style.display = "inline-block";
} else {
htmlBox.style.display = "none";
renderBtn.style.display = "none";
}
}

function spawn() {
const url = document.getElementById('urlInput').value.trim();
const mode = document.getElementById('modeInput').value;
const frameWrap = document.getElementById('frameWrap');

if (!url && mode === "0") {
alert("Enter a URL");
return;
}

frameWrap.innerHTML = "";
const iframe = document.createElement("iframe");
iframe.id = "xframe";

// Mode 2: Direct fetch + blob
if (mode === "2") {
document.getElementById('htmlBox').style.display = "none";
document.getElementById('renderBtn').style.display = "none";

fetch(url)
.then(r => r.text())
.then(html => {
const blob = new Blob([html], { type: "text/html" });
const blobUrl = URL.createObjectURL(blob);
iframe.src = blobUrl;
})
.catch(err => {
iframe.srcdoc = "<h3>Fetch failed.<br>" + err + "</h3>";
});

frameWrap.appendChild(iframe);
spawned = true;
return;
}

// Mode 0 & 1 (proxy)
if (mode === "1") iframe.setAttribute("sandbox", "");

iframe.src =
"https://sealproxy.onrender.com/proxy?mode=" +
mode +
"&q=" +
encodeURIComponent(url);

frameWrap.appendChild(iframe);
spawned = true;

if (mode === "1") {
document.getElementById('htmlBox').style.display = "block";
document.getElementById('renderBtn').style.display = "inline-block";
} else {
document.getElementById('htmlBox').style.display = "none";
document.getElementById('renderBtn').style.display = "none";
}
}

function renderBlob() {
const htmlContent = document.getElementById('htmlBox').value.trim();
if (!htmlContent) {
alert("Paste HTML first");
return;
}

if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);

const blob = new Blob([htmlContent], { type: "text/html" });
currentBlobUrl = URL.createObjectURL(blob);

const iframe = document.getElementById('xframe');
if (iframe) {
iframe.removeAttribute("sandbox");
iframe.src = currentBlobUrl;
}
}

function openNewTab() {
if (!spawned) spawn();
const iframe = document.getElementById("xframe");
if (iframe) window.open(iframe.src, "_blank");
}
</script>

</body>
</html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
