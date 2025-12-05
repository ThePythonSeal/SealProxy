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
                tag["href"] = f"https://freezingduck.onrender.com/proxy?q={absolute}&mode={mode}"
            elif tag.name == "form" and tag.has_attr("action"):
                absolute = urljoin(target_url, tag["action"])
                tag["action"] = f"https://freezingduck.onrender.com/proxy?q={absolute}&mode={mode}"
            else:
                # All other src/href/action → force mode=2
                for attr in ["src", "href", "action"]:
                    if tag.has_attr(attr):
                        absolute = urljoin(target_url, tag[attr])
                        tag[attr] = f"https://freezingduck.onrender.com/proxy?q={absolute}&mode=2"

        # Rewrite URLs inside <script> blocks
        for script in soup.find_all("script"):
            if script.string:
                # Match http(s) URLs or relative URLs in quotes
                def replace_url(match):
                    orig_url = match.group(1)
                    # Resolve relative URLs
                    absolute = urljoin(target_url, orig_url)
                    # Force mode=2 for scripts/resources
                    return f'"https://freezingduck.onrender.com/proxy?q={absolute}&mode=2"'

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
<title>Redirecting…</title>
<meta http-equiv="refresh" content="0;url=data:text/html;charset=utf-8,%3C!DOCTYPE%20html%3E%0A%3Chtml%3E%0A%3Chead%3E%0A%3Cmeta%20charset%3D%22UTF-8%22%3E%0A%3Ctitle%3EProxy%20Client%3C%2Ftitle%3E%0A%3Cstyle%3E%0Abody%20%7B%20font-family%3A%20sans-serif%3B%20margin%3A%2010px%3B%20%7D%0A%23frameWrap%20%7B%20width%3A%20100%25%3B%20height%3A%20400px%3B%20margin-top%3A%2010px%3B%20border%3A%201px%20solid%20%23ccc%3B%20%7D%0Aiframe%20%7B%20width%3A%20100%25%3B%20height%3A%20100%25%3B%20border%3A%20none%3B%20%7D%0A%23htmlBox%20%7B%20width%3A%20100%25%3B%20height%3A%20150px%3B%20margin-top%3A%2010px%3B%20display%3A%20none%3B%20%7D%0A%23renderBtn%20%7B%20margin-top%3A%205px%3B%20display%3A%20none%3B%20%7D%0A%3C%2Fstyle%3E%0A%3C%2Fhead%3E%0A%3Cbody%3E%0A%0A%3Cdiv%3E%0AURL%3A%3Cbr%3E%0A%3Cinput%20id%3D%22urlInput%22%20type%3D%22text%22%20placeholder%3D%22https%3A%2F%2Fexample.com%22%20style%3D%22width%3A%20300px%3B%22%3E%0A%3C%2Fdiv%3E%0A%0A%3Cdiv%3E%0AMode%3A%3Cbr%3E%0A%3Cselect%20id%3D%22modeInput%22%20onchange%3D%22checkMode()%22%3E%0A%3Coption%20value%3D%220%22%3ENormal%3C%2Foption%3E%0A%3Coption%20value%3D%221%22%3EBlocked%3C%2Foption%3E%0A%3Coption%20value%3D%222%22%3EFetch%20Directly%3C%2Foption%3E%0A%3C%2Fselect%3E%0A%3C%2Fdiv%3E%0A%0A%3Cbutton%20onclick%3D%22spawn()%22%3ELoad%3C%2Fbutton%3E%0A%3Cbutton%20onclick%3D%22openNewTab()%22%3EOpen%20in%20New%20Tab%3C%2Fbutton%3E%0A%0A%3Ctextarea%20id%3D%22htmlBox%22%20placeholder%3D%22Paste%20HTML%20here%20for%20mode%201%22%3E%3C%2Ftextarea%3E%0A%3Cbutton%20id%3D%22renderBtn%22%20onclick%3D%22renderBlob()%22%3ERender%3C%2Fbutton%3E%0A%0A%3Cdiv%20id%3D%22frameWrap%22%3E%3C%2Fdiv%3E%0A%0A%3Cscript%3E%0Alet%20spawned%20%3D%20false%3B%0Alet%20currentBlobUrl%20%3D%20null%3B%0A%0Afunction%20checkMode()%20%7B%0Aconst%20mode%20%3D%20document.getElementById('modeInput').value%3B%0Aconst%20htmlBox%20%3D%20document.getElementById('htmlBox')%3B%0Aconst%20renderBtn%20%3D%20document.getElementById('renderBtn')%3B%0A%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20%7B%0AhtmlBox.style.display%20%3D%20%22block%22%3B%0ArenderBtn.style.display%20%3D%20%22inline-block%22%3B%0A%7D%20else%20%7B%0AhtmlBox.style.display%20%3D%20%22none%22%3B%0ArenderBtn.style.display%20%3D%20%22none%22%3B%0A%7D%0A%7D%0A%0Afunction%20spawn()%20%7B%0Aconst%20url%20%3D%20document.getElementById('urlInput').value.trim()%3B%0Aconst%20mode%20%3D%20document.getElementById('modeInput').value%3B%0Aconst%20frameWrap%20%3D%20document.getElementById('frameWrap')%3B%0A%0Aif%20(!url%20%26%26%20mode%20%3D%3D%3D%20%220%22)%20%7B%0Aalert(%22Enter%20a%20URL%22)%3B%0Areturn%3B%0A%7D%0A%0AframeWrap.innerHTML%20%3D%20%22%22%3B%0Aconst%20iframe%20%3D%20document.createElement(%22iframe%22)%3B%0Aiframe.id%20%3D%20%22xframe%22%3B%0A%0A%2F%2F%20Mode%202%3A%20Direct%20fetch%20%2B%20blob%0Aif%20(mode%20%3D%3D%3D%20%222%22)%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22none%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22none%22%3B%0A%0Afetch(url)%0A.then(r%20%3D%3E%20r.text())%0A.then(html%20%3D%3E%20%7B%0Aconst%20blob%20%3D%20new%20Blob(%5Bhtml%5D%2C%20%7B%20type%3A%20%22text%2Fhtml%22%20%7D)%3B%0Aconst%20blobUrl%20%3D%20URL.createObjectURL(blob)%3B%0Aiframe.src%20%3D%20blobUrl%3B%0A%7D)%0A.catch(err%20%3D%3E%20%7B%0Aiframe.srcdoc%20%3D%20%22%3Ch3%3EFetch%20failed.%3Cbr%3E%22%20%2B%20err%20%2B%20%22%3C%2Fh3%3E%22%3B%0A%7D)%3B%0A%0AframeWrap.appendChild(iframe)%3B%0Aspawned%20%3D%20true%3B%0Areturn%3B%0A%7D%0A%0A%2F%2F%20Mode%200%20%26%201%20(proxy)%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20iframe.setAttribute(%22sandbox%22%2C%20%22%22)%3B%0A%0Aiframe.src%20%3D%0A%22https%3A%2F%2Ffreezingduck.onrender.com%2Fproxy%3Fmode%3D%22%20%2B%0Amode%20%2B%0A%22%26q%3D%22%20%2B%0AencodeURIComponent(url)%3B%0A%0AframeWrap.appendChild(iframe)%3B%0Aspawned%20%3D%20true%3B%0A%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22block%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22inline-block%22%3B%0A%7D%20else%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22none%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22none%22%3B%0A%7D%0A%7D%0A%0Afunction%20renderBlob()%20%7B%0Aconst%20htmlContent%20%3D%20document.getElementById('htmlBox').value.trim()%3B%0Aif%20(!htmlContent)%20%7B%0Aalert(%22Paste%20HTML%20first%22)%3B%0Areturn%3B%0A%7D%0A%0Aif%20(currentBlobUrl)%20URL.revokeObjectURL(currentBlobUrl)%3B%0A%0Aconst%20blob%20%3D%20new%20Blob(%5BhtmlContent%5D%2C%20%7B%20type%3A%20%22text%2Fhtml%22%20%7D)%3B%0AcurrentBlobUrl%20%3D%20URL.createObjectURL(blob)%3B%0A%0Aconst%20iframe%20%3D%20document.getElementById('xframe')%3B%0Aif%20(iframe)%20%7B%0Aiframe.removeAttribute(%22sandbox%22)%3B%0Aiframe.src%20%3D%20currentBlobUrl%3B%0A%7D%0A%7D%0A%0Afunction%20openNewTab()%20%7B%0Aif%20(!spawned)%20spawn()%3B%0Aconst%20iframe%20%3D%20document.getElementById(%22xframe%22)%3B%0Aif%20(iframe)%20window.open(iframe.src%2C%20%22_blank%22)%3B%0A%7D%0A%3C%2Fscript%3E%0A%0A%3C%2Fbody%3E%0A%3C%2Fhtml%3E">
</head>
<body>
If you are not redirected automatically, <a href="data:text/html;charset=utf-8,%3C!DOCTYPE%20html%3E%0A%3Chtml%3E%0A%3Chead%3E%0A%3Cmeta%20charset%3D%22UTF-8%22%3E%0A%3Ctitle%3EProxy%20Client%3C%2Ftitle%3E%0A%3Cstyle%3E%0Abody%20%7B%20font-family%3A%20sans-serif%3B%20margin%3A%2010px%3B%20%7D%0A%23frameWrap%20%7B%20width%3A%20100%25%3B%20height%3A%20400px%3B%20margin-top%3A%2010px%3B%20border%3A%201px%20solid%20%23ccc%3B%20%7D%0Aiframe%20%7B%20width%3A%20100%25%3B%20height%3A%20100%25%3B%20border%3A%20none%3B%20%7D%0A%23htmlBox%20%7B%20width%3A%20100%25%3B%20height%3A%20150px%3B%20margin-top%3A%2010px%3B%20display%3A%20none%3B%20%7D%0A%23renderBtn%20%7B%20margin-top%3A%205px%3B%20display%3A%20none%3B%20%7D%0A%3C%2Fstyle%3E%0A%3C%2Fhead%3E%0A%3Cbody%3E%0A%0A%3Cdiv%3E%0AURL%3A%3Cbr%3E%0A%3Cinput%20id%3D%22urlInput%22%20type%3D%22text%22%20placeholder%3D%22https%3A%2F%2Fexample.com%22%20style%3D%22width%3A%20300px%3B%22%3E%0A%3C%2Fdiv%3E%0A%0A%3Cdiv%3E%0AMode%3A%3Cbr%3E%0A%3Cselect%20id%3D%22modeInput%22%20onchange%3D%22checkMode()%22%3E%0A%3Coption%20value%3D%220%22%3ENormal%3C%2Foption%3E%0A%3Coption%20value%3D%221%22%3EBlocked%3C%2Foption%3E%0A%3Coption%20value%3D%222%22%3EFetch%20Directly%3C%2Foption%3E%0A%3C%2Fselect%3E%0A%3C%2Fdiv%3E%0A%0A%3Cbutton%20onclick%3D%22spawn()%22%3ELoad%3C%2Fbutton%3E%0A%3Cbutton%20onclick%3D%22openNewTab()%22%3EOpen%20in%20New%20Tab%3C%2Fbutton%3E%0A%0A%3Ctextarea%20id%3D%22htmlBox%22%20placeholder%3D%22Paste%20HTML%20here%20for%20mode%201%22%3E%3C%2Ftextarea%3E%0A%3Cbutton%20id%3D%22renderBtn%22%20onclick%3D%22renderBlob()%22%3ERender%3C%2Fbutton%3E%0A%0A%3Cdiv%20id%3D%22frameWrap%22%3E%3C%2Fdiv%3E%0A%0A%3Cscript%3E%0Alet%20spawned%20%3D%20false%3B%0Alet%20currentBlobUrl%20%3D%20null%3B%0A%0Afunction%20checkMode()%20%7B%0Aconst%20mode%20%3D%20document.getElementById('modeInput').value%3B%0Aconst%20htmlBox%20%3D%20document.getElementById('htmlBox')%3B%0Aconst%20renderBtn%20%3D%20document.getElementById('renderBtn')%3B%0A%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20%7B%0AhtmlBox.style.display%20%3D%20%22block%22%3B%0ArenderBtn.style.display%20%3D%20%22inline-block%22%3B%0A%7D%20else%20%7B%0AhtmlBox.style.display%20%3D%20%22none%22%3B%0ArenderBtn.style.display%20%3D%20%22none%22%3B%0A%7D%0A%7D%0A%0Afunction%20spawn()%20%7B%0Aconst%20url%20%3D%20document.getElementById('urlInput').value.trim()%3B%0Aconst%20mode%20%3D%20document.getElementById('modeInput').value%3B%0Aconst%20frameWrap%20%3D%20document.getElementById('frameWrap')%3B%0A%0Aif%20(!url%20%26%26%20mode%20%3D%3D%3D%20%220%22)%20%7B%0Aalert(%22Enter%20a%20URL%22)%3B%0Areturn%3B%0A%7D%0A%0AframeWrap.innerHTML%20%3D%20%22%22%3B%0Aconst%20iframe%20%3D%20document.createElement(%22iframe%22)%3B%0Aiframe.id%20%3D%20%22xframe%22%3B%0A%0A%2F%2F%20Mode%202%3A%20Direct%20fetch%20%2B%20blob%0Aif%20(mode%20%3D%3D%3D%20%222%22)%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22none%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22none%22%3B%0A%0Afetch(url)%0A.then(r%20%3D%3E%20r.text())%0A.then(html%20%3D%3E%20%7B%0Aconst%20blob%20%3D%20new%20Blob(%5Bhtml%5D%2C%20%7B%20type%3A%20%22text%2Fhtml%22%20%7D)%3B%0Aconst%20blobUrl%20%3D%20URL.createObjectURL(blob)%3B%0Aiframe.src%20%3D%20blobUrl%3B%0A%7D)%0A.catch(err%20%3D%3E%20%7B%0Aiframe.srcdoc%20%3D%20%22%3Ch3%3EFetch%20failed.%3Cbr%3E%22%20%2B%20err%20%2B%20%22%3C%2Fh3%3E%22%3B%0A%7D)%3B%0A%0AframeWrap.appendChild(iframe)%3B%0Aspawned%20%3D%20true%3B%0Areturn%3B%0A%7D%0A%0A%2F%2F%20Mode%200%20%26%201%20(proxy)%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20iframe.setAttribute(%22sandbox%22%2C%20%22%22)%3B%0A%0Aiframe.src%20%3D%0A%22https%3A%2F%2Ffreezingduck.onrender.com%2Fproxy%3Fmode%3D%22%20%2B%0Amode%20%2B%0A%22%26q%3D%22%20%2B%0AencodeURIComponent(url)%3B%0A%0AframeWrap.appendChild(iframe)%3B%0Aspawned%20%3D%20true%3B%0A%0Aif%20(mode%20%3D%3D%3D%20%221%22)%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22block%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22inline-block%22%3B%0A%7D%20else%20%7B%0Adocument.getElementById('htmlBox').style.display%20%3D%20%22none%22%3B%0Adocument.getElementById('renderBtn').style.display%20%3D%20%22none%22%3B%0A%7D%0A%7D%0A%0Afunction%20renderBlob()%20%7B%0Aconst%20htmlContent%20%3D%20document.getElementById('htmlBox').value.trim()%3B%0Aif%20(!htmlContent)%20%7B%0Aalert(%22Paste%20HTML%20first%22)%3B%0Areturn%3B%0A%7D%0A%0Aif%20(currentBlobUrl)%20URL.revokeObjectURL(currentBlobUrl)%3B%0A%0Aconst%20blob%20%3D%20new%20Blob(%5BhtmlContent%5D%2C%20%7B%20type%3A%20%22text%2Fhtml%22%20%7D)%3B%0AcurrentBlobUrl%20%3D%20URL.createObjectURL(blob)%3B%0A%0Aconst%20iframe%20%3D%20document.getElementById('xframe')%3B%0Aif%20(iframe)%20%7B%0Aiframe.removeAttribute(%22sandbox%22)%3B%0Aiframe.src%20%3D%20currentBlobUrl%3B%0A%7D%0A%7D%0A%0Afunction%20openNewTab()%20%7B%0Aif%20(!spawned)%20spawn()%3B%0Aconst%20iframe%20%3D%20document.getElementById(%22xframe%22)%3B%0Aif%20(iframe)%20window.open(iframe.src%2C%20%22_blank%22)%3B%0A%7D%0A%3C%2Fscript%3E%0A%0A%3C%2Fbody%3E%0A%3C%2Fhtml%3E">click here</a>.
</body>
</html>

    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
