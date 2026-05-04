import os
import random
import subprocess


def process_video(input_path, output_path):
    """
    FFmpeg uniqualization pipeline:
    - Random start offset 0-3s (accurate seek, after -i)
    - Trim to 15s
    - Random zoom 102-105%: scale to cover 1080x1920 * zoom, then center-crop
    - Random speed 1.0 or 1.05x
    - Brightness +2%, contrast +3%
    - Output: 1080x1920 vertical, libx264, AAC
    """
    if not os.path.exists(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    start_offset = round(random.uniform(0, 3), 2)
    zoom         = round(random.uniform(1.02, 1.05), 4)
    speed        = random.choice([1.0, 1.05])

    # Scale to cover 1080x1920 + zoom margin maintaining AR, then crop
    scale_w = int(1080 * zoom)
    scale_h = int(1920 * zoom)

    vf_parts = [
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase:flags=lanczos",
        "crop=1080:1920",
        "eq=brightness=0.02:contrast=1.03",
    ]
    af_parts = []

    if speed != 1.0:
        vf_parts.append(f"setpts={round(1/speed, 6)}*PTS")
        af_parts.append(f"atempo={speed}")

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,           # input first
        '-ss', str(start_offset),   # accurate seek AFTER input (frame-level)
        '-t', str(15),
        '-vf', ','.join(vf_parts),
        '-af', ','.join(af_parts) if af_parts else 'anull',
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
        # Capture head + tail so the actual error isn't truncated
        stderr = result.stderr
        detail = stderr[:1000] + ('\n...\n' + stderr[-1000:] if len(stderr) > 1000 else '')
        raise RuntimeError(f"FFmpeg error:\n{detail}")

    return output_path
