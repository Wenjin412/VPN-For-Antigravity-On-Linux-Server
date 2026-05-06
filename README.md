# SVPN - Server VPN Manager for Linux

SVPN is a lightweight, reliable VPN manager designed for **any Linux server** that needs external internet access. Built on [Mihomo](https://github.com/MetaCubeX/mihomo) (Clash Meta), it provides on-demand proxy services **without disrupting any existing services** running on your server.

Whether your server is behind a firewall, in a restricted network, or simply needs access to global resources (GitHub, Google, Docker Hub, npm, PyPI, etc.), SVPN gets you connected safely.

## Features

- **Plug and Play**: Pure Python 3, no third-party dependencies. Automatically detects OS and architecture (Linux amd64/arm64, macOS), downloads the correct proxy core from GitHub mirrors, and guides you through subscription setup.
- **Auto Environment Setup**: On first start, SVPN automatically configures proxy environment variables in `~/.bashrc` so all new terminals have VPN access by default.
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
4. **Automatically configure proxy environment variables** in `~/.bashrc`.

### 3. Apply environment variables

```bash
# Apply proxy settings to current terminal
source ~/.bashrc
```

Or simply open a new terminal - proxy will be active automatically.

### 4. Verify it's working

```bash
# Should show VPN server location (e.g., United States), not your real location
curl -s ipinfo.io | grep country

# Or run the built-in test
python3 svpn.py test
```

That's it! Now all your terminal applications (git, curl, pip, docker, npm, etc.) will use the VPN automatically.

## CLI Reference

```
python3 svpn.py <command>

Commands:
  start        Start the VPN proxy service (auto-configures ~/.bashrc)
  stop         Stop the VPN proxy service
  status       Check proxy status and current best node
  test         Test connectivity (Google, GitHub, OpenAI)
  nodes        List all available nodes from subscription
  set-filter   Set node filter regex pattern (empty = use all nodes)
  env          Print proxy environment variable export commands
  setup-env    Configure proxy environment variables in ~/.bashrc
  install      Download/reinstall the proxy core
  add-sub URL  Add or update subscription URL
  update       Refresh subscription (pull new/removed nodes)
  best         Test all nodes and switch to the fastest one
```

## Node Selection

By default, SVPN uses **all nodes** in your subscription for automatic selection. You can filter nodes by region:

```bash
# List all available nodes
python3 svpn.py nodes

# Filter for US nodes only
python3 svpn.py set-filter '(?i)us|美国|USA'

# Filter for Japan nodes
python3 svpn.py set-filter '(?i)jp|日本|Japan'

# Filter for Hong Kong nodes
python3 svpn.py set-filter '(?i)hk|香港|Hong Kong'

# Clear filter (use all nodes)
python3 svpn.py set-filter ''

# Restart to apply new filter
python3 svpn.py stop && python3 svpn.py start
```

The filter uses **regex pattern matching** on node names. Common patterns:
- `(?i)` makes the match case-insensitive
- Use `|` for OR matching (e.g., `us|美国|USA`)

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

## Environment Variables

After running `svpn.py start`, the following variables are set in `~/.bashrc`:

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7890
export no_proxy=localhost,127.0.0.1,::1,*.local
export NO_PROXY=localhost,127.0.0.1,::1,*.local
```

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

## Troubleshooting

### Proxy running but not working

**Symptom**: `svpn.py status` shows the proxy is running, but `curl ipinfo.io` still shows your real location.

**Solution**:

```bash
# Check if proxy env vars are set
echo $http_proxy

# If empty, apply them
source ~/.bashrc

# Or run the setup command
python3 svpn.py setup-env
```

### Verify proxy is correctly routing traffic

```bash
# Without proxy (shows your real IP)
curl -s ipinfo.io | grep country

# With proxy (should show VPN server country, e.g., "US")
curl -x http://127.0.0.1:7890 -s ipinfo.io | grep country
```

### No nodes available / "Available proxies: 0"

If `svpn.py status` shows 0 available proxies:

1. Check what nodes are in your subscription:
   ```bash
   python3 svpn.py nodes
   ```

2. If you see nodes but they don't match your filter, clear the filter to use all nodes:
   ```bash
   python3 svpn.py set-filter ''
   python3 svpn.py stop && python3 svpn.py start
   ```

3. If `nodes` shows no nodes, update your subscription:
   ```bash
   python3 svpn.py update
   ```

### Node names don't contain country codes

Some subscriptions use custom node names without country identifiers. Use `svpn.py nodes` to see actual node names, then set a filter that matches them, or clear the filter to use all nodes.

## Requirements

- Python 3.6+
- Linux (amd64/arm64) or macOS
- A valid proxy subscription URL (from your VPN service provider)

## License

MIT License
