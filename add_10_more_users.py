from pymongo import MongoClient
import uuid
import random
from datetime import datetime, timedelta
import os

# MongoDB Atlas Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://shaibinkb16_db_user:Shaibin@cluster0.rpxtsc4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["posh"]
users_collection = db["users"]

def generate_additional_users():
    demo_users = []

    # Additional names for the 10 new users
    additional_users = [
        ("Oliver", "Carter"), ("Isabella", "Mitchell"), ("William", "Perez"),
        ("Sophia", "Roberts"), ("James", "Turner"), ("Charlotte", "Phillips"),
        ("Benjamin", "Campbell"), ("Amelia", "Parker"), ("Lucas", "Evans"),
        ("Harper", "Edwards")
    ]

    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com", "edu.org"]

    for first_name, last_name in additional_users:
        domain = random.choice(domains)
        email = f"{first_name.lower()}.{last_name.lower()}@{domain}"

        # Random progress data
        completed_slides = random.randint(0, 15)  # 0-15 slides completed
        login_count = random.randint(1, 12)
        total_login_time = round(random.uniform(3.0, 150.0), 2)  # 3 minutes to 2.5 hours

        # Random status based on progress
        if completed_slides == 0:
            status = "in_progress"
        elif completed_slides >= 13:
            status = "completed"
        else:
            status = random.choice(["in_progress", "in_progress", "completed"])

        # Random timestamps
        start_time = datetime.now() - timedelta(days=random.randint(1, 45))
        end_time = start_time + timedelta(minutes=total_login_time) if status == "completed" else None
        finished_at = end_time if status == "completed" else None

        user = {
            "_id": str(uuid.uuid4()),
            "email": email,
            "completed_slides": completed_slides,
            "total_login_time": total_login_time,
            "login_count": login_count,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "finished_at": finished_at
        }

        demo_users.append(user)

    return demo_users

def add_10_more_users():
    print("Generating 10 additional demo users...")
    demo_users = generate_additional_users()

    print("Connecting to MongoDB...")
    try:
        client.admin.command("ping")
        print("Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print("MongoDB connection failed:", e)
        return

    print("Getting current user count...")
    current_count = users_collection.count_documents({})
    print(f"Current users in database: {current_count}")

    print("Inserting 10 additional demo users...")
    result = users_collection.insert_many(demo_users)
    print(f"Successfully inserted {len(result.inserted_ids)} additional demo users!")

    # Display updated summary
    print("\nUpdated Demo Data Summary:")
    total_users = users_collection.count_documents({})
    completed_users = users_collection.count_documents({'status': 'completed'})
    in_progress_users = users_collection.count_documents({'status': 'in_progress'})

    print(f"Total users: {total_users}")
    print(f"Completed: {completed_users}")
    print(f"In Progress: {in_progress_users}")

    print("\nNew users added:")
    for user in demo_users:
        print(f"{user['email']} - Slides: {user['completed_slides']} - Status: {user['status']}")

if __name__ == "__main__":
    add_10_more_users()