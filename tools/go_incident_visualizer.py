#!/usr/bin/env python3
"""
Go service incident visualizer.

Run this on the problematic Linux host to collect CPU, memory, thread,
network, IO, and optional goroutine-dump signals, then generate a standalone
HTML report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], timeout: int = 5) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    except FileNotFoundError:
        return {
            "cmd": cmd,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"command not found: {cmd[0]}",
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    except PermissionError as exc:
        return {
            "cmd": cmd,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"permission denied: {exc}",
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "ok": False,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout}s",
            "elapsed_ms": int((time.time() - started) * 1000),
        }


def read_text(path: str | Path, limit: int | None = None) -> str:
    try:
        data = Path(path).read_text(errors="replace")
        return data if limit is None else data[:limit]
    except OSError as exc:
        return f"READ_ERROR: {exc}"


def parse_kv_status(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def parse_size_kb(value: str) -> int | None:
    match = re.search(r"(\d+)\s+kB", value)
    return int(match.group(1)) if match else None


def kb_to_mb(kb: int | None) -> float | None:
    return round(kb / 1024, 2) if kb is not None else None


def find_pid_by_name(name: str) -> int | None:
    if not name:
        return None
    pgrep = run_cmd(["pgrep", "-f", name])
    if pgrep["ok"] and pgrep["stdout"]:
        for line in pgrep["stdout"].splitlines():
            try:
                pid = int(line.strip())
            except ValueError:
                continue
            if pid != os.getpid():
                return pid

    ps = run_cmd(["ps", "axo", "pid=,command="])
    for line in ps["stdout"].splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and name in parts[1]:
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            if pid != os.getpid():
                return pid
    return None


def collect_process(pid: int | None) -> dict[str, Any]:
    if pid is None:
        return {"found": False}

    proc_dir = Path(f"/proc/{pid}")
    status_text = read_text(proc_dir / "status")
    status = parse_kv_status(status_text) if not status_text.startswith("READ_ERROR") else {}
    stat = read_text(proc_dir / "stat")
    cmdline = read_text(proc_dir / "cmdline").replace("\x00", " ").strip()

    ps_one = run_cmd(["ps", "-p", str(pid), "-o", "pid,ppid,user,%cpu,%mem,rss,vsz,etime,stat,comm,args"], timeout=5)
    threads = collect_threads(pid)
    network = collect_network(pid)

    return {
        "found": proc_dir.exists(),
        "pid": pid,
        "cmdline": cmdline,
        "status_raw": status_text,
        "status": status,
        "stat_raw": stat,
        "ps": ps_one,
        "memory_mb": {
            "rss": kb_to_mb(parse_size_kb(status.get("VmRSS", ""))),
            "size": kb_to_mb(parse_size_kb(status.get("VmSize", ""))),
            "data": kb_to_mb(parse_size_kb(status.get("VmData", ""))),
        },
        "threads_count": int(status.get("Threads", "0")) if status.get("Threads", "0").isdigit() else None,
        "threads": threads,
        "network": network,
        "pmap_tail": run_cmd(["pmap", "-x", str(pid)], timeout=8),
    }


def collect_threads(pid: int) -> dict[str, Any]:
    cmd = ["ps", "-L", "-p", str(pid), "-o", "pid,tid,pcpu,pmem,stat,comm"]
    result = run_cmd(cmd, timeout=5)
    rows = []
    for line in result["stdout"].splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            rows.append(
                {
                    "pid": int(parts[0]),
                    "tid": int(parts[1]),
                    "tid_hex": format(int(parts[1]), "x"),
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "stat": parts[4],
                    "comm": " ".join(parts[5:]),
                }
            )
        except ValueError:
            continue
    rows.sort(key=lambda row: row["cpu"], reverse=True)
    return {"raw": result, "top": rows[:20]}


def collect_network(pid: int) -> dict[str, Any]:
    ss = run_cmd(["ss", "-antp"], timeout=8)
    lines = []
    states = Counter()
    pid_token = f"pid={pid},"
    for line in ss["stdout"].splitlines():
        if pid_token in line or f",{pid}," in line:
            lines.append(line)
            state = line.split()[0] if line.split() else "UNKNOWN"
            states[state] += 1
    return {"raw": ss, "lines": lines[:200], "states": dict(states), "total": sum(states.values())}


def collect_system() -> dict[str, Any]:
    return {
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "uptime": run_cmd(["uptime"]),
        "free": run_cmd(["free", "-m"]),
        "df": run_cmd(["df", "-h"]),
        "top": run_cmd(["top", "-b", "-n", "1"], timeout=8),
        "ps_cpu": run_cmd(["ps", "aux", "--sort=-%cpu"], timeout=8),
        "ps_mem": run_cmd(["ps", "aux", "--sort=-%mem"], timeout=8),
        "vmstat": run_cmd(["vmstat", "1", "2"], timeout=5),
        "iostat": run_cmd(["iostat", "-x", "1", "2"], timeout=6) if shutil.which("iostat") else {"ok": False, "stderr": "iostat not installed"},
    }


GOROUTINE_HEADER = re.compile(r"^goroutine\s+\d+\s+\[([^\]]+)\]", re.MULTILINE)


def analyze_goroutine_dump(path: str | None) -> dict[str, Any]:
    if not path:
        return {"provided": False}
    text = read_text(path)
    if text.startswith("READ_ERROR"):
        return {"provided": True, "ok": False, "error": text}

    states = Counter(GOROUTINE_HEADER.findall(text))
    stacks = re.split(r"\n(?=goroutine\s+\d+\s+\[)", text)
    hot_terms = {
        "chan send": 0,
        "chan receive": 0,
        "sync.Mutex.Lock": 0,
        "database/sql": 0,
        "net/http": 0,
        "runtime.gopark": 0,
        "syscall": 0,
        "GC": 0,
    }
    for term in hot_terms:
        hot_terms[term] = text.count(term)

    repeated_frames = Counter()
    for stack in stacks:
        for line in stack.splitlines()[1:8]:
            stripped = line.strip()
            if stripped and not stripped.startswith("/"):
                repeated_frames[stripped] += 1
                break

    return {
        "provided": True,
        "ok": True,
        "path": path,
        "goroutine_count": len(GOROUTINE_HEADER.findall(text)),
        "states": dict(states.most_common(20)),
        "hot_terms": hot_terms,
        "top_frames": dict(repeated_frames.most_common(20)),
        "sample": text[:12000],
    }


def maybe_send_quit(pid: int | None, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"sent": False}
    if pid is None:
        return {"sent": False, "error": "missing pid"}
    try:
        os.kill(pid, signal.SIGQUIT)
        return {"sent": True, "pid": pid, "note": "SIGQUIT sent; check service stdout/journal/container logs for goroutine dump."}
    except OSError as exc:
        return {"sent": False, "error": str(exc)}


def score_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    process = report.get("process", {})
    threads = process.get("threads", {}).get("top", [])
    memory = process.get("memory_mb", {})
    network = process.get("network", {})
    goroutine = report.get("goroutine", {})

    if threads:
        top = threads[0]
        if top["cpu"] >= 80:
            findings.append(
                {
                    "level": "critical",
                    "title": "单线程 CPU 接近打满",
                    "detail": f"TID {top['tid']} / 0x{top['tid_hex']} 当前 CPU {top['cpu']}%。优先在 goroutine dump 中搜索十六进制线程 ID。",
                    "suggestion": "重点排查死循环、空 select default、无限重试、日志疯狂打印。",
                }
            )
        elif top["cpu"] >= 50:
            findings.append(
                {
                    "level": "warning",
                    "title": "存在高 CPU 线程",
                    "detail": f"TID {top['tid']} / 0x{top['tid_hex']} 当前 CPU {top['cpu']}%。",
                    "suggestion": "采集 goroutine dump，并用线程十六进制 ID 对齐具体栈帧。",
                }
            )

    threads_count = process.get("threads_count")
    if threads_count and threads_count > 1000:
        findings.append(
            {
                "level": "critical" if threads_count > 5000 else "warning",
                "title": "线程数异常偏高",
                "detail": f"进程线程数 {threads_count}。",
                "suggestion": "检查 goroutine 泄漏、阻塞调用、cgo 或线程锁定场景。",
            }
        )

    rss = memory.get("rss")
    if rss and rss > 2048:
        findings.append(
            {
                "level": "warning",
                "title": "进程 RSS 较高",
                "detail": f"当前物理内存占用约 {rss} MB。",
                "suggestion": "结合 pmap、goroutine 数量、队列堆积和 map/slice 增长排查内存上涨。",
            }
        )

    states = network.get("states", {})
    close_wait = states.get("CLOSE-WAIT", 0)
    syn_sent = states.get("SYN-SENT", 0)
    time_wait = states.get("TIME-WAIT", 0)
    if close_wait > 20:
        findings.append(
            {
                "level": "critical",
                "title": "CLOSE-WAIT 连接过多",
                "detail": f"CLOSE-WAIT 数量 {close_wait}。",
                "suggestion": "优先检查 HTTP client 是否遗漏 resp.Body.Close()，或连接关闭逻辑是否失效。",
            }
        )
    if syn_sent > 20:
        findings.append(
            {
                "level": "warning",
                "title": "SYN-SENT 连接较多",
                "detail": f"SYN-SENT 数量 {syn_sent}。",
                "suggestion": "排查下游不可达、网络 ACL、防火墙或 DNS 异常。",
            }
        )
    if time_wait > 1000:
        findings.append(
            {
                "level": "warning",
                "title": "TIME-WAIT 数量很高",
                "detail": f"TIME-WAIT 数量 {time_wait}。",
                "suggestion": "检查短连接过多、连接池复用不足或客户端超时配置。",
            }
        )

    if goroutine.get("ok"):
        count = goroutine.get("goroutine_count", 0)
        if count > 10000:
            findings.append(
                {
                    "level": "critical",
                    "title": "goroutine 数量疑似泄漏",
                    "detail": f"dump 中 goroutine 数量 {count}。",
                    "suggestion": "重点看 chan send/receive、net/http、database/sql、锁等待等重复栈。",
                }
            )
        elif count > 500:
            findings.append(
                {
                    "level": "warning",
                    "title": "goroutine 数量偏高",
                    "detail": f"dump 中 goroutine 数量 {count}。",
                    "suggestion": "如果该实例平时没有这么多 goroutine，优先排查阻塞等待、请求堆积或泄漏。",
                }
            )
        hot_terms = goroutine.get("hot_terms", {})
        if hot_terms.get("chan receive", 0) > 100:
            findings.append(
                {
                    "level": "warning",
                    "title": "大量 goroutine 阻塞在 chan receive",
                    "detail": f"chan receive 状态出现 {hot_terms.get('chan receive')} 次。",
                    "suggestion": "通常是消费者等待生产者、channel 未关闭，或 goroutine 生命周期没有退出条件。",
                }
            )
        if hot_terms.get("chan send", 0) > 100:
            findings.append(
                {
                    "level": "warning",
                    "title": "大量 goroutine 阻塞在 chan send",
                    "detail": f"chan send 状态出现 {hot_terms.get('chan send')} 次。",
                    "suggestion": "通常是生产速度大于消费速度、消费者退出，或 channel buffer 被打满。",
                }
            )
        if hot_terms.get("database/sql", 0) > 50:
            findings.append(
                {
                    "level": "warning",
                    "title": "大量 goroutine 卡在 database/sql",
                    "detail": f"database/sql 出现 {hot_terms.get('database/sql')} 次。",
                    "suggestion": "检查数据库慢查询、连接池耗尽、下游数据库可用性。",
                }
            )
        if hot_terms.get("net/http", 0) > 50:
            findings.append(
                {
                    "level": "warning",
                    "title": "大量 goroutine 卡在 net/http",
                    "detail": f"net/http 出现 {hot_terms.get('net/http')} 次。",
                    "suggestion": "检查下游 HTTP 超时、连接池、Body 关闭和外部服务状态。",
                }
            )

    if not findings:
        findings.append(
            {
                "level": "info",
                "title": "未发现强异常信号",
                "detail": "当前采集结果没有触发高风险规则。",
                "suggestion": "如果问题仍在，建议补充 goroutine dump、业务日志、容器事件或 pprof。",
            }
        )
    return findings


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def bar(label: str, value: float, max_value: float, color: str = "#4f7cff") -> str:
    pct = 0 if max_value <= 0 else min(100, max(0, value / max_value * 100))
    return f"""
    <div class="bar-row">
      <div class="bar-label">{esc(label)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>
      <div class="bar-value">{esc(value)}</div>
    </div>
    """


def render_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return '<p class="muted">无数据</p>'
    head = "".join(f"<th>{esc(col)}</th>" for col in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{esc(row.get(col, ''))}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render_raw(title: str, result: dict[str, Any] | str) -> str:
    if isinstance(result, dict):
        cmd = " ".join(result.get("cmd", []))
        content = result.get("stdout") or result.get("stderr") or ""
        label = f"{title}: {cmd}" if cmd else title
    else:
        label = title
        content = result
    return f"<details><summary>{esc(label)}</summary><pre>{esc(content[:30000])}</pre></details>"


def render_html(report: dict[str, Any]) -> str:
    process = report.get("process", {})
    threads = process.get("threads", {}).get("top", [])
    network = process.get("network", {})
    goroutine = report.get("goroutine", {})
    findings = report.get("findings", [])
    memory = process.get("memory_mb", {})

    max_cpu = max([row["cpu"] for row in threads] + [100])
    thread_bars = "\n".join(
        bar(f"TID {row['tid']} / 0x{row['tid_hex']}", row["cpu"], max_cpu, "#ef6c4f" if row["cpu"] >= 80 else "#4f7cff")
        for row in threads[:10]
    )
    net_bars = "\n".join(bar(state, count, max(network.get("states", {}).values() or [1]), "#30a46c") for state, count in network.get("states", {}).items())
    goroutine_bars = "\n".join(bar(state, count, max(goroutine.get("states", {}).values() or [1]), "#8b5cf6") for state, count in goroutine.get("states", {}).items())

    finding_cards = []
    for item in findings:
        finding_cards.append(
            f"""
            <div class="finding {esc(item['level'])}">
              <div class="finding-title">{esc(item['title'])}</div>
              <div>{esc(item['detail'])}</div>
              <div class="suggestion">{esc(item['suggestion'])}</div>
            </div>
            """
        )

    raw = report.get("system", {})
    raw_sections = [
        render_raw("uptime", raw.get("uptime", {})),
        render_raw("free -m", raw.get("free", {})),
        render_raw("df -h", raw.get("df", {})),
        render_raw("top", raw.get("top", {})),
        render_raw("ps cpu", raw.get("ps_cpu", {})),
        render_raw("ps mem", raw.get("ps_mem", {})),
        render_raw("vmstat", raw.get("vmstat", {})),
        render_raw("iostat", raw.get("iostat", {})),
        render_raw("process status", process.get("status_raw", "")),
        render_raw("pmap", process.get("pmap_tail", {})),
    ]
    if goroutine.get("ok"):
        raw_sections.append(render_raw("goroutine sample", goroutine.get("sample", "")))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Go 线上问题排查报告</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; color: #1f2937; background: #f6f8fb; }}
    header {{ padding: 32px 44px; background: #ffffff; border-bottom: 1px solid #e5e7eb; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0 0 16px; font-size: 20px; }}
    main {{ padding: 28px 44px 48px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 20px; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }}
    .metric {{ font-size: 28px; font-weight: 750; margin-top: 8px; }}
    .muted {{ color: #6b7280; }}
    .section {{ margin-top: 20px; }}
    .finding {{ border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; border: 1px solid #e5e7eb; background: #fff; }}
    .finding-title {{ font-weight: 750; margin-bottom: 6px; }}
    .finding.critical {{ border-color: #fca5a5; background: #fff1f2; }}
    .finding.warning {{ border-color: #fcd34d; background: #fffbeb; }}
    .finding.info {{ border-color: #93c5fd; background: #eff6ff; }}
    .suggestion {{ margin-top: 6px; color: #374151; }}
    .bar-row {{ display: grid; grid-template-columns: 190px 1fr 70px; gap: 10px; align-items: center; margin: 9px 0; }}
    .bar-label {{ font-size: 13px; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{ height: 12px; background: #edf1f7; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 999px; }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; color: #4b5563; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
    th {{ color: #4b5563; background: #f9fafb; }}
    details {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }}
    summary {{ cursor: pointer; font-weight: 650; }}
    pre {{ white-space: pre-wrap; overflow: auto; max-height: 420px; color: #111827; }}
    @media (max-width: 1000px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 640px) {{ main, header {{ padding-left: 18px; padding-right: 18px; }} .grid {{ grid-template-columns: 1fr; }} .bar-row {{ grid-template-columns: 1fr; }} .bar-value {{ text-align: left; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Go 线上问题排查报告</h1>
    <div class="muted">生成时间：{esc(report['system']['time'])} · 主机：{esc(report['system']['hostname'])} · PID：{esc(process.get('pid', '未指定'))}</div>
  </header>
  <main>
    <div class="grid">
      <div class="card"><div class="muted">RSS 内存</div><div class="metric">{esc(memory.get('rss', '-'))} MB</div></div>
      <div class="card"><div class="muted">线程数</div><div class="metric">{esc(process.get('threads_count', '-'))}</div></div>
      <div class="card"><div class="muted">连接数</div><div class="metric">{esc(network.get('total', 0))}</div></div>
      <div class="card"><div class="muted">goroutine</div><div class="metric">{esc(goroutine.get('goroutine_count', '未提供'))}</div></div>
    </div>

    <section class="card section">
      <h2>最可能的问题点</h2>
      {''.join(finding_cards)}
    </section>

    <section class="grid section">
      <div class="card" style="grid-column: span 2;">
        <h2>线程 CPU Top</h2>
        {thread_bars or '<p class="muted">未采集到线程数据</p>'}
      </div>
      <div class="card" style="grid-column: span 2;">
        <h2>网络连接状态</h2>
        {net_bars or '<p class="muted">未采集到连接数据</p>'}
      </div>
    </section>

    <section class="card section">
      <h2>线程明细</h2>
      {render_table(threads[:20], ['tid', 'tid_hex', 'cpu', 'mem', 'stat', 'comm'])}
    </section>

    <section class="card section">
      <h2>goroutine 状态</h2>
      {goroutine_bars or '<p class="muted">未提供 goroutine dump。可用 --send-quit 触发后，从日志中取 dump 再用 --goroutine-log 分析。</p>'}
    </section>

    <section class="card section">
      <h2>重复栈帧 Top</h2>
      {render_table([{'frame': k, 'count': v} for k, v in goroutine.get('top_frames', {}).items()], ['frame', 'count'])}
    </section>

    <section class="section">
      <h2>原始现场</h2>
      {''.join(raw_sections)}
    </section>
  </main>
</body>
</html>"""


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(report), encoding="utf-8")
    json_path = output.with_suffix(".json")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a visual incident report for a Go service.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--pid", type=int, help="Go service PID.")
    target.add_argument("--process-name", help="Find PID by process name or command substring.")
    parser.add_argument("--goroutine-log", help="Path to goroutine dump log produced by kill -QUIT / kill -3.")
    parser.add_argument("--send-quit", action="store_true", help="Send SIGQUIT to the PID before collecting. This prints goroutine stacks to service logs.")
    parser.add_argument("--output", default="go_incident_report.html", help="Output HTML path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pid = args.pid or find_pid_by_name(args.process_name or "")

    quit_result = maybe_send_quit(pid, args.send_quit)
    if args.send_quit:
        time.sleep(1)

    report = {
        "system": collect_system(),
        "process": collect_process(pid),
        "goroutine": analyze_goroutine_dump(args.goroutine_log),
        "sigquit": quit_result,
    }
    report["findings"] = score_findings(report)

    output = Path(args.output).resolve()
    write_report(report, output)

    print(f"HTML report: {output}")
    print(f"JSON data:   {output.with_suffix('.json')}")
    for item in report["findings"]:
        print(f"[{item['level']}] {item['title']} - {item['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
