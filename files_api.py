import os
import json
import time
from typing import Any, Dict, List, Optional


_DOTENV_LOADED = False


def _load_env_from_dotenv_once() -> None:
    """Load env vars from a local `.env` if present (no external deps).

    Does not override existing environment variables.
    Supported format: KEY=VALUE, ignores lines starting with '#'.
    Quotes around VALUE (single/double) are stripped.
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    candidates = [
        os.environ.get("ENV_FILE"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    for path in candidates:
        if not path:
            continue
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if (val.startswith('"') and val.endswith('"')) or (
                        val.startswith("'") and val.endswith("'")
                    ):
                        val = val[1:-1]
                    if key and key not in os.environ:
                        os.environ[key] = val
            # Stop after first readable .env
            break
        except Exception:
            # Silently ignore parse errors; env can still be provided via OS
            pass


def _get_api_key(explicit: Optional[str] = None) -> str:
    """Resolve the API key from param or env.

    Checks, in order: explicit param, GOOGLE_API_KEY, GEMINI_API_KEY.
    """
    _load_env_from_dotenv_once()
    api_key = explicit or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set `GOOGLE_API_KEY` (or pass api_key) to use the Files API."
        )
    return api_key


def _get_client(api_key: Optional[str] = None):
    """Create and return a genai.Client instance."""
    try:
        # The official client lives under `google.genai` (package: google-genai)
        from google import genai  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "The `google-genai` package is required. Install with: pip install google-genai"
        ) from e

    key = _get_api_key(api_key)
    return genai.Client(api_key=key)


def get_client(api_key: Optional[str] = None):
    """Public helper to obtain a configured genai.Client."""
    return _get_client(api_key)


def _file_to_metadata_dict(f: Any) -> Dict[str, Any]:
    """Convert a Files API object to a basic dict of metadata fields."""
    # Guarded getattr to be resilient to SDK version differences
    fields = [
        "name",
        "display_name",
        "mime_type",
        "size_bytes",
        "create_time",
        "update_time",
        "sha256_hash",
        "uri",
        "state",
    ]
    data: Dict[str, Any] = {}
    for k in fields:
        data[k] = getattr(f, k, None)
    return data


def upload_file(
    file_path: str,
    *,
    display_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a local file to Gemini Files API and return its metadata dict.

    Raises RuntimeError on failure.
    """
    if not os.path.isfile(file_path):
        raise RuntimeError(f"File not found: {file_path}")

    client = _get_client(api_key)
    try:
        if display_name:
            try:
                # Prefer newer SDKs that support display_name
                uploaded = client.files.upload(file=file_path, display_name=display_name)
            except TypeError:
                # Back-compat: older SDKs don't accept display_name
                uploaded = client.files.upload(file=file_path)
        else:
            uploaded = client.files.upload(file=file_path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Files API upload failed: {e}") from e
    return _file_to_metadata_dict(uploaded)


def get_file_metadata(name: str, *, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Fetch metadata by Files API resource name."""
    if not name:
        raise RuntimeError("`name` must be a non-empty Files resource name.")
    client = _get_client(api_key)
    try:
        f = client.files.get(name=name)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Files API get() failed: {e}") from e
    return _file_to_metadata_dict(f)


def list_files(*, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List metadata for all uploaded files."""
    client = _get_client(api_key)
    try:
        items = list(client.files.list())
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Files API list() failed: {e}") from e
    return [_file_to_metadata_dict(f) for f in items]


def wait_until_active(
    name: str,
    *,
    timeout_s: int = 300,
    poll_s: float = 2.0,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Poll Files API until the file becomes ACTIVE or fails.

    Returns the final metadata dict. Raises RuntimeError on timeout/failure.
    """
    client = _get_client(api_key)
    deadline = time.time() + timeout_s
    last_state = None
    while True:
        try:
            f = client.files.get(name=name)
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Files API get() failed while waiting: {e}") from e
        meta = _file_to_metadata_dict(f)
        state = meta.get("state")
        if state != last_state:
            last_state = state
        if state == "ACTIVE":
            return meta
        if state in {"FAILED", "DELETING", "DELETED"}:
            raise RuntimeError(f"File transitioned to terminal state: {state}")
        if time.time() > deadline:
            raise RuntimeError(f"Timeout waiting for file to become ACTIVE (last state: {state})")
        time.sleep(poll_s)


def analyze_file_resource(
    name: str,
    *,
    prompt: str,
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    fps: Optional[float] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> str:
    """Run a Gemini video understanding request on an uploaded Files resource.

    Returns the response text (or string form if text missing).
    """
    client = _get_client(api_key)
    try:
        from google.genai import types  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "The `google-genai` package is required. Install with: pip install google-genai"
        ) from e

    # Always pass a file_data part by URI to avoid SDK schema mismatches
    meta = get_file_metadata(name, api_key=api_key)
    file_uri = meta.get("uri")
    if not file_uri:
        raise RuntimeError("Missing file URI in metadata; cannot create content part.")

    parts = []
    if fps is not None or start is not None or end is not None:
        vm_kwargs: Dict[str, Any] = {}
        if fps is not None:
            vm_kwargs["fps"] = fps
        if start is not None:
            vm_kwargs["start_offset"] = start
        if end is not None:
            vm_kwargs["end_offset"] = end
        parts.append(
            types.Part(
                file_data=types.FileData(file_uri=file_uri),
                video_metadata=types.VideoMetadata(**vm_kwargs),
            )
        )
    else:
        parts.append(types.Part(file_data=types.FileData(file_uri=file_uri)))

    parts.append(types.Part(text=prompt))

    resp = client.models.generate_content(
        model=model,
        contents=types.Content(parts=parts),
    )
    text = getattr(resp, "text", None)
    return text if text else str(resp)


def metadata_pretty(metadata: Dict[str, Any]) -> str:
    """Pretty-print JSON metadata for CLI/logging."""
    return json.dumps(metadata, indent=2, ensure_ascii=False, default=str)
