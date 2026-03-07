#!/usr/bin/env python3
"""
agvpn.py - Antigravity Server VPN Manager
A lightweight CLI tool to manage a local Mihomo proxy for bypassing server-side API auth blocks.
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

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.yaml")
SUB_FILE = os.path.join(DATA_DIR, "sub_url.txt")
PID_FILE = os.path.join(DATA_DIR, "mihomo.pid")
MIHOMO_BIN = os.path.join(DATA_DIR, "mihomo")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_platform_info():
    sys_name = os.uname().sysname.lower()
    machine = os.uname().machine.lower()
    
    os_map = {'linux': 'linux', 'darwin': 'darwin'}
    if machine in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'arm64'
    else:
        arch = machine
        
    return os_map.get(sys_name, sys_name), arch

def download_mihomo():
    ensure_data_dir()
    os_name, arch = get_platform_info()
    version = "v1.18.3"
    print(f"Detected OS: {os_name}, Arch: {arch}")
    
    if os_name == 'darwin':
        download_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-darwin-{arch}-{version}.gz"
    else:
        if arch == 'amd64':
             download_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-linux-{arch}-compatible-{version}.gz"
        else:
             download_url = f"https://github.com/MetaCubeX/mihomo/releases/download/{version}/mihomo-linux-{arch}-{version}.gz"
    
    download_url = "https://ghfast.top/" + download_url
    gz_path = os.path.join(DATA_DIR, "mihomo.gz")
    
    print(f"Downloading Mihomo from {download_url}...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response, open(gz_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download complete. Extracting...")
        
        with gzip.open(gz_path, 'rb') as f_in:
            with open(MIHOMO_BIN, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        os.remove(gz_path)
        os.chmod(MIHOMO_BIN, 0o755)
        print("Installation complete. Executable saved at:", MIHOMO_BIN)
    except Exception as e:
        print(f"Error during installation {e}")
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
        if url:
            return url
    return None

def generate_config():
    sub_url = get_subscription()
    if not sub_url:
        print("首次启动需要提供节点订阅链接 (Base64/Mihomo格式均可)。")
        sub_url = input("请输入您的订阅 URL: ").strip()
        if not sub_url:
            print("您必须输入一个有效的订阅链接才能继续。")
            sys.exit(1)
        set_subscription(sub_url)
    
    config_yaml = f"""
mixed-port: 7890
allow-lan: true
mode: rule
log-level: info
external-controller: 127.0.0.1:9090

geo-auto-update: true
geo-update-interval: 24
geox-url:
  geoip: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat"
  geosite: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat"
  mmdb: "https://ghfast.top/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/Country.mmdb"

proxy-providers:
  agvpn-provider:
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
      - agvpn-provider
    url: 'http://www.gstatic.com/generate_204'
    interval: 300
    tolerance: 50

rules:
  - DOMAIN-SUFFIX,google.com,PROXY
  - DOMAIN-SUFFIX,googleapis.com,PROXY
  - DOMAIN-KEYWORD,google,PROXY
  - DOMAIN-SUFFIX,github.com,PROXY
  - DOMAIN-SUFFIX,githubusercontent.com,PROXY
  - IP-CIDR,10.0.0.0/8,DIRECT
  - IP-CIDR,172.16.0.0/12,DIRECT
  - IP-CIDR,192.168.0.0/16,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT
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
    
    # Check if process exists
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False

def start_proxy():
    if not os.path.exists(MIHOMO_BIN):
        print("首次运行，正在为您自动下载核心组件...")
        download_mihomo()
    
    generate_config()
    
    if is_running():
        with open(PID_FILE, "r") as f:
            pid = f.read().strip()
        print(f"Mihomo is already running with PID {pid}.")
        return
    
    print("Starting Mihomo...")
    log_file = os.path.join(DATA_DIR, "mihomo.log")
    
    cmd = [MIHOMO_BIN, "-d", DATA_DIR, "-f", CONFIG_FILE]
    
    kwargs = {}
    if os.name != 'nt' and hasattr(os, 'setsid'):
        kwargs['preexec_fn'] = os.setsid
        
    with open(log_file, "w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, **kwargs)
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
            
    print(f"Started Mihomo in background (PID: {proc.pid}).")
    print("Mihomo acts as HTTP/SOCKS5 proxy on 127.0.0.1:7890")
    print("To let a CLI tool use it, prefix your command or export variables:")
    print("  export http_proxy=http://127.0.0.1:7890")
    print("  export https_proxy=http://127.0.0.1:7890")

def stop_proxy():
    if not is_running():
        print("Mihomo is not running.")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return
        
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
    
    print(f"Stopping Mihomo (PID {pid})...")
    try:
        os.kill(int(pid), 15)
        for _ in range(50):
            if not is_running():
                break
            time.sleep(0.1)
        if is_running():
            print("Force killing Mihomo...")
            os.kill(int(pid), 9)
    except OSError:
        pass
    
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    print("Mihomo stopped.")

def api_request(method, path, data=None):
    url = f"http://127.0.0.1:9090{path}"
    headers = {}
    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status in [200, 204]:
                body = response.read()
                if body:
                    return json.loads(body.decode('utf-8'))
                return True
            else:
                return None
    except Exception as e:
        print(f"API request failed: {e}")
        return None

def status_proxy():
    if not is_running():
        print("Mihomo is NOT running.")
        return
        
    resp = api_request("GET", "/proxies/PROXY")
    if resp:
        print("Mihomo is RUNNING.")
        now_active = resp.get("now", "Unknown")
        print(f"Current Selected Node (URL-Test): {now_active}")
        all_proxies = resp.get("all", [])
        print(f"Total available proxies in PROXY group: {len(all_proxies)} (including DIRECT)")
    else:
        print("Mihomo is running but API is inaccessible (maybe starting up?).")

def update_subscription():
    if not is_running():
        print("Mihomo must be running to update subscriptions. Please 'start' it first.")
        return
        
    print("Sending update request to provider 'agvpn-provider'...")
    resp = api_request("PUT", "/providers/proxies/agvpn-provider")
    if resp is not None:
        print("Subscription update requested successfully. Wait a few seconds for it to refresh.")
    else:
        print("Failed to update subscription. Is Mihomo running locally?")

def best_node():
    if not is_running():
        print("Mihomo must be running. Please 'start' it first.")
        return
        
    print("Triggering delay test to find the best node...")
    resp = api_request("GET", "/providers/proxies/agvpn-provider/healthcheck")
    if resp is not None:
        print("Healthcheck triggered. Waiting for 3 seconds...")
        time.sleep(3)
        status_proxy()
    else:
        print("Failed to trigger test. Is Mihomo running locally?")

def main():
    parser = argparse.ArgumentParser(description="agvpn - Antigravity Server VPN Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("install", help="Download and install Mihomo core")
    
    parser_add_sub = subparsers.add_parser("add-sub", help="Add or update subscription URL")
    parser_add_sub.add_argument("url", help="Subscription URL string")
    
    subparsers.add_parser("start", help="Start the VPN proxy")
    subparsers.add_parser("stop", help="Stop the VPN proxy")
    subparsers.add_parser("status", help="Check VPN status and current node")
    subparsers.add_parser("update", help="Update node subscription from URL")
    subparsers.add_parser("best", help="Force URL-Test to switch to the best node")
    
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
