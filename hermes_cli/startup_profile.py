"""
Hermes Startup Profiler — 轻量启动阶段计时器
通过 HERMES_PROFILE=1 环境变量开启

用法:
  HERMES_PROFILE=1 hermes version
"""

import os
import time as _time

_ENABLED = os.getenv("HERMES_PROFILE") == "1"

# (name, start_time, end_time)
_phases = []
_current = None
_start_time = None


def checkpoint(name: str) -> None:
    """
    记录一个阶段的结束和新阶段的开始。
    第一次调用标记起点，后续每次调用结束上一个阶段并开始新阶段。
    只报告有明确起止的阶段。
    """
    global _current, _start_time

    now = _time.perf_counter()

    if _current is None:
        # 第一次调用：仅记录起点，不计入任何阶段
        _current = name
        _start_time = now
        return

    # 结束上一个阶段
    _phases.append((_current, now))
    _current = name


def get_report() -> dict:
    """获取格式化报告"""
    if not _phases:
        return {}

    # 计算总时长（从第一个阶段开始到最后一个阶段结束）
    total_ms = (_phases[-1][1] - _phases[0][1]) * 1000

    report_phases = []
    for name, end_time in _phases:
        # 找到这个阶段的开始时间（上一个阶段的结束，或第一个阶段对应的时间戳）
        start_time = end_time
        # 找到这个阶段的开始：previous end 或第一个阶段的开始
        for i in range(len(_phases) - 1, -1, -1):
            if _phases[i][1] == end_time and i > 0:
                start_time = _phases[i - 1][1]
                break

        # 跳过第一个阶段（没有有效的开始-结束对）
        if start_time == end_time:
            continue

        duration_ms = (end_time - start_time) * 1000
        pct = (duration_ms / total_ms * 100) if total_ms > 0 else 0
        report_phases.append({
            "name": name,
            "duration_ms": round(duration_ms, 1),
            "pct": round(pct, 1),
        })

    return {
        "total_ms": round(total_ms, 1),
        "phases": report_phases,
    }


def print_report() -> None:
    """打印报告到 stderr"""
    import sys

    if not _ENABLED:
        return

    report = get_report()
    if not report or not report["phases"]:
        return

    total = report["total_ms"]
    lines = [
        "",
        "=== Hermes Startup Profile ===",
        f"Total: {total:.1f}ms",
        "",
    ]

    for phase in report["phases"]:
        bar = "█" * int(phase["pct"] / 5)
        lines.append(
            f"  {phase['name']:<28} {phase['duration_ms']:>8.1f}ms  {phase['pct']:>5.1f}%  {bar}"
        )

    lines.append("=" * 50)
    lines.append("")

    sys.stderr.write("\n".join(lines))
