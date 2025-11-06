import os
import sys
import time
from urllib.parse import urljoin
from dotenv import load_dotenv
try:
    from pyngrok import ngrok, conf
except ImportError:
    print("pyngrok is required. Install with: pip install pyngrok")
    sys.exit(1)


def main():

    load_dotenv()
    # Configuration
    port = int(os.getenv("FLASK_PORT", os.getenv("PORT", "10000")))
    authtoken = os.getenv("NGROK_AUTHTOKEN")
    region = os.getenv("NGROK_REGION", "us")  # us, eu, ap, au, sa, jp, in

    if not authtoken:
        print("ERROR: NGROK_AUTHTOKEN environment variable is not set.")
        print("Get one from https://dashboard.ngrok.com/get-started/your-authtoken")
        sys.exit(1)

    # Configure and authenticate
    conf.get_default().region = region
    ngrok.set_auth_token(authtoken)

    # Start HTTPS tunnel to local port
    print(f"Starting ngrok tunnel to http://127.0.0.1:{port} (region={region}) ...")
    public_url = ngrok.connect(addr=port, proto="http", bind_tls=True).public_url

    callback_path = "/linkedin/callback"
    callback_url = urljoin(public_url + '/', callback_path.lstrip('/'))

    print("\nTunnel established:")
    print(f"  Public URL: {public_url}")
    print(f"  Local URL:  http://127.0.0.1:{port}")
    print("\nUse this LinkedIn Redirect URI (must match exactly in app + env):")
    print(f"  {callback_url}")

    print("\nPress Ctrl+C to stop the tunnel.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        ngrok.kill()


if __name__ == "__main__":
    main()


