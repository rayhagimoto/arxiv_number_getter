from flask import Flask, request, render_template_string
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re
import difflib

app = Flask(__name__)

def normalize(text):
    return ' '.join(text.split()).casefold()

def strip_latex_math(text):
    return re.sub(r'\$.*?\$', '', text)

def get_arxiv_id_and_authors(title_query):
    title_query_stripped = strip_latex_math(title_query)
    keywords = re.findall(r'\w+', title_query_stripped)
    query_string = '+AND+'.join(f'all:{word}' for word in keywords)
    url = f"http://export.arxiv.org/api/query?search_query={query_string}&start=0&max_results=10"

    with urllib.request.urlopen(url) as response:
        xml_data = response.read().decode('utf-8')

    root = ET.fromstring(xml_data)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    target_title = normalize(title_query_stripped)
    candidates = []

    for entry in root.findall('atom:entry', ns):
        title_raw = entry.find('atom:title', ns).text.strip()
        title_clean = normalize(strip_latex_math(title_raw))
        candidates.append((title_clean, entry))

    titles = [t[0] for t in candidates]
    best_matches = difflib.get_close_matches(target_title, titles, n=1, cutoff=0.8)

    if best_matches:
        match_title = best_matches[0]
        for title_clean, entry in candidates:
            if title_clean == match_title:
                full_id_url = entry.find('atom:id', ns).text.strip()
                arxiv_id = full_id_url.split('/abs/')[-1].split('v')[0]

                authors = entry.findall('atom:author', ns)
                last_names = [author.find('atom:name', ns).text.strip().split()[-1] for author in authors]
                last_names_str = ', '.join(last_names)

                return f"{last_names_str} {arxiv_id}"

    return "No match found."

# Minimal HTML
HTML_TEMPLATE = """
<!doctype html>
<title>arXiv Finder</title>
<h2>Enter paper title</h2>
<form method="post">
  <input name="title" style="width: 400px;" placeholder="Paste arXiv paper title here">
  <button type="submit">Find</button>
</form>
{% if result %}
  <p><strong>Result:</strong> {{ result }}</p>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        title = request.form["title"]
        result = get_arxiv_id_and_authors(title)
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    app.run(debug=True)
