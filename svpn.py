#!/usr/bin/env python3
"""
svpn.py - Server VPN Manager for Linux
A lightweight CLI tool to manage a local proxy for providing internet access
to any Linux server, without disrupting existing services.
"""
import os
import sys
import argparse
import urllib.request
import urllib.error
import json
import gzip
import shutil
import subprocess
import time
import ssl
import signal


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.yaml")
SUB_FILE = os.path.join(DATA_DIR, "sub_url.txt")
FILTER_FILE = os.path.join(DATA_DIR, "node_filter.txt")
PID_FILE = os.path.join(DATA_DIR, "mihomo.pid")
MIHOMO_BIN = os.path.join(DATA_DIR, "mihomo")
PROXY_PORT = 7890
API_PORT = 9090
# Default filter: empty string means use all nodes
DEFAULT_NODE_FILTER = ""
US_NODE_FILTER = r"(?i)(^|[^\w])(US|USA|United States|America|美国)([^\w]|$)"

GH_MIRRORS = [
    "https://gh-proxy.com/",
    "https://ghfast.top/",
    "https://ghproxy.net/",
    "",
]

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_platform_info():
    sys_name = os.uname().sysname.lower()
    machine = os.uname().machine.lower()
    os_map = {"linux": "linux", "darwin": "darwin"}
    if machine in ["x86_64", "amd64"]:
        arch = "amd64"
    elif machine in ["aarch64", "arm64"]:
        arch = "arm64"
    else:
        arch = machine
    return os_map.get(sys_name, sys_name), arch

def download_url_with_retry(url, dest_path, desc="file"):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get("https_proxy") or os.environ.get("http_proxy")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    with opener.open(req) as response, open(dest_path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)
    return True

