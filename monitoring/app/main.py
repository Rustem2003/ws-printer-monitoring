"""
Enterprise Printer Monitoring Service
ICMP Ping + SNMP v1/v2c/v3 collector + on-demand HTTP /check
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException

# SNMP OIDs (RFC 1759 / Printer MIB)
SNMP_OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    # Printer status (hrPrinterStatus / hrDeviceStatus)
    "printer_status": "1.3.6.1.2.1.25.3.5.1.1.1",
    "device_status": "1.3.6.1.2.1.25.3.2.1.5.1",
    # Printer MIB supplies (RFC 1759)
    "prtMarkerSuppliesLevel": "1.3.6.1.2.1.43.11.1.1.9",
    "prtMarkerSuppliesMaxCapacity": "1.3.6.1.2.1.43.11.1.1.8",
    "prtMarkerSuppliesDescription": "1.3.6.1.2.1.43.11.1.1.6",
    "prtMarkerSuppliesType": "1.3.6.1.2.1.43.11.1.1.5",
    # Page counter
    "prtMarkerLifeCount": "1.3.6.1.2.1.43.10.2.1.4.1.1",
    # Alerts
    "prtAlertCode": "1.3.6.1.2.1.43.18.1.1.7",
    "prtAlertDescription": "1.3.6.1.2.1.43.18.1.1.4",
    "prtAlertSeverity": "1.3.6.1.2.1.43.18.1.1.6",
    # Serial / firmware
    "serial": "1.3.6.1.2.1.43.5.1.1.17.1",
}

STATUS_MAP = {
    1: ("other", "warning"),
    2: ("unknown", "warning"),
    3: ("idle", "info"),
    4: ("printing", "info"),
    5: ("warmup", "info"),
}

DEV_STATUS_MAP = {
    1: ("unknown", "warning"),
    2: ("running", "info"),
    3: ("warning", "warning"),
    4: ("testing", "info"),
    5: ("down", "critical"),
}

ERROR_PATTERNS = {
    "paper_jam": ["jam"],
    "no_paper": ["no paper", "paper empty", "paper out", "tray empty", "out of paper"],
    "open_cover": ["cover open", "door open"],
    "scanner_error": ["scanner"],
    "fuser_error": ["fuser"],
    "drum_error": ["drum"],
    "toner_error": ["toner empty", "toner low", "no toner", "toner error", "low toner", "replace toner"],
    "service_required": ["service required", "service call"],
    "maintenance_required": ["maintenance"],
}

INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "60"))
SNMP_COMMUNITY = os.getenv("SNMP_COMMUNITY", "public")
NOTIFICATION_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:9002")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {}


async def ping_host(ip: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "2", "-W", "2", ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception:
        return False


def _parse_snmp_value(line: str) -> str | None:
    """Parse a single 'OID = TYPE: value' line."""
    if "=" not in line:
        return None
    rhs = line.split("=", 1)[1].strip()
    if ":" in rhs:
        rhs = rhs.split(":", 1)[1].strip()
    return rhs.strip('"')


async def snmp_get(ip: str, oid: str, community: str = "public", version: str = "2c") -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "snmpget", f"-v{version}", "-c", community, "-t", "3", "-r", "1",
            "-Oqv",  # output as quoted value only
            ip, oid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        if proc.returncode == 0 and stdout:
            return stdout.decode().strip().strip('"') or None
    except Exception:
        pass
    return None


async def snmp_walk_pairs(ip: str, oid: str, community: str = "public", version: str = "2c") -> list[tuple[str, str]]:
    """Walk OID, return list of (suffix, value) pairs preserving order."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "snmpwalk", f"-v{version}", "-c", community, "-t", "3", "-r", "1",
            "-On",  # numeric OIDs
            ip, oid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        if proc.returncode != 0 or not stdout:
            return []
        out = []
        for line in stdout.decode().strip().split("\n"):
            if "=" not in line:
                continue
            full_oid, rhs = line.split("=", 1)
            full_oid = full_oid.strip()
            suffix = full_oid.rsplit(".", 1)[-1]
            val = rhs.strip()
            if ":" in val:
                val = val.split(":", 1)[1].strip()
            out.append((suffix, val.strip('"')))
        return out
    except Exception:
        return []


