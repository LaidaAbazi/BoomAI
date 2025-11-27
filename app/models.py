from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, func, Table, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date, timezone
from app import db


class Company(db.Model):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship('User', back_populates='owned_company', foreign_keys=[owner_user_id])
    users = relationship('User', back_populates='company', foreign_keys='User.company_id')


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    # Company / role fields
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='SET NULL'), nullable=True)
    role = Column(String(50), nullable=False, default='owner')  # 'owner' or 'employee'
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

    # LinkedIn integration fields
    linkedin_connected = Column(Boolean, default=False)
    linkedin_member_id = Column(String(100), nullable=True)  # LinkedIn Member ID (sub)
    linkedin_access_token = Column(Text, nullable=True)  # Encrypted access token (TEXT for long encrypted values)
    linkedin_refresh_token = Column(Text, nullable=True)  # Encrypted refresh token (TEXT for long encrypted values)
    linkedin_scope = Column(String(500), nullable=True)  # Store granted scopes
    linkedin_name = Column(String(200), nullable=True)  # LinkedIn display name
    linkedin_email = Column(String(255), nullable=True)  # LinkedIn email (if available)
    linkedin_token_expires_at = Column(DateTime(timezone=True), nullable=True)  # Token expiration timestamp
    linkedin_authed_at = Column(DateTime(timezone=True), nullable=True)  # When OAuth was completed

    # Story usage tracking fields
    stories_used_this_month = Column(Integer, default=0)
    extra_credits = Column(Integer, default=0)
    last_reset_date = Column(Date, nullable=True)

    
    # Subscription status
    has_active_subscription = Column(Boolean, default=False)
    subscription_start_date = Column(Date, nullable=True)
    
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Relationships
    company = relationship('Company', back_populates='users', foreign_keys=[company_id])
    owned_company = relationship('Company', back_populates='owner', uselist=False, foreign_keys=[Company.owner_user_id])
    case_studies = relationship('CaseStudy', back_populates='user')
    slack_installations = relationship('SlackInstallation', back_populates='user', cascade='all, delete-orphan')
    teams_installations = relationship('TeamsInstallation', back_populates='user', cascade='all, delete-orphan')

    def can_create_story(self):
        """Check if user can create a story (has active subscription and credits)"""
        # TEMPORARILY DISABLED - Allow story creation without subscription
        return True  # Always allow
        
        # Original code (commented for easy revert):
        # if not self.has_active_subscription:
        #     return False
        # return self.stories_used_this_month < 10 or self.extra_credits > 0
    
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
        """Reset monthly story usage (called on subscription renewal via webhook)"""
        self.stories_used_this_month = 0
        self.last_reset_date = date.today()


class CaseStudy(db.Model):
    __tablename__ = 'case_studies'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # Optional: company scoping for owner visibility (same company as creator)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=True)
    title = Column(String(200))
    final_summary = Column(Text)
    final_summary_pdf_path = Column(String(500))
    final_summary_pdf_data = Column(db.LargeBinary)
    final_summary_word_data = Column(db.LargeBinary)
    sentiment_chart_data = Column(db.LargeBinary, nullable=True)
    meta_data_text = Column(Text, nullable=True)
    linkedin_post = Column(Text, nullable=True)
    email_subject = Column(Text, nullable=True)
    email_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # HeyGen video fields
    video_id = Column(String(100), nullable=True)
    video_url = Column(Text, nullable=True)
    video_status = Column(String(50), nullable=True)
    video_created_at = Column(DateTime(timezone=True), nullable=True)

    # HeyGen newsflash video fields (30-second)
    newsflash_video_id = Column(String(100), nullable=True)
    newsflash_video_url = Column(Text, nullable=True)
    newsflash_video_status = Column(String(50), nullable=True)
    newsflash_video_created_at = Column(DateTime(timezone=True), nullable=True)

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
    # podcast_audio_data = Column(db.LargeBinary, nullable=True)  NEW
    # podcast_audio_mime = Column(String(64), nullable=True)     NEW
    # podcast_audio_size = Column(Integer, nullable=True)         NEW
    
    # Story counting field
    story_counted = Column(Boolean, default=False)
    podcast_script = Column(Text, nullable=True)
    
    # Language field
    language = Column(String(50), nullable=True)  # Store detected language (e.g., 'English', 'Spanish')
    
    # Submission fields
    submitted = Column(Boolean, default=False)  # Whether story has been submitted to owner
    submitted_at = Column(DateTime(timezone=True), nullable=True)  # When story was submitted

    user = relationship('User', back_populates='case_studies')
    company = relationship('Company')
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


class CompanyInvite(db.Model):
    __tablename__ = 'company_invites'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), nullable=False, default='employee')  # Currently only 'employee'
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used = Column(Boolean, default=False)

    company = relationship('Company', backref='invites')

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

class StoryFeedback(db.Model):
    __tablename__ = 'story_feedbacks'
    id = Column(Integer, primary_key=True)
    case_study_id = Column(Integer, ForeignKey('case_studies.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_thumbs_up = Column(Boolean, nullable=False)  # True for thumbs up, False for thumbs down
    is_thumbs_down = Column(Boolean, nullable=False, default=False)  # True for thumbs down, False for thumbs up
    feedback_text = Column(Text, nullable=True)  # Optional text feedback (can be provided with or without thumbs down)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    case_study = relationship('CaseStudy', backref='story_feedbacks')
    user = relationship('User', backref='story_feedbacks')
    
    # Unique constraint: one feedback per user per story
    __table_args__ = (
        db.UniqueConstraint('case_study_id', 'user_id', name='uq_story_feedback_user'),
    )
    
    def __init__(self, **kwargs):
        # Automatically set is_thumbs_down based on is_thumbs_up
        if 'is_thumbs_up' in kwargs:
            kwargs['is_thumbs_down'] = not kwargs['is_thumbs_up']
        super().__init__(**kwargs)
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_study_id': self.case_study_id,
            'user_id': self.user_id,
            'is_thumbs_up': self.is_thumbs_up,
            'is_thumbs_down': self.is_thumbs_down,
            'feedback_text': self.feedback_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OAuthState(db.Model):
    """
    Store OAuth state values for CSRF protection across multiple hosts.
    Each state is associated with a user, has an expiration time, and stores
    the redirect_uri that was used for the OAuth request.
    """
    __tablename__ = 'oauth_states'
    id = Column(Integer, primary_key=True)
    state = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    redirect_uri = Column(String(500), nullable=False)  # Store the redirect URI used
    content = Column(Text, nullable=True)  # Optional: store content to be posted
    frontend_callback_url = Column(String(500), nullable=True)  # Frontend URL to redirect to after OAuth
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # State expiration time
    used = Column(Boolean, default=False)  # Mark as used after successful validation
    
    user = relationship('User', backref='oauth_states')
    
    def is_expired(self):
        """Check if the state has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self):
        """Check if the state is valid (not expired and not used)"""
        return not self.is_expired() and not self.used

class StripeWebhookEvent(db.Model):
    """Track processed Stripe webhook events for idempotency"""
    __tablename__ = 'stripe_webhook_events'
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)  # Stripe event ID
    event_type = Column(String(100), nullable=False)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f'<StripeWebhookEvent {self.event_id}>' 
