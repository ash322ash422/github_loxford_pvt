from typing import TypedDict


class RunState(TypedDict, total=False):
    run_id: str
    user_request: str
    input_root: str
    run_root: str
    file_inventory: list[dict]
    csv_profiles: list[dict]
    processing_plan: dict
    generated_script_path: str
    execution_attempts: int
    execution_result: dict
    validation_result: dict
    output_paths: list[str]
    archive_manifest: list[dict]
    errors: list[str]
    status: str