async def snmp_walk(ip: str, oid: str, community: str = "public", version: str = "2c") -> list[str]:
    return [v for _, v in await snmp_walk_pairs(ip, oid, community, version)]


def classify_error(desc: str) -> dict | None:
    d = (desc or "").lower()
    for event_type, keywords in ERROR_PATTERNS.items():
        for kw in keywords:
            if kw in d:
                severity = "critical" if event_type in ("fuser_error", "drum_error", "service_required") else "warning"
                return {
                    "event_type": event_type,
                    "severity": severity,
                    "message": f"{event_type.replace('_', ' ').title()}: {desc[:200]}",
                }
    return None


def detect_consumable_color(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ("black", "bk ", "k toner", "schwarz")): return "Black"
    if any(k in n for k in ("cyan", "blue")): return "Cyan"
    if any(k in n for k in ("magenta", "red")): return "Magenta"
    if any(k in n for k in ("yellow", "gelb")): return "Yellow"
    if "drum" in n: return "Drum"
    if "fuser" in n: return "Fuser"
    return name or "Supply"


async def collect_printer(printer: dict) -> dict:
    """Collect full status snapshot for a single printer."""
    ip = printer["ip_address"]
    community = printer.get("snmp_community") or SNMP_COMMUNITY
    version = printer.get("snmp_version") or "2c"

    is_alive = await ping_host(ip)
    if not is_alive:
        return {
            "printer_id": printer["id"],
            "status_code": 7,
            "status_text": "no_response",
            "is_online": False,
            "consumables": [],
            "events": [{
                "event_type": "offline",
                "severity": "critical",
                "message": f"Printer {printer.get('name') or ip} is unreachable (ping failed)",
            }],
        }

    # Probe sysDescr, status, supplies, alerts concurrently
    sys_descr_t = asyncio.create_task(snmp_get(ip, SNMP_OIDS["sysDescr"], community, version))
    dev_status_t = asyncio.create_task(snmp_get(ip, SNMP_OIDS["device_status"], community, version))
    page_count_t = asyncio.create_task(snmp_get(ip, SNMP_OIDS["prtMarkerLifeCount"], community, version))
    serial_t = asyncio.create_task(snmp_get(ip, SNMP_OIDS["serial"], community, version))

    levels_t = asyncio.create_task(snmp_walk_pairs(ip, SNMP_OIDS["prtMarkerSuppliesLevel"], community, version))
    descs_t = asyncio.create_task(snmp_walk_pairs(ip, SNMP_OIDS["prtMarkerSuppliesDescription"], community, version))
    maxes_t = asyncio.create_task(snmp_walk_pairs(ip, SNMP_OIDS["prtMarkerSuppliesMaxCapacity"], community, version))

    alert_descs_t = asyncio.create_task(snmp_walk(ip, SNMP_OIDS["prtAlertDescription"], community, version))

    sys_descr = await sys_descr_t
    dev_status = await dev_status_t
    page_count_raw = await page_count_t
    serial = await serial_t
    levels = await levels_t
    descs = await descs_t
    maxes = await maxes_t
    alert_descs = await alert_descs_t

    # If SNMP is non-responsive entirely, mark offline despite ping
    snmp_responding = bool(sys_descr or levels or alert_descs)
    if not snmp_responding:
        return {
            "printer_id": printer["id"],
            "status_code": 2,
            "status_text": "no_snmp",
            "is_online": False,
            "consumables": [],
            "events": [{
                "event_type": "no_response",
                "severity": "critical",
                "message": f"Printer {printer.get('name') or ip}: SNMP не отвечает (community={community})",
            }],
        }

    # Status decoding
    try:
        dev_status_code = int(dev_status) if dev_status else None
    except ValueError:
        dev_status_code = None
    if dev_status_code in DEV_STATUS_MAP:
        status_text, severity_hint = DEV_STATUS_MAP[dev_status_code]
    else:
        status_text, severity_hint = ("idle", "info")
    is_online = dev_status_code not in (5,)  # 5=down

    # Build consumables: match by index
    desc_map = {sfx: val for sfx, val in descs}
    max_map = {sfx: val for sfx, val in maxes}
    consumables = []
    for sfx, level_str in levels:
        name = desc_map.get(sfx) or f"Supply {sfx}"
        try:
            current = float(level_str)
        except ValueError:
            continue
        try:
            max_cap = int(max_map.get(sfx, "0"))
        except ValueError:
            max_cap = 0
        # Some printers return -3 (unknown), -2 (other) — skip
        if current < 0:
            continue
        consumables.append({
            "name": detect_consumable_color(name),
            "current_level": current,
            "max_capacity": max_cap if max_cap > 0 else None,
        })

    # Alert events
    events = []
    for desc in alert_descs:
        if not desc:
            continue
        ev = classify_error(desc)
        if ev and not any(e["event_type"] == ev["event_type"] for e in events):
            events.append(ev)

    # Low toner thresholds
    for c in consumables:
        if c.get("max_capacity") and c["max_capacity"] > 0:
            pct = c["current_level"] * 100.0 / c["max_capacity"]
        else:
            pct = c["current_level"] if 0 <= c["current_level"] <= 100 else -1
        if 0 <= pct <= 5:
            events.append({
                "event_type": "toner_error",
                "severity": "critical",
                "message": f"{c['name']} критически низкий уровень: {pct:.0f}%",
            })
        elif pct <= 20:
            events.append({
                "event_type": "toner_error",
                "severity": "warning",
                "message": f"{c['name']} низкий уровень: {pct:.0f}%",
            })

    try:
        page_count = int(page_count_raw) if page_count_raw else None
    except ValueError:
        page_count = None

    return {
        "printer_id": printer["id"],
        "status_code": dev_status_code or 3,
        "status_text": status_text,
        "is_online": is_online,
        "page_count": page_count,
        "consumables": consumables,
        "events": events,
        "serial_number": serial[:120] if serial else None,
        "raw_snmp_data": {"sysDescr": sys_descr[:300] if sys_descr else None},
    }


