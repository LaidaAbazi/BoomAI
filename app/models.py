from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, func, Table, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app import db

class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    company_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime(timezone=True))
    is_verified = Column(Boolean, default=False)

    # Slack integration fields
    slack_connected = Column(Boolean, default=False)
    slack_user_id = Column(String(100), nullable=True)
    slack_team_id = Column(String(100), nullable=True)  # Store team/workspace ID
    slack_user_token = Column(String(500), nullable=True)  # Encrypted token
    slack_scope = Column(String(500), nullable=True)  # Store granted scopes
    slack_authed_at = Column(DateTime(timezone=True), nullable=True)  # When OAuth was completed

    # Teams integration fields
    teams_connected = Column(Boolean, default=False)
    teams_user_id = Column(String(100), nullable=True)
    teams_tenant_id = Column(String(100), nullable=True)  # Store tenant ID
    teams_user_token = Column(String(500), nullable=True)  # Encrypted token
    teams_scope = Column(String(500), nullable=True)  # Store granted scopes
    teams_authed_at = Column(DateTime(timezone=True), nullable=True)  # When OAuth was completed

    # Story usage tracking fields
    stories_used_this_month = Column(Integer, default=0)
    extra_credits = Column(Integer, default=0)
    last_reset_date = Column(Date, nullable=True)
    
    # Subscription status
    has_active_subscription = Column(Boolean, default=False)
    subscription_start_date = Column(Date, nullable=True)


    case_studies = relationship('CaseStudy', back_populates='user')
    slack_installations = relationship('SlackInstallation', back_populates='user', cascade='all, delete-orphan')
    teams_installations = relationship('TeamsInstallation', back_populates='user', cascade='all, delete-orphan')

    def can_create_story(self):
        """Check if user can create a story (has active subscription and credits)"""
        if not self.has_active_subscription:
            return False
        return self.stories_used_this_month < 10 or self.extra_credits > 0
    
    def can_buy_extra_credits(self):
        """Check if user can buy extra credits (must have used all 10 monthly stories)"""
        return self.stories_used_this_month >= 10
    
    def needs_subscription(self):
        """Check if user needs to subscribe to monthly plan"""
        return not self.has_active_subscription

    def record_story_creation(self):
        """Record story creation and update counters"""
        if self.stories_used_this_month < 10:
            # Use monthly allowance
            self.stories_used_this_month += 1
        elif self.extra_credits > 0:
            # Use extra credit
            self.extra_credits -= 1
            self.stories_used_this_month += 1
        else:
            raise ValueError("No credits left")

    def add_extra_credits(self, quantity):
        """Add extra story credits"""
        self.extra_credits += quantity

    def reset_monthly_usage(self):
        """Reset monthly story usage (called by scheduled job)"""
        self.stories_used_this_month = 0
        self.last_reset_date = date.today()


class CaseStudy(db.Model):
    __tablename__ = 'case_studies'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200))
    final_summary = Column(Text)
    final_summary_pdf_path = Column(String(500))
    final_summary_pdf_data = Column(db.LargeBinary)
    final_summary_word_data = Column(db.LargeBinary)
    sentiment_chart_data = Column(db.LargeBinary, nullable=True)
    meta_data_text = Column(Text, nullable=True)
    linkedin_post = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # HeyGen video fields
    video_id = Column(String(100), nullable=True)
    video_url = Column(Text, nullable=True)
    video_status = Column(String(50), nullable=True)
    video_created_at = Column(DateTime(timezone=True), nullable=True)

    # Pictory video fields
    pictory_storyboard_id = Column(String(100), nullable=True)
    pictory_render_id = Column(String(100), nullable=True)
    pictory_video_url = Column(Text, nullable=True)
    pictory_video_status = Column(String(50), nullable=True)
    pictory_video_created_at = Column(DateTime(timezone=True), nullable=True)

        # Wondercraft podcast fields
    podcast_job_id = Column(String(100), nullable=True)
    podcast_url = Column(Text, nullable=True)
    podcast_status = Column(String(50), nullable=True)
    podcast_created_at = Column(DateTime(timezone=True), nullable=True)
    podcast_audio_data = Column(db.LargeBinary, nullable=True)
    podcast_audio_mime = Column(String(64), nullable=True)
    podcast_audio_size = Column(Integer, nullable=True)
    podcast_audio_data = Column(db.LargeBinary, nullable=True)  # NEW
    podcast_audio_mime = Column(String(64), nullable=True)     # NEW
    podcast_audio_size = Column(Integer, nullable=True)         # NEW
    
    # Story counting field
    story_counted = Column(Boolean, default=False)
    podcast_script = Column(Text, nullable=True)

    user = relationship('User', back_populates='case_studies')
    solution_provider_interview = relationship('SolutionProviderInterview', uselist=False, back_populates='case_study')
    client_interview = relationship('ClientInterview', uselist=False, back_populates='case_study')
    invite_tokens = relationship('InviteToken', back_populates='case_study')
    labels = relationship('Label', secondary='case_study_labels', back_populates='case_studies')

