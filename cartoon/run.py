import os

from app import app

if __name__ == "__main__":
    print("🚀 Starting Cartoon GAN Application on http://localhost:5000...")
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
