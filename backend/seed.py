import json
import random
import sys
import urllib.request
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Bookmark,
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


def fetch_external_feed():
    """Fetch live tech articles dynamically from the public Dev.to API."""
    url = "https://dev.to/api/articles?per_page=30"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("✅ Successfully fetched live articles from Dev.to API.")
                return json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Failed to fetch live API data: {e}")
    return []


def seed_database():
    app = create_app()

    with app.app_context():
        print("🌐 Fetching live API payload from Dev.to...")
        feed_items = fetch_external_feed()

        if not feed_items:
            print("❌ No live items fetched. Check internet connection and aborting seed.")
            return

        try:
            # 1. Clear existing database records in strict reverse dependency order
            print("🧹 Clearing existing database records...")
            db.session.execute(content_categories.delete())
            CommentReaction.query.delete()
            ContentReaction.query.delete()
            Comment.query.delete()
            ContentReport.query.delete()
            Notification.query.delete()
            Bookmark.query.delete()
            Share.query.delete()
            Subscription.query.delete()
            Content.query.delete()
            Category.query.delete()
            Profile.query.delete()
            User.query.delete()

            db.session.commit()
            print("✅ Database cleared successfully.")

            users_map = {}
            categories_map = {}
            contents = []
            comments = []
            default_password = "password12345"

            # 2. Seed Users & Profiles dynamically from Dev.to author payloads
            print("👥 Seeding Users and Profiles from live author payloads...")
            for item in feed_items:
                author_info = item.get("user", {})
                username = author_info.get("username")
                description = item.get("description", "")

                if not username:
                    continue

                if username not in users_map:
                    role = (
                        "Admin"
                        if len(users_map) == 0
                        else ("tech_writer" if len(users_map) == 1 else "Member")
                    )

                    user = User(
                        Username=username,
                        Email=f"{username}@dev.to",
                        Role=role,
                        IsActive=True,
                    )

                    # Set hashed password safely
                    if hasattr(user, "set_password"):
                        user.set_password(default_password)
                    elif hasattr(user, "password_hash"):
                        user.password_hash = generate_password_hash(default_password)

                    bio = (
                        author_info.get("summary")
                        or description
                        or "Software engineer & content creator."
                    )
                    profile_img = (
                        author_info.get("profile_image_90")
                        or f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
                    )

                    profile = Profile()

                    # Set Profile fields defensively to match your model schema
                    if hasattr(profile, "Bio"):
                        profile.Bio = bio[:255]
                    elif hasattr(profile, "bio"):
                        profile.bio = bio[:255]

                    if hasattr(profile, "ProfileImage"):
                        profile.ProfileImage = profile_img
                    elif hasattr(profile, "profile_image"):
                        profile.profile_image = profile_img

                    user.profile = profile
                    db.session.add(user)
                    users_map[username] = user

            db.session.flush()

            # 3. Seed Categories dynamically from Article Tags
            print("📂 Seeding Categories dynamically from article tags...")
            first_user = list(users_map.values())[0]

            for item in feed_items:
                for tag in item.get("tag_list", []):
                    tag_name = tag.capitalize()
                    if tag_name not in categories_map:
                        category = Category(
                            Name=tag_name,
                            Description=f"Real discussions and tutorials about {tag_name}.",
                            CreatedBy=first_user.UserID,
                        )
                        db.session.add(category)
                        categories_map[tag_name] = category

            db.session.flush()
            user_list = list(users_map.values())

            # 4. Seed Content directly from Dev.to Articles
            print("📦 Seeding Content items directly from live articles...")
            for item in feed_items:
                author_info = item.get("user", {})
                username = author_info.get("username")
                title = item.get("title")
                description = item.get("description")
                article_url = item.get("canonical_url") or item.get("url")
                
                # Dynamic image fallback: resolves missing/null cover_image values from API
                cover_img = (
                    item.get("cover_image")
                    or item.get("social_image")
                    or f"https://picsum.photos/800/400?random={item.get('id', random.randint(1, 1000))}"
                )

                if not username or not title or username not in users_map:
                    continue

                content_item = Content(
                    UserID=users_map[username].UserID,
                    Title=title,
                    Description=description or title,
                    ContentType="Article",
                    ContentURL=article_url,
                    Status="Published",
                    IsApproved=True,
                )

                if hasattr(content_item, "ThumbnailURL"):
                    content_item.ThumbnailURL = cover_img
                if hasattr(content_item, "ViewsCount"):
                    content_item.ViewsCount = random.randint(50, 1200)

                for tag in item.get("tag_list", []):
                    tag_name = tag.capitalize()
                    if tag_name in categories_map:
                        content_item.categories.append(categories_map[tag_name])

                db.session.add(content_item)
                contents.append(content_item)

            db.session.flush()

            # 5. Seed Comments dynamically using real excerpts
            print("💬 Seeding Comments using live article excerpts...")
            for content in contents:
                comment_author = random.choice(user_list)
                comment_text = f"Great insights on this! {content.Description[:100]}"

                comment = Comment(
                    UserID=comment_author.UserID,
                    ContentID=content.ContentID,
                    Text=comment_text,
                )
                db.session.add(comment)
                comments.append(comment)

            db.session.flush()

            # 6. Seed Reactions with unique user-content constraints
            print("👍 Seeding Content Reactions...")
            unique_likes = set()
            reaction_choices = ["Like", "Love", "Haha", "Wow"]
            max_rxns = min(40, len(contents) * len(user_list))

            while len(unique_likes) < max_rxns:
                u_id = random.choice(user_list).UserID
                c_id = random.choice(contents).ContentID

                if (u_id, c_id) not in unique_likes:
                    unique_likes.add((u_id, c_id))
                    rxn = ContentReaction(
                        UserID=u_id,
                        ContentID=c_id,
                        Reaction=random.choice(reaction_choices),
                    )
                    db.session.add(rxn)

            db.session.commit()
            print("🎉 Database successfully populated with real external data from Dev.to!")
            print(f"🔑 Default login password for seeded accounts: '{default_password}'")

        except Exception as e:
            print(f"❌ Error during database seeding: {e}")
            db.session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    seed_database()