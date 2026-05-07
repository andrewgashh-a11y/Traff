import os
import random
import subprocess


def process_video(input_path, output_path):
    """
    FFmpeg uniqualization pipeline → 1080x1920 vertical, libx264, AAC.
    - Trim to 15s from start (no random seek — avoids frame=0 on short/fragmented clips)
    - Random zoom 102-105%
    - Random speed 1.0 or 1.05x
    - Brightness +2%, contrast +3%
    """
    if not os.path.exists(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    zoom  = round(random.uniform(1.02, 1.05), 4)
    speed = random.choice([1.0, 1.05])

    scale_w = int(1080 * zoom)
    scale_h = int(1920 * zoom)
    if scale_w % 2:
        scale_w += 1
    if scale_h % 2:
        scale_h += 1

    vf_parts = [
        "format=yuv420p",   # convert HDR/10-bit to 8-bit before other filters
        "setsar=1",         # normalise anamorphic SAR
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
        lines = [l.strip() for l in result.stderr.splitlines() if l.strip()]

        # Drop the standard FFmpeg header (version, build config, lib versions)
        # so we don't waste our char budget on noise
        header_prefixes = (
            'ffmpeg version', 'built with', 'configuration:',
            'libavutil', 'libavcodec', 'libavformat', 'libavdevice',
            'libavfilter', 'libswscale', 'libswresample', 'libpostproc',
        )
        body = [l for l in lines if not any(l.startswith(p) for p in header_prefixes)]

        # Prefer lines that look like actual errors
        err_kw = ('error', 'invalid', 'failed', 'cannot', 'finishing stream',
                  'output file is empty', 'nothing was encoded',
                  'conversion failed', 'no such', 'could not', 'unable')
        errs = [l for l in body if any(k in l.lower() for k in err_kw)]

        detail = ' | '.join(errs[:6]) if errs else ' | '.join(body[-15:])
        raise RuntimeError(detail[:2000])

    return output_path
