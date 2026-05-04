import os
import random
import requests
import vk_api
import yt_dlp as ytdl


def get_vk_session(token):
    vk_session = vk_api.VkApi(token=token)
    return vk_session.get_api()


def resolve_group_id(vk, url):
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
    owner_id = -abs(int(group_id))
    videos = []
    offset = 0
    batch = 200

    while len(videos) < max(count * 3, 50):
        result = vk.video.get(owner_id=owner_id, count=batch, offset=offset)
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
    Download with four strategies, returning on first success.
    Raises RuntimeError listing every failure if all strategies fail.
    """
    owner_id = video_item.get('owner_id', '')
    video_id  = video_item.get('id', '')
    errors = []

    # Strategy 1: re-fetch fresh CDN URLs from VK API right now so srcIp
    # matches this process's outgoing IP, then direct-download best quality
    if vk_token:
        try:
            fresh = _refetch_files(vk_token, owner_id, video_id)
            for q in ('mp4_720', 'mp4_480', 'mp4_360', 'mp4_240', 'mp4_1080'):
                url = fresh.get(q)
                if not url:
                    continue
                try:
                    _direct_download(url, dest_path)
                    return
                except Exception as e:
                    errors.append(f"fresh-{q}: {e}")
        except Exception as e:
            errors.append(f"re-fetch API: {e}")

    # Strategy 2: yt-dlp with vk.com/video page URL (VK extractor fetches
    # its own fresh CDN URLs bound to yt-dlp's outgoing IP)
    for page_url in (
        f"https://vk.com/video{owner_id}_{video_id}",
        f"https://vk.com/clip{owner_id}_{video_id}",
    ):
        try:
            _ytdlp_download(page_url, dest_path)
            return
        except Exception as e:
            errors.append(f"yt-dlp {page_url}: {e}")

    # Strategy 3: yt-dlp with HLS/DASH stream (no srcIp on manifest URLs)
    cached_files = video_item.get('files', {})
    stream_url = (cached_files.get('hls') or
                  cached_files.get('dash_uni') or
                  cached_files.get('dash_sep'))
    if stream_url:
        try:
            _ytdlp_download(stream_url, dest_path)
            return
        except Exception as e:
            errors.append(f"yt-dlp HLS/DASH: {e}")

    # Strategy 4: cached CDN URLs as last resort
    for q in ('mp4_720', 'mp4_480', 'mp4_360', 'mp4_240', 'mp4_1080'):
        url = cached_files.get(q)
        if not url:
            continue
        try:
            _direct_download(url, dest_path)
            return
        except Exception as e:
            errors.append(f"cached-{q}: {e}")

    raise RuntimeError("All strategies failed: " + " | ".join(errors))


def _refetch_files(vk_token, owner_id, video_id):
    """Call VK API right before download to get fresh srcIp-bound URLs."""
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    videos = vk.video.get(videos=f"{owner_id}_{video_id}", count=1)
    items = videos.get('items', [])
    if not items:
        raise RuntimeError("video not found in fresh API response")
    return items[0].get('files', {})


def _ytdlp_download(url, dest_path):
    """Download via yt-dlp Python library — no PATH dependency."""
    base = dest_path[:-4] if dest_path.lower().endswith('.mp4') else dest_path

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': base + '.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://vk.com/',
        },
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    out = base + '.mp4'
    if not os.path.exists(out):
        raise RuntimeError(f"output not found at {out}")
    if out != dest_path:
        os.rename(out, dest_path)


def _direct_download(url, dest_path):
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://vk.com/',
        'Origin':  'https://vk.com',
    }
    with requests.get(url, stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
