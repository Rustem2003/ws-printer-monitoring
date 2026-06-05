"""
Enterprise Printer Discovery Service
SNMP Broadcast, Nmap, Ping Sweep
"""
import asyncio
import json
import os
import socket
import ipaddress

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, BackgroundTasks
from datetime import datetime, timezone

app = FastAPI(title="Printer Discovery Service")

SUBNETS = os.getenv("SUBNETS", "192.168.0.0/24,10.0.0.0/24")
DISCOVERY_METHOD = os.getenv("DISCOVERY_METHOD", "snmp_broadcast")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")
NOTIFICATION_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:9002")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {}

# SNMP printer vendor OID fingerprints
VENDOR_OIDS = {
    "HP": "1.3.6.1.4.1.11",
    "Xerox": "1.3.6.1.4.1.253",
    "Canon": "1.3.6.1.4.1.1602",
    "Brother": "1.3.6.1.4.1.2435",
    "Kyocera": "1.3.6.1.4.1.1347",
    "Ricoh": "1.3.6.1.4.1.367",
    "Konica Minolta": "1.3.6.1.4.1.18334",
    "Epson": "1.3.6.1.4.1.1248",
}


async def ping_sweep(subnet: str) -> list[str]:
    """Ping sweep an entire subnet."""
    active_ips = []
    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts = list(network.hosts())[:256]

    tasks = []
    for host in hosts:
        ip = str(host)
        tasks.append(_ping_single(ip))

    results = await asyncio.gather(*tasks)
    for ip, alive in zip([str(h) for h in hosts], results):
        if alive:
            active_ips.append(ip)
    return active_ips


async def _ping_single(ip: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "2", ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception:
        return False


async def snmp_probe(ip: str, community: str = "public") -> dict | None:
    """Probe an IP for SNMP printer info."""
    try:
        # Try to get sysDescr
        proc = await asyncio.create_subprocess_exec(
            "snmpget", "-v2c", "-c", community, "-t", "3", "-r", "1",
            ip, "1.3.6.1.2.1.1.1.0",  # sysDescr
            "1.3.6.1.2.1.1.5.0",       # sysName
            "1.3.6.1.2.1.25.3.2.1.3.1", # hrDeviceDescr
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)

        if not stdout or proc.returncode != 0:
            return None

        text = stdout.decode().lower()

        # Check if device is a printer
        printer_keywords = ["printer", "mfp", "multifunction", "laserjet", "workcentre",
                           "pixma", "imageclass", "docuprint", "phaser", "versalink"]

        is_printer = any(kw in text for kw in printer_keywords)
        if not is_printer:
            # Check vendor OIDs as fallback
            for vendor, oid in VENDOR_OIDS.items():
                try:
                    p = await asyncio.create_subprocess_exec(
                        "snmpget", "-v2c", "-c", community, "-t", "2",
                        ip, f"{oid}.1.0",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await p.wait()
                    if p.returncode == 0:
                        is_printer = True
                        break
                except Exception:
                    pass

        if not is_printer:
            return None

        # Parse lines to extract name and vendor
        lines = stdout.decode().strip().split("\n")
        sys_name = ""
        sys_descr = ""
        for line in lines:
            if "STRING:" in line:
                val = line.split("STRING:")[-1].strip().strip('"')
                if "sysName" in line or "1.1.5" in line:
                    sys_name = val
                elif not sys_descr:
                    sys_descr = val

        # Detect vendor
        vendor = "Unknown"
        for v_name, v_oid in VENDOR_OIDS.items():
            if v_name.lower() in text:
                vendor = v_name
                break

        return {
            "name": sys_name or f"Printer-{ip}",
            "ip_address": ip,
            "vendor": vendor,
            "model": sys_descr[:200] if sys_descr else None,
            "snmp_version": "2c",
            "snmp_community": community,
        }
    except Exception:
        return None


async def snmp_broadcast_discovery(subnet: str) -> list[dict]:
    """Discover printers via SNMP broadcast."""
    devices = []
    active_ips = await ping_sweep(subnet)
    print(f"[discovery] Found {len(active_ips)} active hosts in {subnet}")

    # Probe each active IP with SNMP
    tasks = [snmp_probe(ip) for ip in active_ips]
    results = await asyncio.gather(*tasks)

    for r in results:
        if r:
            devices.append(r)

    print(f"[discovery] Found {len(devices)} printers in {subnet}")
    return devices


async def nmap_discovery(subnet: str) -> list[dict]:
    """Discover printers via Nmap SNMP + printer ports."""
    devices = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "nmap", "-p", "161,515,631,9100", "--open",
            "-oX", "-", subnet,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60.0)

        if stdout:
            # Parse nmap XML output (simplified — extract IPs)
            for line in stdout.decode().split("\n"):
                if "addrtype=\"ipv4\"" in line and "addr=\"" in line:
                    ip = line.split("addr=\"")[1].split("\"")[0]
                    # Probe with SNMP
                    info = await snmp_probe(ip)
                    if info:
                        devices.append(info)
    except Exception as e:
        print(f"[discovery] Nmap error: {e}")

    return devices


async def run_discovery(subnet: str, method: str, job_id: int | None = None):
    """Run the discovery process."""
    print(f"[discovery] Starting {method} discovery on {subnet}")

    if method == "nmap":
        devices = await nmap_discovery(subnet)
    else:
        devices = await snmp_broadcast_discovery(subnet)

    # Register discovered printers via backend API
    added = 0
    async with httpx.AsyncClient(timeout=30.0, headers=INTERNAL_HEADERS) as client:
        for device in devices:
            try:
                resp = await client.post(
                    f"{BACKEND_URL}/api/v1/printers",
                    json=device,
                )
                if resp.status_code in (200, 201):
                    added += 1
                else:
                    print(f"[discovery] Backend rejected {device.get('ip_address')}: {resp.status_code} {resp.text[:200]}")
            except Exception as e:
                print(f"[discovery] Failed to register {device.get('ip_address')}: {e}")

        if job_id:
            try:
                await client.put(
                    f"{BACKEND_URL}/api/v1/discovery/status",
                    json={
                        "job_id": job_id,
                        "status": "completed",
                        "devices_found": len(devices),
                        "devices_added": added,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as e:
                print(f"[discovery] Failed to update job status: {e}")

        if added > 0:
            try:
                await client.post(
                    f"{NOTIFICATION_URL}/send",
                    json={
                        "event_type": "discovered",
                        "severity": "info",
                        "message": f"🔍 Discovery completed on {subnet}: found {len(devices)} printers, added {added} new",
                    },
                )
            except Exception:
                pass

    print(f"[discovery] Completed: {len(devices)} found, {added} added")


@app.post("/scan")
async def trigger_scan(data: dict):
    """External trigger for scanning."""
    subnet = data.get("subnet", SUBNETS.split(",")[0])
    method = data.get("method", DISCOVERY_METHOD)
    job_id = data.get("job_id")

    asyncio.create_task(run_discovery(subnet, method, job_id))
    return {"status": "started", "subnet": subnet, "method": method}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "discovery-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
