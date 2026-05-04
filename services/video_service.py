import os
import random
import subprocess


def process_video(input_path, output_path):
    """
    FFmpeg uniqualization pipeline → 1080x1920 vertical, libx264, AAC.
    - Random start offset 0-3s (accurate seek, -ss after -i)
    - Trim to 15s
    - Random zoom 102-105%
    - Random speed 1.0 or 1.05x
    - Brightness +2%, contrast +3%
    """
    if not os.path.exists(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    start_offset = round(random.uniform(0, 3), 2)
    zoom         = round(random.uniform(1.02, 1.05), 4)
    speed        = random.choice([1.0, 1.05])

    scale_w = int(1080 * zoom)
    scale_h = int(1920 * zoom)
    # libx264 requires even dimensions
    if scale_w % 2:
        scale_w += 1
    if scale_h % 2:
        scale_h += 1

    vf_parts = [
        # Normalise to 8-bit yuv420p first; eq/scale silently fail on 10-bit HDR input
        "format=yuv420p",
        # Normalise SAR so scale calculates correctly for anamorphic clips
        "setsar=1",
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
        '-i', input_path,
        '-ss', str(start_offset),   # accurate seek after input
        '-t', '15',
        '-vf', ','.join(vf_parts),
        '-af', ','.join(af_parts) if af_parts else 'anull',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        # Extract the actual error lines (not just the tail) so they show
        # in one log line without newlines truncating the display
        lines = [l.strip() for l in result.stderr.splitlines() if l.strip()]
        err_lines = [l for l in lines
                     if any(k in l.lower() for k in
                            ('error', 'invalid', 'failed', 'cannot', 'unable', 'no such'))]
        detail = ' | '.join(err_lines[:4]) if err_lines else ' | '.join(lines[-5:])
        raise RuntimeError(f"FFmpeg: {detail}")

    return output_path
