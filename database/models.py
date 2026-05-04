from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    vk_url = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)
    pinned = db.Column(db.Boolean, default=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    total_parsed = db.Column(db.Integer, default=0)

    jobs = db.relationship('Job', backref='group', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'vk_url': self.vk_url,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'pinned': self.pinned,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'total_parsed': self.total_parsed,
        }


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    group_url = db.Column(db.String(255), nullable=True)  # for ad-hoc URLs
    status = db.Column(db.String(20), default='pending')  # pending/processing/done/error
    video_count = db.Column(db.Integer, default=5)
    filter_type = db.Column(db.String(20), default='new')  # new/popular/random
    language = db.Column(db.String(5), default='RU')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    videos = db.relationship('Video', backref='job', lazy=True)
    logs = db.relationship('LogEntry', backref='job', lazy=True, order_by='LogEntry.created_at')

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'group_url': self.group_url,
            'status': self.status,
            'video_count': self.video_count,
            'filter_type': self.filter_type,
            'language': self.language,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'videos_done': sum(1 for v in self.videos if v.sent_to_telegram),
            'videos_total': len(self.videos),
        }


class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    vk_video_id = db.Column(db.String(100), nullable=True)
    original_title = db.Column(db.Text, nullable=True)
    original_desc = db.Column(db.Text, nullable=True)
    generated_title = db.Column(db.Text, nullable=True)
    generated_caption = db.Column(db.Text, nullable=True)
    output_path = db.Column(db.String(512), nullable=True)
    sent_to_telegram = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LogEntry(db.Model):
    __tablename__ = 'log_entries'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    level = db.Column(db.String(10), default='info')  # info/success/error
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'time': self.created_at.strftime('%H:%M:%S'),
        }


class DailyStat(db.Model):
    __tablename__ = 'daily_stats'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=date.today, unique=True)
    openrouter_requests = db.Column(db.Integer, default=0)
    videos_processed = db.Column(db.Integer, default=0)


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
