"""Run the beginner lesson with the current Python interpreter."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    # Pipeline: raw observations -> prepared features -> Feast -> models.
    for script in ["get_data.py", "transform_features.py"]:
        subprocess.run([sys.executable, str(ROOT / script)], check=True)
        
    # This calls the same CLI as `feast apply`, using the active interpreter.
    subprocess.run(
        [sys.executable, "-c", "from feast.cli.cli import cli; cli()", "apply"],
        cwd=ROOT / "feature_repo", check=True,
    )
    
    for script in ["train_models.py", "materialize.py", "predict.py"]:
        subprocess.run([sys.executable, str(ROOT / script)], check=True)


if __name__ == "__main__":
    main()
