import os
from flask import Flask, render_template_string, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

report_path = os.getenv("REPORT_PATH")
# paths are properly formatted
if report_path:
    report_path = os.path.normpath(report_path)  # converts slashes automatically
    
@app.route("/")
def home():
    """Serve the latest HTML report."""
    if not os.path.exists(report_path):
        return "<h1>No report available. Please generate one first.</h1>"
    
    with open(report_path, encoding="utf-8") as f:
        html_report = f.read()
    
    return render_template_string(html_report)

@app.route("/download_pdf")
def download_pdf():
    """Allow downloading the latest PDF report."""
    if not os.path.exists(report_path):
        return "<h1>PDF report not found. Generate the report first.</h1>"
    
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
 