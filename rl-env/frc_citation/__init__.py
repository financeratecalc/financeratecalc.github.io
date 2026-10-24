# The taskset needs the `verifiers` package; the offline receipt verifier (verify_offline) does not.
# Keep the package importable without verifiers so site build and CI scripts can use the verifier alone.
try:
    from frc_citation.taskset import FrcCitationTaskset  # noqa: F401
    __all__ = ["FrcCitationTaskset"]
except ImportError:  # verifiers not installed: verify_offline, rewards and temporal remain importable
    __all__ = []
