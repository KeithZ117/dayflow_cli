import argparse
import sys
from typing import Optional

from .files import (
    get_file_metadata,
    list_files,
    metadata_pretty,
    upload_file,
    get_client,
    wait_until_active,
)


def cmd_upload(args: argparse.Namespace) -> int:
    try:
        meta = upload_file(
            args.file,
            display_name=args.display_name,
            api_key=args.api_key,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(metadata_pretty(meta))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    try:
        meta = get_file_metadata(args.name, api_key=args.api_key)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(metadata_pretty(meta))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    try:
        items = list_files(api_key=args.api_key)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    for meta in items:
        print(metadata_pretty(meta))
    return 0


def _to_duration_str(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Already like '123s'
    if s.endswith("s") and s[:-1].replace(".", "", 1).isdigit():
        return s
    # Pure seconds number
    if s.replace(".", "", 1).isdigit():
        return f"{s}s"
    # Try MM:SS or HH:MM:SS
    parts = s.split(":")
    try:
        nums = [float(p) for p in parts]
    except Exception:
        return s  # Fallback: let API decide
    if len(nums) == 2:  # MM:SS
        total = nums[0] * 60 + nums[1]
    elif len(nums) == 3:  # HH:MM:SS
        total = nums[0] * 3600 + nums[1] * 60 + nums[2]
    else:
        return s
    return f"{total}s"


def cmd_analyze(args: argparse.Namespace) -> int:
    # Optionally wait until file is ACTIVE
    try:
        if args.wait:
            wait_until_active(args.name, api_key=args.api_key)
        meta = get_file_metadata(args.name, api_key=args.api_key)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        client = get_client(args.api_key)
        from google.genai import types  # Imported lazily to avoid dependency for other cmds

        # Build content parts depending on whether user specified clip/fps
        parts = []
        start = _to_duration_str(args.start)
        end = _to_duration_str(args.end)
        if args.fps is not None or start is not None or end is not None:
            # Use file URI for a Part with VideoMetadata
            file_uri = meta.get("uri")
            if not file_uri:
                raise RuntimeError("Missing file URI in metadata; cannot build video metadata part.")
            vm_kwargs = {}
            if args.fps is not None:
                vm_kwargs["fps"] = args.fps
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
            # Use file URI part without extra metadata to avoid schema issues
            file_uri = meta.get("uri")
            if not file_uri:
                raise RuntimeError("Missing file URI in metadata; cannot build content part.")
            parts.append(types.Part(file_data=types.FileData(file_uri=file_uri)))

        parts.append(types.Part(text=args.prompt))

        response = client.models.generate_content(
            model=args.model,
            contents=types.Content(parts=parts),
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Print the analysis text
    text = getattr(response, "text", None)
    if not text:
        # Fallback: print raw object if text missing
        print(str(response))
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Upload files to Gemini Files API and fetch metadata.",
    )
    p.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="Google API key (defaults to env GOOGLE_API_KEY or GEMINI_API_KEY).",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upload", help="Upload a local file and print metadata.")
    up.add_argument("--file", required=True, help="Path to local file (e.g., video.mp4)")
    up.add_argument("--display-name", default=None, help="Optional display name")
    up.set_defaults(func=cmd_upload)

    gt = sub.add_parser("get", help="Fetch metadata by file resource name.")
    gt.add_argument("--name", required=True, help="Files API resource name")
    gt.set_defaults(func=cmd_get)

    ls = sub.add_parser("list", help="List all uploaded files.")
    ls.set_defaults(func=cmd_list)

    an = sub.add_parser(
        "analyze",
        help="Analyze an uploaded video with Gemini and print a structured report.",
    )
    an.add_argument("--name", required=True, help="Files API resource name (e.g., files/abc123)")
    an.add_argument(
        "--prompt",
        default=(
            "请分析视频中我在做什么，按时间轴总结关键活动。"
            "右上角有我的webcam：评估是否专注（如是否注视屏幕、明显分心动作）。"
            "webcam下方显示现实时间：请识别关键片段的时间戳并在报告中标注，时间格式统一为MM:SS。"
            "输出结构：\n1) 总览\n2) 关键事件（含时间戳）\n3) 专注度评估\n4) 其他观察\n5) 总结与建议。"
        ),
        help="Custom analysis prompt (default is Chinese structured analysis).",
    )
    an.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    an.add_argument("--fps", type=float, default=None, help="Custom FPS for analysis")
    an.add_argument(
        "--start",
        default=None,
        help="Clip start offset (seconds, MM:SS, or HH:MM:SS).",
    )
    an.add_argument(
        "--end",
        default=None,
        help="Clip end offset (seconds, MM:SS, or HH:MM:SS).",
    )
    an.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the file to become ACTIVE before analysis.",
    )
    an.set_defaults(func=cmd_analyze)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
