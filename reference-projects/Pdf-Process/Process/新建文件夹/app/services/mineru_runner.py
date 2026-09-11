import json, shutil, subprocess, sys
from pathlib import Path
from ..config import settings

def run_mineru(pdf: Path, out: Path, parse_method: str|None=None):
    out.mkdir(parents=True, exist_ok=True)
    executable = settings.mineru_command
    if not Path(executable).exists():
        executable = shutil.which(executable) or str(Path(sys.executable).with_name('mineru.exe'))
    # hybrid-engine is the default in MinerU 3.4, but it is needlessly
    # demanding for a local CPU/AMD desktop. The pipeline backend still keeps
    # formulas and tables enabled and has a much smaller dependency surface.
    cmd=[executable, '-p', str(pdf), '-o', str(out), '-m', parse_method or settings.mineru_parse_method, '-b', 'pipeline', '-f', 'true', '-t', 'true', '-l', 'en']
    try:
        p=subprocess.run(cmd, capture_output=True, text=True, timeout=settings.mineru_timeout_seconds)
        (out/'mineru.log').write_text((p.stdout or '')+'\n'+(p.stderr or ''), encoding='utf-8')
        if p.returncode!=0: raise RuntimeError((p.stderr or p.stdout or 'MinerU failed')[-4000:])
    except FileNotFoundError:
        raise RuntimeError('MinerU command not found. Install mineru[all]==3.4.4 or set MINERU_COMMAND.')
    return out

def find_middle_json(out: Path):
    return next(iter(out.rglob('*_middle.json')), None)
