import json
import shutil
import subprocess
import uuid
from pathlib import Path

IMAGE = 'smart-pipeline-python:local'


def save_generated_script(run_root, code):
    path = Path(run_root) / 'generated_pipeline.py'
    if len(code.encode()) > 100_000:
        raise ValueError('Generated code exceeds 100 KB')
    path.write_text(code, encoding='utf-8')
    return str(path)


def execute_script(run_root):
    root = Path(run_root).resolve()
    if not shutil.which('docker'):
        return {'exit_code': -1, 'error': 'Docker is required; execution refused without isolation.'}
    name = 'sales-' + uuid.uuid4().hex
    cmd = ['docker', 'run', '--rm', '--name', name, '--network=none', '--read-only',
           '--memory=256m', '--cpus=1', '--pids-limit=32', '--cap-drop=ALL',
           '--security-opt=no-new-privileges', '--user=65534:65534',
           '--ulimit', 'fsize=16777216:16777216', '--log-driver=none',
           '--mount', f'type=bind,src={root / "inputs"},dst=/inputs,readonly',
           '--mount', f'type=bind,src={root / "generated_pipeline.py"},dst=/pipeline.py,readonly',
           '--mount', f'type=bind,src={root / "plan.json"},dst=/plan.json,readonly',
           '--tmpfs', '/outputs:rw,size=32m,mode=1777',
           '--mount', f'type=bind,src={root / "outputs"},dst=/export', IMAGE,
           'sh', '-c', 'python -I -B /pipeline.py /inputs /outputs /plan.json > /outputs/execution.log 2>&1; rc=$?; cp /outputs/*.csv /outputs/execution.log /export/ 2>/dev/null; exit $rc']
    try:
        result = subprocess.run(cmd, timeout=60, capture_output=True)
        return {'exit_code': result.returncode, 'error': result.stderr.decode(errors='replace')[:8000]}
    except subprocess.TimeoutExpired:
        return {'exit_code': -1, 'error': 'Execution timed out'}
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)
