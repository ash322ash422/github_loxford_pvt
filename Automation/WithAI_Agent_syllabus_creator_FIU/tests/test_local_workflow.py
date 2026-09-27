import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from main import build_demo_package, save_draft
from src.config import settings
from src.lms import LocalLMSClient


def test_demo_package_contains_all_requested_outputs(tmp_path):
    package = build_demo_package("Prepare next week's DBMS class.")
    data = package.to_dict()
    assert data["next_topic"]
    assert data["lecture_outline"]
    assert data["examples_and_exercises"]
    assert data["quiz"]
    assert data["announcement"]
    assert data["lms_metadata"]


def test_lms_publish_writes_only_when_called(tmp_path):
    package = build_demo_package("Prepare next week's DBMS class.")
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(package.to_dict()), encoding="utf-8")
    assert not (tmp_path / "lms" / "CS301_next_class.json").exists()
    published = LocalLMSClient(tmp_path / "lms").publish(package.to_dict())
    assert published.exists()
