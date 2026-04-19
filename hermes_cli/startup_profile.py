"""
Hermes Startup Profiler — 轻量启动阶段计时器
通过 HERMES_PROFILE=1 环境变量开启

用法:
  HERMES_PROFILE=1 hermes version
  HERMES_PROFILE=1 hermes status
"""

import os
import time

# 全局开关
_ENABLED = os.getenv("HERMES_PROFILE") == "1"

# checkpoints: {name: (start_time, end_time)}
_checkpoints = {}
_current = None
_start_time = None


def checkpoint(name: str) -> None:
    """
    记录一个阶段的结束和新阶段的开始。
    第一次调用标记"阶段1开始"，之后每次调用结束上一个阶段。
    """
    global _current, _start_time

    now = time.perf_counter()
    now_ms = now * 1000

    if _current is None:
        # 第一次调用：这是起点
        _start_time = now
        _current = name
        _checkpoints[name] = {"start_ms": 0, "end_ms": None, "duration_ms": None}
        return

    # 结束上一个阶段
    if _current in _checkpoints:
        _checkpoints[_current]["end_ms"] = now_ms
        _checkpoints[_current]["duration_ms"] = now_ms - _checkpoints[_current]["start_ms"]

    # 开始新阶段
    _current = name
    _checkpoints[name] = {"start_ms": now_ms, "end_ms": None, "duration_ms": None}


def get_report() -> dict:
    """获取格式化报告"""
    if not _checkpoints:
        return {}

    # 计算总时长
    all_ends = [v["end_ms"] for v in _checkpoints.values() if v["end_ms"] is not None]
    total_ms = max(all_ends) - _checkpoints[list(_checkpoints.keys())[0]]["start_ms"]

    report = {
        "total_ms": round(total_ms, 1),
        "phases": [],
    }

    first_start = _checkpoints[list(_checkpoints.keys())[0]]["start_ms"]
    for name, data in _checkpoints.items():
        if data["duration_ms"] is not None:
            pct = (data["duration_ms"] / total_ms * 100) if total_ms > 0 else 0
            report["phases"].append({
                "name": name,
                "duration_ms": round(data["duration_ms"], 1),
                "pct": round(pct, 1),
                "start_ms": round(data["start_ms"] - first_start, 1),
            })

    return report


def print_report() -> None:
    """打印报告到 stderr"""
    report = get_report()
    if not report:
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
            f"  {phase['name']:<30} {phase['duration_ms']:>8.1f}ms  {phase['pct']:>5.1f}%  {bar}"
        )

    lines.append("=" * 50)
    lines.append("")

    import sys
    sys.stderr.write("\n".join(lines))


def profile(name: str):
    """装饰器模式：@profile("阶段名")"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            checkpoint(name)
            if _ENABLED:
                import sys
                sys.stderr.write(f"[PROFILE] > {name}\n")
            result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator
