import sys
import json
import random
import urllib.request
from app import create_app
from app.extensions import db
from app.models import (
    User, Profile, Category, Content, Comment, CommentReaction, ContentReaction,
    Subscription, Wishlist, Share, Notification, ContentReport, content_categories
)

def fetch_external_feed():
    """Fetch live data dynamically from public Dev.to API"""
    url = "https://dev.to/api/articles?per_page=20"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        print(f"Failed to fetch live API data: {e}")
    return []

def seed_database():
    app = create_app()
    with app.app_context():
        print("Fetching live API payload...")
        feed_items = fetch_external_feed()

        if not feed_items:
            print("No items fetched. Aborting database seed.")
            return

        try:
            print("Clearing existing database records...")
            db.session.execute(content_categories.delete())
            CommentReaction.query.delete()
            ContentReaction.query.delete()
            Comment.query.delete()
            Content.query.delete()
            Category.query.delete()
            Profile.query.delete()
            User.query.delete()
            db.session.commit()

            users_map = {}
            categories_map = {}
            contents = []
            comments = []

            # 1. Dynamically build Users and Profiles from API Authors
            print("Seeding Users and Profiles from live author payloads...")
            for item in feed_items:
                author_info = item.get("user", {})
                username = author_info.get("username")
                description = item.get("description")

                if not username or not description:
                    continue

                if username not in users_map:
                    user = User(
                        Username=username,
                        Email=f"{username}@dev.to",
                        Role="Admin" if len(users_map) == 0 else "Member",
                        IsActive=True
                    )
                    user.password_hash = f"hash_{username}"

                    profile = Profile(
                        Bio=author_info.get("summary") or description,
                        ProfileImage=author_info.get("profile_image_90") or "",
                        Interests=", ".join(item.get("tag_list", []))
                    )
                    user.profile = profile
                    db.session.add(user)
                    users_map[username] = user

                # 2. Dynamically build Categories from Article Tags
                for tag in item.get("tag_list", []):
                    tag_name = tag.capitalize()
                    if tag_name not in categories_map:
                        category = Category(
                            Name=tag_name,
                            Description=description,
                            CreatedBy=users_map[username].UserID
                        )
                        db.session.add(category)
                        categories_map[tag_name] = category

            db.session.flush()
            user_list = list(users_map.values())

            # 3. Dynamically build Content from API Articles
            print("Seeding Content items directly from API articles...")
            for item in feed_items:
                author_info = item.get("user", {})
                username = author_info.get("username")
                title = item.get("title")
                description = item.get("description")
                article_url = item.get("canonical_url") or item.get("url")
                thumbnail_url = item.get("cover_image") or ""

                if not username or not title or not description:
                    continue

                content_item = Content(
                    UserID=users_map[username].UserID,
                    Title=title,
                    Description=description,
                    ContentType="Article",
                    ContentURL=article_url,
                    ThumbnailURL=thumbnail_url,
                    Status="Published",
                    IsApproved=True
                )

                for tag in item.get("tag_list", []):
                    tag_name = tag.capitalize()
                    if tag_name in categories_map:
                        content_item.categories.append(categories_map[tag_name])

                db.session.add(content_item)
                contents.append(content_item)

            db.session.flush()

            # 4. Dynamically build Comments using API Descriptions
            print("Seeding Comments dynamically using API excerpts...")
            for content in contents:
                sample_text = content.Description
                comment = Comment(
                    UserID=random.choice(user_list).UserID,
                    ContentID=content.ContentID,
                    Text=sample_text
                )
                db.session.add(comment)
                comments.append(comment)

            db.session.flush()

            # 5. Dynamically seed Reactions adhering to unique constraints
            print("Seeding Reactions...")
            unique_likes = set()
            reaction_choices = ['Like', 'Love', 'Haha', 'Wow']
            
            while len(unique_likes) < min(25, len(contents) * len(user_list)):
                u_id = random.choice(user_list).UserID
                c_id = random.choice(contents).ContentID
                
                if (u_id, c_id) not in unique_likes:
                    unique_likes.add((u_id, c_id))
                    rxn = ContentReaction(
                        UserID=u_id,
                        ContentID=c_id,
                        Reaction=random.choice(reaction_choices)
                    )
                    db.session.add(rxn)

            db.session.commit()
            print("Database populated using dynamic external feed.")

        except Exception as e:
            print(f"Error during seeding: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    seed_database()