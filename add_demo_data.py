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

def generate_demo_users():
    demo_users = []

    # Sample email domains and names
    first_names = ["John", "Jane", "Mike", "Sarah", "David", "Emma", "Chris", "Lisa", "Alex", "Maria",
                   "Tom", "Anna", "Steve", "Kate", "Mark", "Amy", "Paul", "Nina", "Jake", "Lucy"]
    last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Moore", "Taylor", "Anderson", "Thomas",
                  "Jackson", "White", "Harris", "Martin", "Garcia", "Rodriguez", "Lewis", "Lee", "Walker", "Hall"]
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com"]

    for i in range(20):
        first_name = first_names[i]
        last_name = last_names[i]
        domain = random.choice(domains)
        email = f"{first_name.lower()}.{last_name.lower()}@{domain}"

        # Random progress data
        completed_slides = random.randint(0, 15)  # 0-15 slides completed
        login_count = random.randint(1, 10)
        total_login_time = round(random.uniform(5.0, 120.0), 2)  # 5 minutes to 2 hours

        # Random status based on progress
        if completed_slides == 0:
            status = "in_progress"
        elif completed_slides >= 12:
            status = "completed"
        else:
            status = random.choice(["in_progress", "in_progress", "completed"])

        # Random timestamps
        start_time = datetime.utcnow() - timedelta(days=random.randint(1, 30))
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

def insert_demo_data():
    print("Generating demo users...")
    demo_users = generate_demo_users()

    print("Connecting to MongoDB...")
    try:
        client.admin.command("ping")
        print("Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print("MongoDB connection failed:", e)
        return

    # Clear existing demo data (optional - comment out if you want to keep existing data)
    print("Clearing existing users...")
    users_collection.delete_many({})

    print("Inserting demo users...")
    result = users_collection.insert_many(demo_users)
    print(f"Successfully inserted {len(result.inserted_ids)} demo users!")

    # Display summary
    print("\nDemo Data Summary:")
    print(f"Total users: {users_collection.count_documents({})}")
    print(f"Completed: {users_collection.count_documents({'status': 'completed'})}")
    print(f"In Progress: {users_collection.count_documents({'status': 'in_progress'})}")

    print("\nSample users:")
    for user in users_collection.find().limit(5):
        print(f"{user['email']} - Slides: {user['completed_slides']} - Status: {user['status']}")

if __name__ == "__main__":
    insert_demo_data()