async def push_result(client: httpx.AsyncClient, result: dict):
    pid = result["printer_id"]
    try:
        r = await client.post(f"{BACKEND_URL}/api/v1/printers/{pid}/status", json=result)
        if r.status_code not in (200, 201):
            print(f"[monitor] backend rejected status for #{pid}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[monitor] backend push error #{pid}: {e}")

    for event in result.get("events", []):
        try:
            await client.post(
                f"{NOTIFICATION_URL}/send",
                json={
                    "printer_id": pid,
                    "event_type": event["event_type"],
                    "severity": event["severity"],
                    "message": event["message"],
                },
                timeout=10.0,
            )
        except Exception:
            pass


async def collect_and_push_one(printer_id: int) -> dict:
    """Fetch single printer, collect, push. Used by on-demand /check."""
    async with httpx.AsyncClient(timeout=30.0, headers=INTERNAL_HEADERS) as client:
        r = await client.get(f"{BACKEND_URL}/api/v1/printers/{printer_id}")
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Printer #{printer_id} not found (backend {r.status_code})")
        printer = r.json()
        result = await collect_printer(printer)
        await push_result(client, result)
        return {
            "printer_id": printer_id,
            "status": result.get("status_text"),
            "is_online": result.get("is_online"),
            "consumables": result.get("consumables"),
            "events_count": len(result.get("events", [])),
        }


async def monitoring_loop():
    print(f"[monitor] loop started, interval={INTERVAL_SECONDS}s, backend={BACKEND_URL}")
    while True:
        try:
            async with httpx.AsyncClient(timeout=60.0, headers=INTERNAL_HEADERS) as client:
                resp = await client.get(f"{BACKEND_URL}/api/v1/printers?page_size=200")
                if resp.status_code != 200:
                    print(f"[monitor] fetch printers failed: {resp.status_code}")
                else:
                    printers = resp.json().get("items", [])
                    print(f"[monitor] checking {len(printers)} printers")
                    tasks = [collect_printer(p) for p in printers]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if isinstance(res, Exception):
                            print(f"[monitor] collect error: {res}")
                            continue
                        await push_result(client, res)
        except Exception as e:
            print(f"[monitor] loop error: {e}")
        await asyncio.sleep(INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(monitoring_loop())
    yield
    task.cancel()


app = FastAPI(title="Printer Monitoring Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "monitoring-service", "interval": INTERVAL_SECONDS}


@app.post("/check/{printer_id}")
async def check_now(printer_id: int):
    return await collect_and_push_one(printer_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
