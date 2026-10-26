import os, platform, subprocess, re, time
import psutil

# nvidia-smi takes ~80 ms and briefly touches the GPU driver, so it must never
# run on the dashboard refresh loop. Results are cached and only refreshed when
# the Performance page actually needs them.
_GPU_CACHE = {"at": 0.0, "data": None}
_GPU_TTL = 15.0


def gpu_snapshot(max_age=_GPU_TTL):
    """GPU name/load/temperature, refreshed at most every *max_age* seconds."""
    now = time.time()
    cached = _GPU_CACHE["data"]
    if cached is not None and now - _GPU_CACHE["at"] < max_age:
        return dict(cached)

    data = {"gpu": None, "gpu_temp": None, "gpu_name": None}
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, encoding="oem", errors="replace",
            timeout=1.5, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        parts = p.stdout.strip().splitlines()[0].split(",")
        data["gpu_name"] = parts[0].strip()
        data["gpu"] = float(parts[1].strip())
        if parts[2].strip().isdigit():
            data["gpu_temp"] = float(parts[2].strip())
    except Exception:
        pass

    _GPU_CACHE["at"] = now
    _GPU_CACHE["data"] = data
    return dict(data)


def snapshot(include_gpu=False):
    """Cheap CPU/RAM/disk sample. GPU data is opt-in and cached."""
    vm = psutil.virtual_memory()
    try:
        drive = os.environ.get("SystemDrive", "C:") + "\\"
        disk = psutil.disk_usage(drive)
    except Exception:
        disk = psutil.disk_usage(os.path.abspath(os.sep))
    d = {"cpu": psutil.cpu_percent(None), "ram": vm.percent,
         "ram_used": vm.used/1024**3, "ram_total": vm.total/1024**3,
         "disk": disk.percent, "disk_used": disk.used/1024**3, "disk_total": disk.total/1024**3,
         "gpu": None, "gpu_temp": None, "gpu_name": None}
    if include_gpu:
        d.update(gpu_snapshot())
    return d


def ping_host(host, count=4, timeout=2):
    host = (host or "").strip()
    if not host or len(host) > 253 or any(c.isspace() for c in host):
        raise ValueError("Enter a valid host or IP address.")
    kwargs = {}
    if platform.system().lower() == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout*1000), host]
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        # Windows console tools emit OEM code page text, not UTF-8.
        kwargs["encoding"] = "oem"
        kwargs["errors"] = "replace"
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=count*timeout+5, **kwargs)
    except subprocess.TimeoutExpired:
        return None, 100, ""
    out = (p.stdout or "") + "\n" + (p.stderr or "")
    avg = None; loss = None
    m = re.search(r"(?:Average|Moyenne|Durchschnitt|Mittelwert|Promedio|Média|Media|Среднее)\s*=\s*(\d+)\s*ms", out, re.I)
    if not m: m = re.search(r"avg[/= ]+([\d.]+)", out, re.I)
    if m: avg = float(m.group(1))
    if avg is None:
        vals = [float(x) for x in re.findall(r"(?:time|temps|zeit|tiempo|tempo|время)[=<]([\d.]+)\s*ms", out, re.I)]
        if vals: avg = sum(vals)/len(vals)
    m = re.search(r"\((\d+)%\s*(?:loss|perte|verlust|pérdida|perda|потерь)\)", out, re.I)
    if not m: m = re.search(r"(\d+)%\s*(?:packet loss|perte)", out, re.I)
    if m: loss = int(m.group(1))
    if loss is None:
        sent = re.search(r"Sent\s*=\s*(\d+)", out, re.I)
        rec = re.search(r"Received\s*=\s*(\d+)", out, re.I)
        if sent and rec and int(sent.group(1)): loss = round((1-int(rec.group(1))/int(sent.group(1)))*100)
    if loss is None: loss = 100 if p.returncode else 0
    return avg, loss, out
