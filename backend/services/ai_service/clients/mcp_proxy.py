"""Operator-owned MCP egress policy, separate from per-user connectors."""
import os
import re
from urllib.parse import urlsplit


def proxy_for(host):
    proxy = os.getenv('MCP_HTTP_PROXY', '').strip()
    raw_hosts = os.getenv('MCP_PROXY_HOSTS', '').strip()
    if not proxy and not raw_hosts:
        return None
    if not proxy or not raw_hosts:
        raise ValueError('MCP proxy requires both address and exact hostname allowlist')
    try:
        p = urlsplit(proxy)
        valid = (p.scheme == 'http' and p.hostname in ('127.0.0.1', '::1')
                 and p.port is not None and 1 <= p.port <= 65535
                 and not (p.username or p.password or p.query or p.fragment)
                 and p.path in ('', '/') and not any(c.isspace() for c in proxy))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('MCP proxy must be an explicit loopback HTTP proxy with a port')
    hosts = [h.strip().lower() for h in raw_hosts.split(',')]
    label = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    for h in hosts:
        if (len(h) > 253 or not re.fullmatch(rf'(?:{label}\.)+[a-z]{{2,63}}', h)
                or h.endswith(('.localhost', '.local', '.internal', '.home', '.test', '.invalid'))):
            raise ValueError('MCP proxy allowlist requires exact public DNS hostnames, no wildcards or IPs')
    # No suffix match: subdomains and similarly named domains need their own entry.
    return proxy if host.lower() in hosts else None
