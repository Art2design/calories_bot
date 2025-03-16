import os
import logging
from flask import Flask, render_template

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)