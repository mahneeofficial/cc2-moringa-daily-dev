from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from app.extensions import bcrypt, db

# Association table for Many-to-Many relationship between Content and Category
content_categories = db.Table(
    'content_categories',
    db.Column('ContentID', db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), primary_key=True),
    db.Column('CategoryID', db.Integer, db.ForeignKey('categories.CategoryID', ondelete='CASCADE'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'users'

    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(150), nullable=False)
    Email = db.Column(db.String(200), unique=True, index=True, nullable=False)
    PasswordHash = db.Column(db.String, nullable=False)
    Role = db.Column(db.String(50), nullable=True, default='user')
    IsActive = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = db.relationship('Profile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    categories_created = db.relationship('Category', back_populates='creator', foreign_keys='Category.CreatedBy')
    contents = db.relationship('Content', back_populates='author', foreign_keys='Content.UserID', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='author', foreign_keys='Comment.UserID', cascade='all, delete-orphan')
    content_reactions = db.relationship('ContentReaction', back_populates='user', cascade='all, delete-orphan')
    comment_reactions = db.relationship('CommentReaction', back_populates='user', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', back_populates='user', cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', back_populates='user', cascade='all, delete-orphan')
    shares_sent = db.relationship('Share', foreign_keys='Share.UserID', back_populates='sender', cascade='all, delete-orphan')
    shares_received = db.relationship('Share', foreign_keys='Share.SharedWithUserID', back_populates='recipient', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    reports_submitted = db.relationship('ContentReport', back_populates='reporter', foreign_keys='ContentReport.ReportedBy', cascade='all, delete-orphan')

    @hybrid_property
    def password(self):
        raise AttributeError("Password hashes may not be viewed")

    @password.setter
    def password(self, plain_password):
        if not plain_password:
            raise ValueError("Password cannot be empty")
        if isinstance(plain_password, bytes):
            plain_password = plain_password.decode('utf-8')
        self.PasswordHash = bcrypt.generate_password_hash(plain_password).decode('utf-8')

    def set_password(self, plain_password):
        self.password = plain_password

    def check_password(self, plain_password):
        return self.authenticate(plain_password)

    def authenticate(self, plain_password):
        if not self.PasswordHash or not plain_password:
            return False
        try:
            if isinstance(plain_password, bytes):
                plain_password = plain_password.decode('utf-8')
            return bcrypt.check_password_hash(self.PasswordHash, plain_password)
        except Exception:
            return False

    @property
    def id(self):
        return self.UserID

    @property
    def username(self):
        return self.Username

    @property
    def email(self):
        return self.Email

    def to_dict(self):
        return {
            "id": self.UserID,
            "username": self.Username,
            "email": self.Email,
            "role": self.Role or "user",
            "isActive": self.IsActive,
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class Profile(db.Model):
    __tablename__ = 'profiles'

    ProfileID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), unique=True, index=True, nullable=False)
    Bio = db.Column(db.Text, nullable=True)
    Interests = db.Column(db.Text, nullable=True)
    ProfileImage = db.Column(db.String(255), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    UpdatedAt = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship('User', back_populates='profile')

    def to_dict(self):
        return {
            "profileId": self.ProfileID,
            "userId": self.UserID,
            "bio": self.Bio,
            "interests": self.Interests,
            "profileImage": self.ProfileImage,
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None,
            "updatedAt": self.UpdatedAt.isoformat() if self.UpdatedAt else None
        }


class Category(db.Model):
    __tablename__ = 'categories'

    CategoryID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), unique=True, nullable=False)
    Slug = db.Column(db.String(150), unique=True, nullable=True)
    Description = db.Column(db.Text, nullable=True)
    IconURL = db.Column(db.String(255), nullable=True)
    CreatedBy = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='SET NULL'), index=True, nullable=True)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship('User', back_populates='categories_created')
    subscribers = db.relationship('Subscription', back_populates='category', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.CategoryID,
            "name": self.Name,
            "slug": self.Slug,
            "description": self.Description,
            "iconUrl": self.IconURL,
            "createdBy": self.CreatedBy,
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class Content(db.Model):
    __tablename__ = 'content'

    ContentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    Title = db.Column(db.String(255), nullable=False)
    Slug = db.Column(db.String(255), unique=True, nullable=True)
    Description = db.Column(db.Text, nullable=True)
    Body = db.Column(db.Text, nullable=True)
    ContentType = db.Column(db.String(50), nullable=True, default='Article')
    ContentURL = db.Column(db.String(255), nullable=True)
    Status = db.Column(db.String(50), nullable=True, default='Published')
    IsApproved = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    UpdatedAt = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    author = db.relationship('User', back_populates='contents')
    categories = db.relationship(
        'Category',
        secondary=content_categories,
        backref=db.backref('contents', lazy='selectin')
    )
    comments = db.relationship('Comment', back_populates='content', cascade="all, delete-orphan")
    reactions = db.relationship('ContentReaction', back_populates='content', cascade="all, delete-orphan")
    bookmarks = db.relationship('Bookmark', back_populates='content', cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='content', cascade="all, delete-orphan")
    notifications = db.relationship('Notification', back_populates='content', cascade="all, delete-orphan")
    reports = db.relationship('ContentReport', back_populates='content', cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "Status IN ('Draft', 'Pending', 'Published', 'Archived')",
            name='check_valid_content_status'
        ),
        CheckConstraint(
            "ContentType IN ('Article', 'Video', 'Audio', 'Image')",
            name='check_valid_content_type'
        ),
    )

    @property
    def id(self):
        return self.ContentID

    @property
    def title(self):
        return self.Title

    @property
    def body(self):
        return self.Body or self.Description

    def to_dict(self):
        return {
            "id": self.ContentID,
            "title": self.Title,
            "slug": self.Slug,
            "description": self.Description,
            "body": self.Body,
            "type": (self.ContentType or "article").lower(),
            "url": self.ContentURL,
            "status": self.Status,
            "isApproved": self.IsApproved,
            "userId": self.UserID,
            "author": self.author.to_dict() if self.author else None,
            "categories": [c.to_dict() for c in self.categories],
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None,
            "updatedAt": self.UpdatedAt.isoformat() if self.UpdatedAt else None
        }