def download_mihomo():
    ensure_data_dir()
    os_name, arch = get_platform_info()
    version = "v1.18.3"
    print(f"Detected OS: {os_name}, Arch: {arch}")

    if os_name == "darwin":
        gh_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-darwin-{arch}-{version}.gz"
    else:
        if arch == "amd64":
            gh_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-linux-{arch}-compatible-{version}.gz"
        else:
            gh_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-linux-{arch}-{version}.gz"

    gz_path = os.path.join(DATA_DIR, "mihomo.gz")

    for mirror in GH_MIRRORS:
        download_url = mirror + gh_url
        try:
            print(f"Downloading Mihomo from {download_url or gh_url}...")
            download_url_with_retry(download_url, gz_path)
            print("Download complete. Extracting...")
            with gzip.open(gz_path, "rb") as f_in:
                with open(MIHOMO_BIN, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(gz_path)
            os.chmod(MIHOMO_BIN, 0o755)
            print(f"Installation complete. Executable saved at: {MIHOMO_BIN}")
            return
        except Exception as e:
            print(f"Mirror failed: {e}")
            if os.path.exists(gz_path):
                os.remove(gz_path)
            continue
    print("Error: All download mirrors failed. Please check network connectivity.")
    sys.exit(1)

def set_subscription(url):
    ensure_data_dir()
    with open(SUB_FILE, "w") as f:
        f.write(url.strip())
    print("Subscription URL saved.")

def get_subscription():
    if not os.path.exists(SUB_FILE):
        return None
    with open(SUB_FILE, "r") as f:
        url = f.read().strip()
        return url if url else None

def set_node_filter(filter_pattern):
    """Set node filter pattern. Empty string means use all nodes."""
    ensure_data_dir()
    with open(FILTER_FILE, "w") as f:
        f.write(filter_pattern.strip())
    if filter_pattern:
        print(f"Node filter saved: '{filter_pattern}'")
    else:
        print("Node filter cleared (will use all nodes)")

def get_node_filter():
    """Get node filter pattern. Returns empty string if not set (use all nodes)."""
    if not os.path.exists(FILTER_FILE):
        return DEFAULT_NODE_FILTER
    with open(FILTER_FILE, "r") as f:
        return f.read().strip()

def generate_config():
    sub_url = get_subscription()
    if not sub_url:
        print("First run: a subscription URL is required (Base64/Clash/Mihomo formats supported).")
        sub_url = input("Enter your subscription URL: ").strip()
        if not sub_url:
            print("A valid subscription URL is required to continue.")
            sys.exit(1)
        set_subscription(sub_url)

    node_filter = get_node_filter()
    filter_line = f"    filter: '{node_filter}'" if node_filter else ""

    config_yaml = f"""\
mixed-port: {PROXY_PORT}
allow-lan: true
bind-address: "*"
mode: rule
log-level: info
external-controller: 127.0.0.1:{API_PORT}

geo-auto-update: true
geo-update-interval: 24
geox-url:
  geoip: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat"
  geosite: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat"
  mmdb: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/Country.mmdb"

proxy-providers:
  svpn-provider:
    type: http
    url: "{sub_url}"
    interval: 86400
    path: ./sub.yaml
    health-check:
      enable: true
      interval: 300
      url: http://www.gstatic.com/generate_204

proxy-groups:
  - name: PROXY
    type: url-test
    use:
      - svpn-provider
{filter_line}
    url: 'http://www.gstatic.com/generate_204'
    interval: 300
    tolerance: 50

rules:
  - DOMAIN-SUFFIX,google.com,PROXY
  - DOMAIN-SUFFIX,googleapis.com,PROXY
  - DOMAIN-KEYWORD,google,PROXY
  - DOMAIN-SUFFIX,github.com,PROXY
  - DOMAIN-SUFFIX,githubusercontent.com,PROXY
  - DOMAIN-SUFFIX,github.io,PROXY
  - DOMAIN-SUFFIX,githubassets.com,PROXY
  - DOMAIN-SUFFIX,openai.com,PROXY
  - DOMAIN-SUFFIX,anthropic.com,PROXY
  - DOMAIN-SUFFIX,claude.ai,PROXY
  - DOMAIN-SUFFIX,youtube.com,PROXY
  - DOMAIN-SUFFIX,ytimg.com,PROXY
  - DOMAIN-SUFFIX,googlevideo.com,PROXY
  - DOMAIN-SUFFIX,twitter.com,PROXY
  - DOMAIN-SUFFIX,x.com,PROXY
  - DOMAIN-SUFFIX,facebook.com,PROXY
  - DOMAIN-SUFFIX,instagram.com,PROXY
  - DOMAIN-SUFFIX,wikipedia.org,PROXY
  - DOMAIN-SUFFIX,stackoverflow.com,PROXY
  - DOMAIN-SUFFIX,npmjs.com,PROXY
  - DOMAIN-SUFFIX,pypi.org,PROXY
  - DOMAIN-SUFFIX,docker.io,PROXY
  - DOMAIN-SUFFIX,docker.com,PROXY
  - DOMAIN-SUFFIX,cloudflare.com,PROXY
  - DOMAIN-SUFFIX,amazonaws.com,PROXY
  - DOMAIN-SUFFIX,huggingface.co,PROXY
  - DOMAIN-SUFFIX,notion.so,PROXY
  - DOMAIN-SUFFIX,telegram.org,PROXY
  - DOMAIN-SUFFIX,t.me,PROXY
  - DOMAIN-SUFFIX,discord.com,PROXY
  - DOMAIN-SUFFIX,discord.gg,PROXY
  - DOMAIN-SUFFIX,medium.com,PROXY
  - DOMAIN-SUFFIX,reddit.com,PROXY
  - DOMAIN-SUFFIX,linkedin.com,PROXY
  - DOMAIN-SUFFIX,microsoft.com,PROXY
  - DOMAIN-SUFFIX,apple.com,PROXY
  - DOMAIN-SUFFIX,cloud.google.com,PROXY
  - DOMAIN-SUFFIX,aws.amazon.com,PROXY
  - DOMAIN-SUFFIX,stackoverflow.com,PROXY
  - DOMAIN-SUFFIX,netflix.com,PROXY
  - DOMAIN-SUFFIX,spotify.com,PROXY
  - DOMAIN-SUFFIX,notion.so,PROXY
  - DOMAIN-SUFFIX,figma.com,PROXY
  - DOMAIN-SUFFIX,notion.so,PROXY
  - DOMAIN-SUFFIX,v2ex.com,PROXY
  - DOMAIN-SUFFIX,graphql.org,PROXY
  - GEOIP,PRIVATE,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
"""
    with open(CONFIG_FILE, "w") as f:
        f.write(config_yaml)
    print("Generated config.yaml successfully.")

def is_running():
    if not os.path.exists(PID_FILE):
        return False
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False

def wait_for_port(port, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/version", timeout=2)
            if conn.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def start_proxy():
    if not os.path.exists(MIHOMO_BIN):
        print("Core component not found. Downloading automatically...")
        download_mihomo()

    generate_config()

    if is_running():
        with open(PID_FILE, "r") as f:
            pid = f.read().strip()
        print(f"Mihomo is already running with PID {pid}.")
        print_proxy_usage()
        return

    print("Starting VPN proxy engine...")
    log_file = os.path.join(DATA_DIR, "mihomo.log")

    cmd = [MIHOMO_BIN, "-d", DATA_DIR, "-f", CONFIG_FILE]
    kwargs = {}
    if os.name != "nt" and hasattr(os, "setsid"):
        kwargs["preexec_fn"] = os.setsid

    with open(log_file, "w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, **kwargs)
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))

    if wait_for_port(API_PORT):
        print(f"VPN proxy started successfully (PID: {proc.pid}).")
        setup_persistent_proxy()
        print_proxy_usage()
    else:
        print(f"VPN proxy process launched (PID: {proc.pid}), but API not responding yet.")
        print(f"Check logs: cat {log_file}")

def setup_persistent_proxy():
    """Configure proxy environment variables in ~/.bashrc for all terminals."""
    bashrc = os.path.expanduser("~/.bashrc")
    marker = "# SVPN Proxy Settings"

    # Check if already configured
    if os.path.exists(bashrc):
        with open(bashrc, "r") as f:
            content = f.read()
        if marker in content:
            print("Proxy environment already configured in ~/.bashrc")
            return

    proxy_config = f"""

{marker}
export http_proxy=http://127.0.0.1:{PROXY_PORT}
export https_proxy=http://127.0.0.1:{PROXY_PORT}
export all_proxy=socks5://127.0.0.1:{PROXY_PORT}
export HTTP_PROXY=http://127.0.0.1:{PROXY_PORT}
export HTTPS_PROXY=http://127.0.0.1:{PROXY_PORT}
export ALL_PROXY=socks5://127.0.0.1:{PROXY_PORT}
export no_proxy=localhost,127.0.0.1,::1,*.local
export NO_PROXY=localhost,127.0.0.1,::1,*.local
"""
    with open(bashrc, "a") as f:
        f.write(proxy_config)
    print("✓ Proxy environment variables added to ~/.bashrc")
    print("  Run 'source ~/.bashrc' or open a new terminal to apply.")


def print_proxy_usage():
    print(f"\n  Proxy is running on 127.0.0.1:{PROXY_PORT} (HTTP & SOCKS5)")
    print("  Environment variables have been configured in ~/.bashrc")
    print("  To apply in current terminal, run:")
    print("    source ~/.bashrc")
    print("\n  Or open a new terminal - proxy will be active automatically.")
    print("\n  To use VPN for a single command without env vars:")
    print(f"    http_proxy=http://127.0.0.1:{PROXY_PORT} https_proxy=http://127.0.0.1:{PROXY_PORT} <your-command>")

def stop_proxy():
    if not is_running():
        print("VPN proxy is not running.")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return

    with open(PID_FILE, "r") as f:
        pid = f.read().strip()

    print(f"Stopping VPN proxy (PID {pid})...")
    try:
        os.kill(int(pid), signal.SIGTERM)
        for _ in range(50):
            if not is_running():
                break
            time.sleep(0.1)
        if is_running():
            print("Force killing...")
            os.kill(int(pid), signal.SIGKILL)
    except OSError:
        pass

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    print("VPN proxy stopped.")

def api_request(method, path, data=None):
    url = f"http://127.0.0.1:{API_PORT}{path}"
    headers = {}
    if data:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status in [200, 204]:
                body = response.read()
                if body:
                    return json.loads(body.decode("utf-8"))
                return True
            return None
    except Exception as e:
        print(f"API request failed: {e}")
        return None

def status_proxy():
    if not is_running():
        print("VPN proxy is NOT running.")
        return

    resp = api_request("GET", "/proxies/PROXY")
    if resp:
        print("VPN proxy is RUNNING.")
        now_active = resp.get("now", "Unknown")
        print(f"Active node (auto-selected): {now_active}")
        all_proxies = resp.get("all", [])
        print(f"Available proxies: {len(all_proxies)}")
        node_filter = get_node_filter()
        if node_filter:
            print(f"Node filter: '{node_filter}'")
        else:
            print("Node filter: (none - using all nodes)")
    else:
        print("VPN proxy is running but API is inaccessible (maybe starting up?).")

def list_nodes():
    """List all available nodes from the subscription."""
    if not is_running():
        print("VPN proxy must be running. Run 'start' first.")
        return

    resp = api_request("GET", "/providers/proxies/svpn-provider")
    if not resp:
        print("Failed to get node list. Try 'update' to refresh subscription.")
        return

    proxies = resp.get("proxies", [])
    if not proxies:
        print("No proxies found in subscription.")
        return

    print(f"Total nodes in subscription: {len(proxies)}")
    print("\nAvailable nodes:")
    print("-" * 50)
    for i, proxy in enumerate(proxies, 1):
        name = proxy.get("name", "Unknown")
        node_type = proxy.get("type", "Unknown")
        alive = proxy.get("alive", False)
        delay = proxy.get("history", [{}])[-1].get("delay", "N/A") if proxy.get("history") else "N/A"
        status = "✓" if alive else "✗"
        print(f"  {i:3d}. [{status}] {name} ({node_type}) - {delay}ms")
    print("-" * 50)
    print(f"\nCurrent filter: '{get_node_filter()}'" if get_node_filter() else "\nCurrent filter: (none - using all nodes)")
    print("\nTo filter nodes, use: python3 svpn.py set-filter '<regex_pattern>'")
    print("Examples:")
    print("  python3 svpn.py set-filter '(?i)us|美国'  # US nodes only")
    print("  python3 svpn.py set-filter ''             # Use all nodes")

def update_subscription():
    if not is_running():
        print("VPN proxy must be running. Run 'start' first.")
        return

    print("Updating subscription...")
    resp = api_request("PUT", "/providers/proxies/svpn-provider")
    if resp is not None:
        print("Subscription updated. Wait a few seconds for nodes to refresh.")
    else:
        print("Failed to update subscription.")

def best_node():
    if not is_running():
        print("VPN proxy must be running. Run 'start' first.")
        return

    print("Testing all nodes for best latency...")
    resp = api_request("GET", "/providers/proxies/svpn-provider/healthcheck")
    if resp is not None:
        print("Healthcheck triggered. Waiting for results...")
        time.sleep(3)
        status_proxy()
    else:
        print("Failed to trigger healthcheck.")

def test_connection():
    proxy_url = f"http://127.0.0.1:{PROXY_PORT}"
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)

    targets = {
        "Google": "https://www.google.com",
        "GitHub": "https://github.com",
        "OpenAI": "https://openai.com",
    }

    print("Testing connectivity through VPN proxy...")
    all_ok = True
    for name, url in targets.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = opener.open(req, timeout=10)
            status = "OK" if resp.status == 200 else f"HTTP {resp.status}"
            print(f"  {name}: {status}")
        except Exception as e:
            print(f"  {name}: FAILED ({e})")
            all_ok = False

    if all_ok:
        print("\nAll connectivity tests passed!")
    else:
        print("\nSome tests failed. Check your subscription and try 'best' to switch nodes.")

