import random
import subprocess
import requests
import vk_api


def get_vk_session(token):
    vk_session = vk_api.VkApi(token=token)
    return vk_session.get_api()


def resolve_group_id(vk, url):
    """Extract screen_name from URL and resolve to group info."""
    screen_name = url.rstrip('/').split('/')[-1]
    if screen_name.startswith('club') or screen_name.startswith('public'):
        group_id = screen_name[4:] if screen_name.startswith('club') else screen_name[6:]
        result = vk.groups.getById(group_id=group_id, fields='photo_200')
    else:
        resolved = vk.utils.resolveScreenName(screen_name=screen_name)
        if not resolved or resolved.get('type') not in ('group', 'page', 'event'):
            raise ValueError(f"Cannot resolve '{screen_name}' as a VK group")
        group_id = resolved['object_id']
        result = vk.groups.getById(group_id=group_id, fields='photo_200')

    group = result[0]
    return {
        'id': group['id'],
        'name': group['name'],
        'avatar_url': group.get('photo_200', ''),
    }


def fetch_videos(vk, group_id, count, filter_type):
    """Fetch videos from a VK group."""
    owner_id = -abs(int(group_id))

    videos = []
    offset = 0
    batch = 200

    while len(videos) < max(count * 3, 50):
        result = vk.video.get(
            owner_id=owner_id,
            count=batch,
            offset=offset,
        )
        items = result.get('items', [])
        if not items:
            break
        videos.extend(items)
        offset += batch
        if offset >= result.get('count', 0):
            break

    if filter_type == 'new':
        videos.sort(key=lambda v: v.get('date', 0), reverse=True)
    elif filter_type == 'popular':
        videos.sort(key=lambda v: v.get('views', 0), reverse=True)
    elif filter_type == 'random':
        random.shuffle(videos)

    return videos[:count]


def download_video(video_item, dest_path, vk_token=None):
    """
    Download video using multiple strategies in order:
    1. yt-dlp with VK page URL (handles CDN IP restrictions automatically)
    2. HLS/DASH stream from files dict via yt-dlp (no srcIp restriction)
    3. Direct mp4 CDN URL with VK Referer header (last resort)
    """
    owner_id = video_item.get('owner_id', '')
    video_id = video_item.get('id', '')
    files = video_item.get('files', {})
    errors = []

    # Strategy 1: yt-dlp with VK page URL
    page_url = f"https://vk.com/video{owner_id}_{video_id}"
    try:
        _ytdlp_download(page_url, dest_path)
        return
    except Exception as e:
        errors.append(f"yt-dlp page: {e}")

    # Strategy 2: HLS/DASH stream (no srcIp restriction on streaming URLs)
    stream_url = files.get('hls') or files.get('dash_uni') or files.get('dash_sep')
    if stream_url:
        try:
            _ytdlp_download(stream_url, dest_path)
            return
        except Exception as e:
            errors.append(f"yt-dlp hls/dash: {e}")

    # Strategy 3: Direct mp4 CDN with Referer (may still fail on IP mismatch)
    for quality in ('mp4_720', 'mp4_480', 'mp4_360', 'mp4_240', 'mp4_1080'):
        cdn_url = files.get(quality)
        if not cdn_url:
            continue
        try:
            _direct_download(cdn_url, dest_path)
            return
        except Exception as e:
            errors.append(f"direct {quality}: {e}")

    raise RuntimeError("All download strategies failed:\n" + "\n".join(errors))


def _ytdlp_download(url, dest_path):
    cmd = [
        'yt-dlp',
        '--no-check-certificates',
        '--quiet',
        '--no-warnings',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '--no-playlist',
        '-o', dest_path,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-400:]
        raise RuntimeError(detail)


def _direct_download(url, dest_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://vk.com/',
        'Origin': 'https://vk.com',
    }
    with requests.get(url, stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
