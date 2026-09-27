# exceptions.py
"""Control-flow exceptions used across pipeline stages."""


class TenderCheckStopped(Exception):
    """
    Raised by stage_check_index_and_tender when the document fails the
    tender keyword check. Caught specially by run_pipeline - marks the job
    NOT_A_TENDER instead of FAILED and stops the pipeline early, rather than
    being treated as a stage failure.
    """
