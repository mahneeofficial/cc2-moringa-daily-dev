import random
import sys
from faker import Faker

from app import create_app
from app.extensions import db
from app.models import (
    Bookmark,  # Fixed: Changed Wishlist to Bookmark
    Category,
    Comment,
    CommentReaction,
    Content,
    ContentReaction,
    ContentReport,
    Notification,
    Profile,
    Share,
    Subscription,
    User,
    content_categories,
)

app = create_app()


def seed_database():
    fake = Faker()

    # Constraints and predefined values
    content_statuses = ["Draft", "Published", "Archived"]
    content_types = ["Article", "Video", "Audio", "Image"]
    reaction_types = ["Like", "Love", "Haha", "Wow", "Sad", "Angry"]

    # Category list matching the UI/Figma design requirements
    figma_categories = [
        "DevOps",
        "Fullstack",
        "Frontend",
        "Backend",
        "Mobile",
        "Career",
        "AI/ML",
    ]

    print("🚀 Initializing database seeding process...")

    with app.app_context():
        try:
            # 1. Clear existing tables in explicit reverse-dependency order
            print("🧹 Clearing existing data from database...")

            db.session.execute(content_categories.delete())
            CommentReaction.query.delete()
            ContentReaction.query.delete()
            Comment.query.delete()
            ContentReport.query.delete()
            Notification.query.delete()
            Bookmark.query.delete()  # Fixed: Changed Wishlist to Bookmark
            Share.query.delete()
            Subscription.query.delete()
            Content.query.delete()
            Category.query.delete()
            Profile.query.delete()
            User.query.delete()

            db.session.commit()
            print("✅ All existing tables cleared successfully.")

            # 2. Seed Users & Profiles
            print("👥 Seeding users and profiles...")
            users = []
            for i in range(10):
                # Make the first user an Admin, second a tech_writer, rest regular Members
                if i == 0:
                    role = "Admin"
                elif i == 1:
                    role = "tech_writer"
                else:
                    role = "Member"

                user = User(
                    Username=fake.unique.user_name(),
                    Email=fake.unique.email(),
                    Role=role,
                    IsActive=True,
                )

                # Correctly hash user password
                if hasattr(user, "set_password"):
                    user.set_password("password12345")
                else:
                    user.password_hash = "password12345"

                profile = Profile(
                    Bio=fake.paragraph(nb_sentences=2),
                    ProfileImage=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.Username}",
                    Interests=", ".join(fake.words(nb=4)),
                )

                user.profile = profile
                db.session.add(user)
                users.append(user)

            db.session.flush()

            # 3. Seed Figma Categories
            print("📂 Seeding core categories...")
            categories = []
            admin_user = users[0]

            for name in figma_categories:
                category = Category(
                    Name=name,
                    Description=f"Discussions, guides, and resources for {name}.",
                    CreatedBy=admin_user.UserID,
                )
                db.session.add(category)
                categories.append(category)

            db.session.flush()

            # 4. Seed Content Items
            print("📦 Seeding content items...")
            contents = []
            for _ in range(15):
                author = random.choice(users)
                content_item = Content(
                    UserID=author.UserID,
                    Title=fake.sentence(nb_words=6).rstrip("."),
                    Description=fake.paragraph(nb_sentences=4),
                    ContentType=random.choice(content_types),
                    ContentURL=fake.url(),
                    Status=random.choice(content_statuses),
                    IsApproved=True,
                )

                # Safely set ViewsCount/LikesCount only if the model has those columns
                if hasattr(content_item, "ViewsCount"):
                    content_item.ViewsCount = random.randint(10, 500)
                elif hasattr(content_item, "views_count"):
                    content_item.views_count = random.randint(10, 500)

                # Attach 1 to 2 relevant categories
                assigned_categories = random.sample(
                    categories, k=random.randint(1, 2)
                )
                content_item.categories.extend(assigned_categories)

                db.session.add(content_item)
                contents.append(content_item)

            db.session.flush()

            # 5. Seed Parent Comments & Threaded Replies
            print("💬 Seeding comments and nested replies...")
            comments = []
            for _ in range(20):
                comment = Comment(
                    UserID=random.choice(users).UserID,
                    ContentID=random.choice(contents).ContentID,
                    Text=fake.sentence(),
                )
                db.session.add(comment)
                comments.append(comment)

            db.session.flush()

            # Nested replies referencing parent comments
            for _ in range(8):
                parent = random.choice(comments)
                reply = Comment(
                    UserID=random.choice(users).UserID,
                    ContentID=parent.ContentID,
                    ParentCommentID=parent.CommentID,
                    Text=fake.sentence(),
                )
                db.session.add(reply)

            db.session.flush()

            # 6. Seed Content Reactions
            print("👍 Seeding safe unique content reactions...")
            unique_content_likes = set()
            max_content_rxns = min(25, len(users) * len(contents))

            while len(unique_content_likes) < max_content_rxns:
                u_id = random.choice(users).UserID
                c_id = random.choice(contents).ContentID

                if (u_id, c_id) not in unique_content_likes:
                    unique_content_likes.add((u_id, c_id))
                    rxn = ContentReaction(
                        UserID=u_id,
                        ContentID=c_id,
                        Reaction=random.choice(reaction_types),
                    )
                    db.session.add(rxn)

            # 7. Seed Comment Reactions
            print("❤️  Seeding safe unique comment reactions...")
            unique_comment_likes = set()
            max_comment_rxns = min(15, len(users) * len(comments))

            while len(unique_comment_likes) < max_comment_rxns:
                u_id = random.choice(users).UserID
                m_id = random.choice(comments).CommentID

                if (u_id, m_id) not in unique_comment_likes:
                    unique_comment_likes.add((u_id, m_id))
                    rxn = CommentReaction(
                        UserID=u_id,
                        CommentID=m_id,
                        Reaction=random.choice(reaction_types),
                    )
                    db.session.add(rxn)

            # Commit all operations
            db.session.commit()
            print("🎉 Database successfully seeded!")

        except Exception as e:
            print(f"❌ Error occurred during execution: {e}")
            db.session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    seed_database()