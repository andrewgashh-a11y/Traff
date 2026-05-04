import os
import json
import time
import threading
import tempfile
from datetime import datetime, date

from flask import Flask, jsonify, request, render_template, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy

from config import Config
from database.models import db, Group, Job, Video, LogEntry, DailyStat, Setting

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['DATA_DIR'], exist_ok=True)
os.makedirs(app.config['TMP_DIR'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_setting(key, default=''):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s and s.value else default


def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = Setting(key=key, value=value)
        db.session.add(s)
    db.session.commit()


def add_log(job_id, level, message):
    with app.app_context():
        entry = LogEntry(job_id=job_id, level=level, message=message)
        db.session.add(entry)
        db.session.commit()


def bump_daily_stat(field):
    with app.app_context():
        today = date.today()
        stat = DailyStat.query.filter_by(date=today).first()
        if not stat:
            stat = DailyStat(date=today)
            db.session.add(stat)
        setattr(stat, field, getattr(stat, field) + 1)
        db.session.commit()


# ---------------------------------------------------------------------------
# Background job runner
# ---------------------------------------------------------------------------

def run_job(job_id):
    with app.app_context():
        job = Job.query.get(job_id)
        if not job:
            return

        job.status = 'processing'
        db.session.commit()

        add_log(job_id, 'info', f'Job #{job_id} started')

        vk_token = get_setting('vk_token')
        or_key = get_setting('openrouter_api_key')
        tg_token = get_setting('telegram_bot_token')
        tg_channel = get_setting('telegram_channel_id')

        if not all([vk_token, or_key, tg_token, tg_channel]):
            add_log(job_id, 'error', 'Missing API keys — check Settings')
            job.status = 'error'
            job.finished_at = datetime.utcnow()
            db.session.commit()
            return

        # Resolve group
        from services import vk_service
        try:
            vk = vk_service.get_vk_session(vk_token)
            if job.group_id:
                group = Group.query.get(job.group_id)
                group_url = group.vk_url
            else:
                group_url = job.group_url

            add_log(job_id, 'info', f'Resolving group: {group_url}')
            group_info = vk_service.resolve_group_id(vk, group_url)
            group_vk_id = group_info['id']
        except Exception as e:
            add_log(job_id, 'error', f'VK group error: {e}')
            job.status = 'error'
            job.finished_at = datetime.utcnow()
            db.session.commit()
            return

        # Fetch videos
        try:
            add_log(job_id, 'info', f'Fetching {job.video_count} videos ({job.filter_type})')
            videos = vk_service.fetch_videos(vk, group_vk_id, job.video_count, job.filter_type)
            add_log(job_id, 'success', f'Found {len(videos)} videos')
        except Exception as e:
            add_log(job_id, 'error', f'Fetch error: {e}')
            job.status = 'error'
            job.finished_at = datetime.utcnow()
            db.session.commit()
            return

        from services import video_service, ai_service, telegram_service

        processed = 0
        for idx, vk_video in enumerate(videos, 1):
            vid_id = f"{vk_video.get('owner_id')}_{vk_video.get('id')}"
            add_log(job_id, 'info', f'[{idx}/{len(videos)}] Processing video {vid_id}')

            # Create DB record
            video_rec = Video(
                job_id=job_id,
                vk_video_id=vid_id,
                original_title=vk_video.get('title', ''),
                original_desc=vk_video.get('description', ''),
            )
            db.session.add(video_rec)
            db.session.commit()

            raw_path = os.path.join(app.config['TMP_DIR'], f'raw_{job_id}_{idx}.mp4')
            out_path = os.path.join(app.config['TMP_DIR'], f'out_{job_id}_{idx}.mp4')

            try:
                # Step 1: Download
                add_log(job_id, 'info', f'[{idx}] Downloading video')
                dl_url = vk_service.get_video_download_url(vk_video)
                if not dl_url:
                    add_log(job_id, 'error', f'[{idx}] No direct URL available (private/restricted)')
                    continue
                vk_service.download_video(dl_url, raw_path)
                add_log(job_id, 'success', f'[{idx}] Downloaded')

                # Step 2: FFmpeg
                add_log(job_id, 'info', f'[{idx}] Processing with FFmpeg')
                video_service.process_video(raw_path, out_path)
                add_log(job_id, 'success', f'[{idx}] FFmpeg done')
                video_rec.output_path = out_path

                # Step 3: AI
                add_log(job_id, 'info', f'[{idx}] Generating text via OpenRouter')
                gen_title, gen_caption = ai_service.generate_text(
                    or_key,
                    vk_video.get('title', ''),
                    vk_video.get('description', ''),
                    job.language,
                )
                video_rec.generated_title = gen_title
                video_rec.generated_caption = gen_caption
                db.session.commit()
                bump_daily_stat('openrouter_requests')
                add_log(job_id, 'success', f'[{idx}] AI text generated')

                # Step 4: Telegram
                add_log(job_id, 'info', f'[{idx}] Sending to Telegram')
                telegram_service.send_video_and_caption(
                    tg_token, tg_channel, out_path, gen_title, gen_caption
                )
                video_rec.sent_to_telegram = True
                db.session.commit()
                bump_daily_stat('videos_processed')
                add_log(job_id, 'success', f'[{idx}] Sent to Telegram')

                processed += 1

            except Exception as e:
                add_log(job_id, 'error', f'[{idx}] Error: {e}')
                db.session.rollback()

            finally:
                # Cleanup temp files
                for p in (raw_path, out_path):
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass

                # Rate limit delay before next AI call
                if idx < len(videos):
                    time.sleep(app.config['OPENROUTER_REQUEST_DELAY'])

        # Update group stats
        if job.group_id:
            group = Group.query.get(job.group_id)
            if group:
                group.last_used_at = datetime.utcnow()
                group.total_parsed += processed
                db.session.commit()

        job.status = 'done'
        job.finished_at = datetime.utcnow()
        db.session.commit()
        add_log(job_id, 'success', f'Job #{job_id} complete — {processed}/{len(videos)} videos sent')


# ---------------------------------------------------------------------------
# Routes: Groups
# ---------------------------------------------------------------------------

@app.route('/api/groups', methods=['GET'])
def list_groups():
    groups = Group.query.order_by(Group.pinned.desc(), Group.added_at.desc()).all()
    return jsonify([g.to_dict() for g in groups])


@app.route('/api/groups', methods=['POST'])
def add_group():
    data = request.json
    url = data.get('vk_url', '').strip()
    if not url:
        return jsonify({'error': 'vk_url required'}), 400

    vk_token = get_setting('vk_token')
    if not vk_token:
        return jsonify({'error': 'VK token not configured'}), 400

    from services import vk_service
    try:
        vk = vk_service.get_vk_session(vk_token)
        info = vk_service.resolve_group_id(vk, url)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    existing = Group.query.filter_by(vk_url=url).first()
    if existing:
        return jsonify({'error': 'Group already exists'}), 409

    group = Group(
        vk_url=url,
        name=info['name'],
        avatar_url=info['avatar_url'],
    )
    db.session.add(group)
    db.session.commit()
    return jsonify(group.to_dict()), 201


@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/groups/<int:group_id>/pin', methods=['POST'])
def pin_group(group_id):
    group = Group.query.get_or_404(group_id)
    group.pinned = not group.pinned
    db.session.commit()
    return jsonify(group.to_dict())


# ---------------------------------------------------------------------------
# Routes: Jobs
# ---------------------------------------------------------------------------

@app.route('/api/jobs', methods=['POST'])
def start_job():
    data = request.json
    group_id = data.get('group_id')
    group_url = data.get('group_url', '').strip()

    if not group_id and not group_url:
        return jsonify({'error': 'Provide group_id or group_url'}), 400

    job = Job(
        group_id=group_id or None,
        group_url=group_url or None,
        video_count=int(data.get('video_count', 5)),
        filter_type=data.get('filter_type', 'new'),
        language=data.get('language', 'RU'),
    )
    db.session.add(job)
    db.session.commit()

    t = threading.Thread(target=run_job, args=(job.id,), daemon=True)
    t.start()

    return jsonify(job.to_dict()), 201


@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    job = Job.query.get_or_404(job_id)
    return jsonify(job.to_dict())


@app.route('/api/jobs/<int:job_id>/logs', methods=['GET'])
def get_logs(job_id):
    since_id = request.args.get('since', 0, type=int)
    logs = LogEntry.query.filter(
        LogEntry.job_id == job_id,
        LogEntry.id > since_id,
    ).order_by(LogEntry.id).all()
    job = Job.query.get_or_404(job_id)
    return jsonify({
        'logs': [l.to_dict() for l in logs],
        'job': job.to_dict(),
    })


@app.route('/api/jobs/latest', methods=['GET'])
def latest_job():
    job = Job.query.order_by(Job.id.desc()).first()
    if not job:
        return jsonify(None)
    return jsonify(job.to_dict())


# ---------------------------------------------------------------------------
# Routes: Stats
# ---------------------------------------------------------------------------

@app.route('/api/stats', methods=['GET'])
def get_stats():
    today = date.today()
    stat = DailyStat.query.filter_by(date=today).first()
    total_videos = db.session.query(db.func.sum(Video.sent_to_telegram == True)).scalar() or 0
    last_job = Job.query.filter(Job.finished_at != None).order_by(Job.finished_at.desc()).first()

    return jsonify({
        'openrouter_today': stat.openrouter_requests if stat else 0,
        'videos_today': stat.videos_processed if stat else 0,
        'videos_total': total_videos,
        'last_activity': last_job.finished_at.isoformat() if last_job else None,
    })


# ---------------------------------------------------------------------------
# Routes: Settings
# ---------------------------------------------------------------------------

SETTING_KEYS = ['vk_token', 'openrouter_api_key', 'telegram_bot_token', 'telegram_channel_id']


@app.route('/api/settings', methods=['GET'])
def get_settings():
    result = {}
    for key in SETTING_KEYS:
        val = get_setting(key)
        # Mask tokens for display
        if val and key in ('vk_token', 'openrouter_api_key', 'telegram_bot_token'):
            result[key] = val[:6] + '...' + val[-4:] if len(val) > 10 else '***'
        else:
            result[key] = val
    return jsonify(result)


@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    for key in SETTING_KEYS:
        if key in data and data[key] and not data[key].endswith('...'):
            set_setting(key, data[key])
    return jsonify({'ok': True})


@app.route('/api/settings/test/vk', methods=['POST'])
def test_vk():
    token = request.json.get('token') or get_setting('vk_token')
    if not token:
        return jsonify({'ok': False, 'error': 'No token'}), 400
    from services import vk_service
    try:
        vk = vk_service.get_vk_session(token)
        me = vk.users.get()
        return jsonify({'ok': True, 'user': me[0].get('first_name', 'OK')})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/settings/test/openrouter', methods=['POST'])
def test_openrouter():
    api_key = request.json.get('api_key') or get_setting('openrouter_api_key')
    if not api_key:
        return jsonify({'ok': False, 'error': 'No API key'}), 400
    import requests as req
    try:
        r = req.get(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        r.raise_for_status()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/settings/test/telegram', methods=['POST'])
def test_telegram():
    token = request.json.get('token') or get_setting('telegram_bot_token')
    channel = request.json.get('channel_id') or get_setting('telegram_channel_id')
    if not token or not channel:
        return jsonify({'ok': False, 'error': 'Token or channel missing'}), 400
    from services import telegram_service
    try:
        telegram_service.send_test_message(token, channel)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    port = app.config['PORT']
    app.run(host='0.0.0.0', port=port, debug=False)
