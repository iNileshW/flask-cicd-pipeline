"""Flask API for the CI/CD Pipelines lab."""

from flask import Flask, jsonify

app = Flask(__name__)

VERSION = "1.0.0"


@app.route("/health")
def health():
    """Return a JSON health status response."""
    return jsonify({"status": "healthy", "version": VERSION})


@app.route("/api/info")
def info():
    """Return application information."""
    return jsonify({
        "name": "Pipeline API",
        "version": VERSION,
        "environment": "development",
    })


@app.route("/")
def index():
    """Return a welcome message."""
    return jsonify({"message": "CI/CD Pipeline Lab API"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
