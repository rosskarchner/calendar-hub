"""Database models for Calendar Hub."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for GitHub OAuth authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    avatar_url = db.Column(db.String(512))
    name = db.Column(db.String(255))
    github_token = db.Column(db.String(512))  # Store encrypted in production
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to submissions
    submissions = db.relationship('Submission', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class Submission(db.Model):
    """Submission model for events and newsletters."""
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    site_slug = db.Column(db.String(255), nullable=False, index=True)
    submission_type = db.Column(db.String(50), nullable=False)  # 'event' or 'newsletter'
    status = db.Column(db.String(50), default='pending', index=True)  # 'pending', 'confirmed', 'rejected'
    email = db.Column(db.String(255))
    data = db.Column(db.JSON, nullable=False)  # Store submission data as JSON
    pr_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Submission {self.submission_id} - {self.status}>'

    def to_dict(self):
        """Convert submission to dictionary."""
        return {
            'submission_id': self.submission_id,
            'user_id': self.user_id,
            'site_slug': self.site_slug,
            'type': self.submission_type,
            'status': self.status,
            'email': self.email,
            'data': self.data,
            'pr_url': self.pr_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
