import glob
import os
import random
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
    """Download VK video via yt-dlp using the VK page URL.

    yt-dlp's VK extractor handles both vk.com-native and okcdn.ru-hosted
    (OK.ru CDN) videos automatically, fetching fresh URLs bound to its own
    outgoing IP so srcIp restrictions are not a problem.
    """
    owner_id = video_item.get('owner_id', '')
    video_id = video_item.get('id', '')
    page_url = f"https://vk.com/video{owner_id}_{video_id}"

    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 30,
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(page_url, download=True)
        downloaded = ydl.prepare_filename(info)

    # yt-dlp may produce a different extension than .mp4
    if not os.path.exists(downloaded):
        # search for any file yt-dlp wrote for this video id
        matches = glob.glob(f"/tmp/{info['id']}.*")
        if not matches:
            raise RuntimeError(f"yt-dlp finished but no output file found for id {info['id']}")
        downloaded = matches[0]

    os.replace(downloaded, dest_path)
