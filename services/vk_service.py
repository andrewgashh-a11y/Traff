import random
import re
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


def get_video_download_url(video_item):
    """Extract best available direct download URL from video item."""
    files = video_item.get('files', {})
    for quality in ('mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360', 'mp4_240'):
        url = files.get(quality)
        if url:
            return url

    # Try player URL as fallback indicator (actual download not possible without files)
    return None


def download_video(url, dest_path):
    """Download video from direct URL to dest_path."""
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
