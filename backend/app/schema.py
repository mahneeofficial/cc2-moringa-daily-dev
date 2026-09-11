from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from app.models import (
    User, Profile, Category, Content, Comment, CommentReaction, 
    ContentReaction, Subscription, Bookmark, Share, Notification, ContentReport
)
from app.extensions import db

class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        sqla_session = db.session
        include_relationships = True
        include_fk = True

class ProfileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Profile
        load_instance = True
        sqla_session = db.session
        include_fk = True

class CategorySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        load_instance = True
        sqla_session = db.session
        include_fk = True

class ContentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Content
        load_instance = True
        sqla_session = db.session
        include_relationships = True
        include_fk = True

class CommentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Comment
        load_instance = True
        sqla_session = db.session
        include_fk = True

class ContentReactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContentReaction
        load_instance = True
        sqla_session = db.session
        include_fk = True

class CommentReactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CommentReaction
        load_instance = True
        sqla_session = db.session
        include_fk = True

class SubscriptionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Subscription
        load_instance = True
        sqla_session = db.session
        include_fk = True

class BookmarkSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Bookmark
        load_instance = True
        sqla_session = db.session
        include_fk = True

class ShareSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Share
        load_instance = True
        sqla_session = db.session
        include_fk = True

class NotificationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Notification
        load_instance = True
        sqla_session = db.session
        include_fk = True

class ContentReportSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContentReport
        load_instance = True
        sqla_session = db.session
        include_fk = True

user_schema = UserSchema()
users_schema = UserSchema(many=True)
profile_schema = ProfileSchema()
profiles_schema = ProfileSchema(many=True)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
content_schema = ContentSchema()
contents_schema = ContentSchema(many=True)
comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)
content_reaction_schema = ContentReactionSchema()
content_reactions_schema = ContentReactionSchema(many=True)
comment_reaction_schema = CommentReactionSchema()
comment_reactions_schema = CommentReactionSchema(many=True)
subscription_schema = SubscriptionSchema()
subscriptions_schema = SubscriptionSchema(many=True)
bookmark_schema = BookmarkSchema()
bookmarks_schema = BookmarkSchema(many=True)
share_schema = ShareSchema()
shares_schema = ShareSchema(many=True)
notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)
content_report_schema = ContentReportSchema()
content_reports_schema = ContentReportSchema(many=True)