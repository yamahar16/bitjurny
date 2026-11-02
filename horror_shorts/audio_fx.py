"""BGM 드론과 효과음을 ffmpeg로 합성 (저작권 걱정 없는 자체 사운드)."""
from __future__ import annotations

import subprocess
from pathlib import Path

SR = 44100

SFX_EXPR = {
    # 저음 쿵 + 잔향
    "hit": ("0.95*sin(2*PI*(42+70*exp(-t*9))*t)*exp(-t*2.8)+0.25*(random(0)*2-1)*exp(-t*14)", 3.0),
    # 점점 올라가는 긴장음
    "riser": ("0.35*(t/2.5)*sin(2*PI*(180+520*t/2.5)*t)+0.18*(t/2.5)*(random(0)*2-1)", 2.5),
    # 심장 박동 3번
    "heartbeat": ("0.9*sin(2*PI*55*t)*(exp(-mod(t,0.95)*22)+0.7*exp(-abs(mod(t,0.95)-0.22)*28))", 2.85),
    # 지직 노이즈
    "static_burst": ("0.45*(random(0)*2-1)*(1-t/0.7)", 0.7),
    # 딩동 안내음
    "chime": ("0.45*(lt(t,0.6)*sin(2*PI*880*t)*exp(-t*4)+gte(t,0.6)*sin(2*PI*698*(t-0.6))*exp(-(t-0.6)*3.5))", 1.8),
}


def _run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def make_sfx(kind: str, out: Path) -> Path:
    expr, dur = SFX_EXPR[kind]
    if not out.exists():
        _run(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr}':s={SR}:d={dur}", "-af", "afade=t=out:st=%.2f:d=0.25" % (dur - 0.25), str(out)])
    return out


def make_drone(out: Path, seconds: float) -> Path:
    """저음 드론: 55Hz + 미세하게 어긋난 58Hz(맥놀이) + 저역 통과 브라운 노이즈 + 아주 느린 고음 휘파람."""
    d = seconds + 1
    expr = ("0.30*sin(2*PI*55*t)+0.22*sin(2*PI*58.3*t)+0.10*sin(2*PI*110.5*t)*(0.5+0.5*sin(2*PI*0.07*t))"
            "+0.03*sin(2*PI*1244*t)*(0.5+0.5*sin(2*PI*0.031*t))")
    _run([
        "-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr}':s={SR}:d={d}",
        "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.35:sample_rate={SR}:d={d}",
        "-filter_complex",
        "[1]lowpass=f=260,aformat=channel_layouts=stereo[n];[0][n]amix=inputs=2:normalize=0,"
        f"afade=t=in:d=1.5,afade=t=out:st={max(0.0, d - 2):.2f}:d=2[a]",
        "-map", "[a]", str(out),
    ])
    return out