class Comment(db.Model):
    __tablename__ = 'comments'

    CommentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=False)
    ParentCommentID = db.Column(db.Integer, db.ForeignKey('comments.CommentID', ondelete='CASCADE'), index=True, nullable=True)
    Text = db.Column(db.Text, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    UpdatedAt = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    author = db.relationship('User', back_populates='comments')
    content = db.relationship('Content', back_populates='comments')
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[CommentID]),
        cascade="all, delete-orphan"
    )
    reactions = db.relationship('CommentReaction', back_populates='comment', cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('CommentID != ParentCommentID', name='check_no_self_parenting_comment'),
        CheckConstraint('length(trim(Text)) > 0', name='check_comment_not_empty')
    )

    def to_dict(self):
        return {
            "id": self.CommentID,
            "contentId": self.ContentID,
            "userId": self.UserID,
            "parentCommentId": self.ParentCommentID,
            "text": self.Text,
            "author": self.author.Username if self.author else f"User #{self.UserID}",
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class ContentReaction(db.Model):
    __tablename__ = 'content_reactions'

    ReactionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=False)
    Reaction = db.Column(db.String(50), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='content_reactions')
    content = db.relationship('Content', back_populates='reactions')

    __table_args__ = (
        UniqueConstraint('UserID', 'ContentID', name='unique_user_content_reaction'),
        Index('ix_content_reaction_lookup', 'ContentID', 'Reaction'),
    )


class CommentReaction(db.Model):
    __tablename__ = 'comment_reactions'

    ReactionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    CommentID = db.Column(db.Integer, db.ForeignKey('comments.CommentID', ondelete='CASCADE'), index=True, nullable=False)
    Reaction = db.Column(db.String(50), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='comment_reactions')
    comment = db.relationship('Comment', back_populates='reactions')

    __table_args__ = (
        UniqueConstraint('UserID', 'CommentID', name='unique_user_comment_reaction'),
        Index('ix_comment_reaction_lookup', 'CommentID', 'Reaction'),
    )


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    SubscriptionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    CategoryID = db.Column(db.Integer, db.ForeignKey('categories.CategoryID', ondelete='CASCADE'), index=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='subscriptions')
    category = db.relationship('Category', back_populates='subscribers')

    __table_args__ = (
        UniqueConstraint('UserID', 'CategoryID', name='unique_user_category_subscription'),
    )


class Bookmark(db.Model):
    __tablename__ = 'bookmarks'

    BookmarkID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='bookmarks')
    content = db.relationship('Content', back_populates='bookmarks')

    __table_args__ = (
        UniqueConstraint('UserID', 'ContentID', name='unique_user_content_bookmark'),
    )


class Share(db.Model):
    __tablename__ = 'shares'

    ShareID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=False)
    SharedWithUserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=True)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sender = db.relationship('User', foreign_keys=[UserID], back_populates='shares_sent')
    recipient = db.relationship('User', foreign_keys=[SharedWithUserID], back_populates='shares_received')
    content = db.relationship('Content', back_populates='shares')


class Notification(db.Model):
    __tablename__ = 'notifications'

    NotificationID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=True)
    Type = db.Column(db.String(50), nullable=True, default='general')
    Message = db.Column(db.Text, nullable=False)
    IsRead = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='notifications')
    content = db.relationship('Content', back_populates='notifications')

    def to_dict(self):
        return {
            "id": self.NotificationID,
            "userId": self.UserID,
            "contentId": self.ContentID,
            "type": self.Type,
            "message": self.Message,
            "isRead": self.IsRead,
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class ContentReport(db.Model):
    __tablename__ = 'content_reports'

    ReportID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID', ondelete='CASCADE'), index=True, nullable=False)
    ReportedBy = db.Column(db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), index=True, nullable=False)
    Reason = db.Column(db.Text, nullable=False)
    Status = db.Column(db.String(50), nullable=True, default='Pending')
    CreatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    reporter = db.relationship('User', foreign_keys=[ReportedBy], back_populates='reports_submitted')
    content = db.relationship('Content', back_populates='reports')

    def to_dict(self):
        return {
            "id": self.ReportID,
            "contentId": self.ContentID,
            "contentTitle": self.content.Title if self.content else "Deleted Content",
            "reportedBy": self.ReportedBy,
            "reporterUsername": self.reporter.Username if self.reporter else f"User #{self.ReportedBy}",
            "reason": self.Reason,
            "status": self.Status or "Pending",
            "createdAt": self.CreatedAt.isoformat() if self.CreatedAt else None
        }