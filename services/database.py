"""Database service for submissions."""
from models import db, Submission, User
from typing import Optional, Dict


class SubmissionsService:
    """Service for managing event submissions in PostgreSQL."""

    @staticmethod
    def create_submission(submission_id: str, submission_type: str,
                         site_slug: str, user_id: int, email: str, data: dict) -> Submission:
        """Create a new submission in the database."""
        submission = Submission(
            submission_id=submission_id,
            user_id=user_id,
            site_slug=site_slug,
            submission_type=submission_type,
            status='pending',
            email=email,
            data=data
        )
        db.session.add(submission)
        db.session.commit()
        return submission

    @staticmethod
    def get_submission(submission_id: str) -> Optional[Dict]:
        """Get submission by ID."""
        submission = Submission.query.filter_by(submission_id=submission_id).first()
        if submission:
            return submission.to_dict()
        return None

    @staticmethod
    def get_submission_model(submission_id: str) -> Optional[Submission]:
        """Get submission model by ID."""
        return Submission.query.filter_by(submission_id=submission_id).first()

    @staticmethod
    def update_submission_status(submission_id: str, status: str, pr_url: str = None) -> None:
        """Update submission status and optionally store PR URL."""
        submission = Submission.query.filter_by(submission_id=submission_id).first()
        if submission:
            submission.status = status
            if pr_url:
                submission.pr_url = pr_url
            db.session.commit()

    @staticmethod
    def get_user_submissions(user_id: int, limit: int = 50):
        """Get submissions for a specific user."""
        return Submission.query.filter_by(user_id=user_id).order_by(
            Submission.created_at.desc()
        ).limit(limit).all()


class UserService:
    """Service for managing users."""

    @staticmethod
    def get_or_create_user(github_id: str, username: str, email: str = None,
                          avatar_url: str = None, name: str = None, github_token: str = None) -> User:
        """Get existing user or create new one from GitHub data."""
        user = User.query.filter_by(github_id=github_id).first()

        if user:
            # Update user info
            user.username = username
            user.email = email
            user.avatar_url = avatar_url
            user.name = name
            if github_token:
                user.github_token = github_token
            user.last_login = db.func.now()
            db.session.commit()
        else:
            # Create new user
            user = User(
                github_id=github_id,
                username=username,
                email=email,
                avatar_url=avatar_url,
                name=name,
                github_token=github_token
            )
            db.session.add(user)
            db.session.commit()

        return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_github_id(github_id: str) -> Optional[User]:
        """Get user by GitHub ID."""
        return User.query.filter_by(github_id=github_id).first()
