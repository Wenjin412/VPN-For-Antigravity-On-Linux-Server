# SVPN - Server VPN Manager for Linux

SVPN is a lightweight, reliable VPN manager designed for **any Linux server** that needs external internet access. Built on [Mihomo](https://github.com/MetaCubeX/mihomo) (Clash Meta), it provides on-demand proxy services **without disrupting any existing services** running on your server.

Whether your server is behind a firewall, in a restricted network, or simply needs access to global resources (GitHub, Google, Docker Hub, npm, PyPI, etc.), SVPN gets you connected safely.

## Features

- **Plug and Play**: Pure Python 3, no third-party dependencies. Automatically detects OS and architecture (Linux amd64/arm64, macOS), downloads the correct proxy core from GitHub mirrors, and guides you through subscription setup.
- **On-Demand Proxy, Zero Disruption**: SVPN runs a local proxy (default `127.0.0.1:7890` for HTTP/SOCKS5). **No iptables, no system-wide routing changes** — your existing services, APIs, and applications continue to work exactly as before. Only programs that explicitly use the proxy will route through VPN.
- **Smart Routing**: Built-in geographic and domain-based rules ensure that traffic to local networks, private IPs, and domestic (CN) destinations goes direct, while only blocked or overseas traffic uses the VPN tunnel.
- **Auto Best-Node Selection**: URL-Test strategy continuously measures latency across all nodes in your subscription and automatically switches to the fastest one.
- **Multiple GitHub Mirrors**: Automatically tries several GitHub mirror sites for downloading the core binary, ensuring reliable installation even in restricted networks.

## Quick Start

### 1. Get the code

```bash
git clone https://github.com/Wenjin412/VPN-For-Antigravity-On-Linux-Server.git
cd VPN-For-Antigravity-On-Linux-Server
```

### 2. Start the proxy

```bash
python3 svpn.py start
```

On first run, SVPN will:
1. **Download and install** the Mihomo proxy core (auto-detected for your platform).
2. **Prompt for your subscription URL** (supports Base64, Clash YAML, and Mihomo formats).
3. **Generate configuration** and start the proxy daemon in the background.

### 3. Enable VPN for your applications

**Option A: Set environment variables (recommended)**

```bash
# Print the environment commands
python3 svpn.py env

# Or set them directly:
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890

# Now run any command that needs internet access:
git clone https://github.com/some/repo.git
curl https://www.google.com
pip install some-package
docker pull some-image
```

**Option B: For a single command**

```bash
http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 curl https://www.google.com
```

**Option C: Persistent proxy for all new shells**

Add to `~/.bashrc` or `~/.profile`:
```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
```

### 4. Test connectivity

```bash
python3 svpn.py test
```

## CLI Reference

```
python3 svpn.py <command>

Commands:
  start        Start the VPN proxy service
  stop         Stop the VPN proxy service
  status       Check proxy status and current best node
  test         Test connectivity (Google, GitHub)
  env          Print proxy environment variable export commands
  install      Download/reinstall the proxy core
  add-sub URL  Add or update subscription URL
  update       Refresh subscription (pull new/removed nodes)
  best         Test all nodes and switch to the fastest one
```

## How It Works

```
┌──────────────────────────────────────────────────┐
│                  Your Linux Server                │
│                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │
│  │  App A   │  │  App B   │  │ Existing APIs   │  │
│  │(proxy on)│  │(proxy on)│  │ (no proxy set)  │  │
│  └────┬─────┘  └────┬─────┘  └───────┬─────────┘  │
│       │              │                │            │
│       ▼              ▼                ▼            │
│  ┌─────────────────────────┐    Direct out        │
│  │   SVPN (Mihomo proxy)   │                      │
│  │   127.0.0.1:7890        │                      │
│  └───────────┬─────────────┘                      │
│              │ VPN tunnel                          │
└──────────────┼────────────────────────────────────┘
               ▼
        ┌──────────────┐
        │  VPN Server   │
        │  (overseas)   │
        └──────┬───────┘
               │
               ▼
         Internet (Google, GitHub, etc.)
```

- Apps **with** proxy env vars → route through VPN → access blocked sites
- Apps **without** proxy env vars → direct connection → not affected at all
- Your web APIs, database connections, internal services all continue working normally

## Data Directory

SVPN creates a `data/` directory alongside the script:

```
data/
├── mihomo          # Proxy core binary
├── mihomo.pid      # Process ID file
├── mihomo.log      # Runtime logs
├── sub_url.txt     # Saved subscription URL
└── config.yaml     # Generated routing configuration
```

## Requirements

- Python 3.6+
- Linux (amd64/arm64) or macOS
- A valid proxy subscription URL (from your VPN service provider)