def shell_env():
    proxy_url = f"http://127.0.0.1:{PROXY_PORT}"
    print(f"export http_proxy={proxy_url}")
    print(f"export https_proxy={proxy_url}")
    print(f"export all_proxy=socks5://127.0.0.1:{PROXY_PORT}")
    print(f"export HTTP_PROXY={proxy_url}")
    print(f"export HTTPS_PROXY={proxy_url}")
    print(f"export ALL_PROXY=socks5://127.0.0.1:{PROXY_PORT}")
    print("# Copy and paste the above lines into your terminal, or run:")
    print(f"# eval $(python3 {os.path.abspath(__file__)} env)")

def main():
    parser = argparse.ArgumentParser(
        prog="svpn",
        description="SVPN - Server VPN Manager for Linux. Provides internet access to any Linux server without disrupting existing services."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("install", help="Download and install proxy core (Mihomo)")
    subparsers.add_parser("start", help="Start the VPN proxy service")
    subparsers.add_parser("stop", help="Stop the VPN proxy service")
    subparsers.add_parser("status", help="Check proxy status and current node")
    subparsers.add_parser("update", help="Update node subscription from provider URL")
    subparsers.add_parser("best", help="Test all nodes and switch to the best one")
    subparsers.add_parser("test", help="Test connectivity through the VPN proxy")
    subparsers.add_parser("env", help="Print proxy environment variable commands")
    subparsers.add_parser("setup-env", help="Configure proxy environment in ~/.bashrc")
    subparsers.add_parser("nodes", help="List all available nodes from subscription")

    parser_add_sub = subparsers.add_parser("add-sub", help="Add or update subscription URL")
    parser_add_sub.add_argument("url", help="Subscription URL")

    parser_set_filter = subparsers.add_parser("set-filter", help="Set node filter regex (empty to use all)")
    parser_set_filter.add_argument("pattern", nargs="?", default="", help="Regex pattern to filter nodes")

    args = parser.parse_args()

    if args.command == "install":
        download_mihomo()
    elif args.command == "add-sub":
        set_subscription(args.url)
    elif args.command == "start":
        start_proxy()
    elif args.command == "stop":
        stop_proxy()
    elif args.command == "status":
        status_proxy()
    elif args.command == "update":
        update_subscription()
    elif args.command == "best":
        best_node()
    elif args.command == "test":
        test_connection()
    elif args.command == "env":
        shell_env()
    elif args.command == "setup-env":
        setup_persistent_proxy()
    elif args.command == "nodes":
        list_nodes()
    elif args.command == "set-filter":
        set_node_filter(args.pattern)
        if is_running():
            print("\nRestart VPN to apply new filter:")
            print("  python3 svpn.py stop && python3 svpn.py start")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