class SlackInstallation(db.Model):
    __tablename__ = 'slack_installations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    slack_team_id = Column(String(100), nullable=False)
    slack_team_name = Column(String(200), nullable=False)
    bot_token = Column(String(500), nullable=False)  # Encrypted bot token
    is_enterprise_install = Column(Boolean, default=False)
    enterprise_id = Column(String(100), nullable=True)
    enterprise_name = Column(String(200), nullable=True)
    scope = Column(String(500), nullable=False)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship('User', back_populates='slack_installations')
    
    # Unique constraint: one installation per user per team/enterprise
    __table_args__ = (
        db.UniqueConstraint('user_id', 'slack_team_id', name='uq_user_team'),
    )

class TeamsInstallation(db.Model):
    __tablename__ = 'teams_installations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    teams_tenant_id = Column(String(100), nullable=False)
    teams_tenant_name = Column(String(200), nullable=False)
    access_token = Column(String(500), nullable=False)  # Encrypted access token
    refresh_token = Column(String(500), nullable=True)  # Encrypted refresh token
    scope = Column(String(500), nullable=False)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship('User', back_populates='teams_installations')
    
    # Unique constraint: one installation per user per tenant
    __table_args__ = (
        db.UniqueConstraint('user_id', 'teams_tenant_id', name='uq_user_teams_tenant'),
    )

class SolutionProviderInterview(db.Model):
    __tablename__ = 'solution_provider_interviews'
    id = Column(Integer, primary_key=True)
    case_study_id = Column(Integer, ForeignKey('case_studies.id', ondelete='CASCADE'), nullable=False, unique=True)
    session_id = Column(String(36), unique=True, nullable=False)
    transcript = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client_link_url = Column(String(500), nullable=True)

    case_study = relationship('CaseStudy', back_populates='solution_provider_interview')

class ClientInterview(db.Model):
    __tablename__ = 'client_interviews'
    id = Column(Integer, primary_key=True)
    case_study_id = Column(Integer, ForeignKey('case_studies.id', ondelete='CASCADE'), nullable=False, unique=True)
    session_id = Column(String(36), unique=True, nullable=False)
    transcript = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case_study = relationship('CaseStudy', back_populates='client_interview')

class InviteToken(db.Model):
    __tablename__ = 'invite_tokens'
    id = Column(Integer, primary_key=True)
    case_study_id = Column(Integer, ForeignKey('case_studies.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(36), unique=True, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case_study = relationship('CaseStudy', back_populates='invite_tokens')

# Association table for many-to-many relationship between CaseStudy and Label
case_study_labels = Table(
    'case_study_labels', db.metadata,
    Column('case_study_id', Integer, ForeignKey('case_studies.id', ondelete='CASCADE'), primary_key=True),
    Column('label_id', Integer, ForeignKey('labels.id', ondelete='CASCADE'), primary_key=True)
)

class Label(db.Model):
    __tablename__ = 'labels'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    color = Column(String(7), nullable=False)  # HEX color code (e.g., #FAD0D0)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User')
    case_studies = relationship('CaseStudy', secondary=case_study_labels, back_populates='labels')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-assign color if not provided
        if not self.color and self.name:
            from app.utils.color_utils import ColorUtils
            self.color = ColorUtils.get_color_for_label(self.name)

class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    feedback_type = Column(String(50))
    status = Column(String(20), default='pending')
    feedback_summary = Column(Text, nullable=True)
    
    user = relationship('User', backref='feedbacks')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'rating': self.rating,
            'created_at': self.created_at.isoformat(),
            'feedback_type': self.feedback_type,
            'status': self.status,
            'feedback_summary': self.feedback_summary
        } 