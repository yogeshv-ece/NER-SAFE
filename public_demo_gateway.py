"""
NER-SAFE: Temporary Public Access Gateway & Tunnel Manager
Enables secure, temporary public demonstration of the local NER-SAFE system
to judges and evaluators without exposing raw files, .env, or database secrets.

Architecture:
  LOCAL LAPTOP (Windows)
    ↓
  NER-SAFE SERVER (http://127.0.0.1:8000)
    ↓ [Explicit Route Filtering & Allowlist]
  TEMPORARY PUBLIC TUNNEL (Cloudflare / Localtunnel / Ngrok / LAN)
    ↓
  EVALUATORS / JUDGES (Public HTTPS)
"""

import os
import sys
import time
import shutil
import urllib.request
import subprocess
import threading

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
LOCAL_PORT = int(os.environ.get("PORT", 8000))
LOCAL_URL = f"http://127.0.0.1:{LOCAL_PORT}"

def check_server_running(url: str, timeout: float = 2.0) -> bool:
    """Verifies whether the NER-SAFE local server is responding."""
    try:
        req = urllib.request.Request(f"{url}/api/monitoring/status")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def verify_security_firewall(url: str) -> bool:
    """Verifies that static-file allowlist blocks confidential assets."""
    prohibited_routes = ["/.env.example", "/server.py", "/ner_safe.db", "/live_ingestion.py"]
    for route in prohibited_routes:
        try:
            req = urllib.request.Request(f"{url}{route}")
            urllib.request.urlopen(req, timeout=2.0)
            print(f"[SECURITY ALERT] Sensitive route {route} is accessible! Aborting public tunnel.")
            return False
        except urllib.error.HTTPError as e:
            if e.code not in (403, 404):
                print(f"[SECURITY WARNING] Unexpected response {e.code} on {route}")
        except Exception:
            pass
    return True

def start_cloudflare_tunnel(port: int):
    """Launches Cloudflare Quick Tunnel (cloudflared) if available."""
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        return None
    
    print(f"\n[TUNNEL] Launching Cloudflare Quick Tunnel on port {port}...")
    cmd = [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    tunnel_url = None
    start_time = time.time()
    # Cloudflare outputs the tunnel URL to stderr
    while time.time() - start_time < 20:
        line = proc.stderr.readline()
        if "trycloudflare.com" in line:
            for part in line.split():
                if "trycloudflare.com" in part:
                    tunnel_url = part.strip().rstrip("/")
                    if not tunnel_url.startswith("https://"):
                        tunnel_url = "https://" + tunnel_url
                    break
            if tunnel_url:
                break
        time.sleep(0.1)
    
    return proc, tunnel_url

def start_localtunnel(port: int):
    """Launches Localtunnel via npx if npx is available."""
    npx = shutil.which("npx")
    if not npx:
        return None
    
    print(f"\n[TUNNEL] Launching Localtunnel on port {port}...")
    cmd = [npx, "-y", "localtunnel", "--port", str(port)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    tunnel_url = None
    start_time = time.time()
    while time.time() - start_time < 25:
        line = proc.stdout.readline()
        if "loca.lt" in line or "your url is" in line.lower():
            for part in line.split():
                if "loca.lt" in part:
                    tunnel_url = part.strip()
                    break
            if tunnel_url:
                break
        time.sleep(0.1)
    
    return proc, tunnel_url

def get_lan_ip():
    """Finds local network IP for Wi-Fi / Ethernet evaluation."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    print("=" * 72)
    print("NER-SAFE TEMPORARY PUBLIC ACCESS & DEMONSTRATION GATEWAY")
    print("=" * 72)
    
    # 1. Check local server
    if not check_server_running(LOCAL_URL):
        print(f"[*] Local server not responding on {LOCAL_URL}. Starting server in background...")
        server_cmd = [sys.executable, os.path.join(PROJECT_ROOT, "server.py")]
        srv_proc = subprocess.Popen(server_cmd)
        time.sleep(2.0)
        if not check_server_running(LOCAL_URL):
            print(f"[!] ERROR: Failed to start local server on {LOCAL_URL}. Please check server logs.")
            sys.exit(1)
        print("[+] Local server started successfully.")
    else:
        srv_proc = None
        print(f"[+] Local NER-SAFE server is active and healthy on {LOCAL_URL}.")

    # 2. Security Firewall Audit
    print("[*] Running security perimeter audit...")
    if not verify_security_firewall(LOCAL_URL):
        print("[!] Security audit failed. Refusing to open public tunnel.")
        if srv_proc:
            srv_proc.terminate()
        sys.exit(1)
    print("[+] Security perimeter confirmed: Source code, .env, and SQLite files blocked.")

    # 3. Tunnel options
    tunnel_proc = None
    public_url = None

    # Try Cloudflare
    cf_res = start_cloudflare_tunnel(LOCAL_PORT)
    if cf_res:
        tunnel_proc, public_url = cf_res

    # Fallback to Localtunnel
    if not public_url:
        lt_res = start_localtunnel(LOCAL_PORT)
        if lt_res:
            tunnel_proc, public_url = lt_res

    # Display Access Info
    lan_ip = get_lan_ip()
    print("\n" + "=" * 72)
    print("NER-SAFE LIVE DEMONSTRATION PORTAL READY")
    print("=" * 72)
    print(f"Local Laptop Access:      http://localhost:{LOCAL_PORT}/")
    print(f"LAN / Wi-Fi Access:       http://{lan_ip}:{LOCAL_PORT}/")
    if public_url:
        print(f"Temporary Public URL:     {public_url}")
        print("  - Share this HTTPS URL with evaluators and judges.")
        print("  - Local laptop retains full scientific data locally.")
    else:
        print("\nNote: Neither 'cloudflared' nor 'npx localtunnel' was found for auto-tunneling.")
        print("For cloud evaluator demonstration:")
        print(f"  Option 1: Run 'npx localtunnel --port {LOCAL_PORT}' in another terminal.")
        print(f"  Option 2: Run 'cloudflared tunnel --url http://localhost:{LOCAL_PORT}'")
        print(f"  Option 3: Use LAN IP (http://{lan_ip}:{LOCAL_PORT}/) if on the same Wi-Fi.")
    print("=" * 72)
    print("Press Ctrl+C to stop the demonstration gateway and tear down access cleanly.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[+] Cleanly tearing down temporary demonstration gateway...")
        if tunnel_proc:
            tunnel_proc.terminate()
        if srv_proc:
            srv_proc.terminate()
        print("[+] Demonstration session closed safely.")

if __name__ == "__main__":
    main()
