"""One-command classroom demo. Run from any working directory."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    for script in ['generate_data.py', 'build_features.py']:
        subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)
    subprocess.run([sys.executable, '-c', 'from feast.cli.cli import cli; cli()', 'apply'], check=True, cwd=ROOT / 'feature_repo')
    for script in ['train_models.py', 'materialize.py', 'verify_demo.py']:
        subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)


if __name__ == '__main__':
    main()
