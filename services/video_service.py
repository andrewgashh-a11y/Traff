import os
import random
import subprocess
import tempfile


def process_video(input_path, output_path):
    """
    Apply FFmpeg uniqualization:
    - Random start offset 0-3s
    - Trim to 15s
    - Random zoom 102-105%
    - Random speed 1.0 or 1.05x
    - Brightness +2%, contrast +3%
    - Output: 1080x1920 vertical, libx264, AAC
    """
    start_offset = round(random.uniform(0, 3), 2)
    zoom = round(random.uniform(1.02, 1.05), 4)
    speed = random.choice([1.0, 1.05])
    duration = 15

    # Build scale+crop filter for vertical 1080x1920 with zoom
    # Zoom by scaling up then cropping to target
    scale_w = int(1080 * zoom)
    scale_h = int(1920 * zoom)

    vf_parts = [
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase",
        f"crop=1080:1920",
        f"eq=brightness=0.02:contrast=1.03",
    ]

    af_parts = []

    if speed != 1.0:
        vf_parts.append(f"setpts={round(1/speed, 6)}*PTS")
        af_parts.append(f"atempo={speed}")

    vf = ','.join(vf_parts)
    af = ','.join(af_parts) if af_parts else 'anull'

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_offset),
        '-i', input_path,
        '-t', str(duration),
        '-vf', vf,
        '-af', af,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")

    return output_path
