import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import os


class AuthorizedEmailManager:
    def __init__(self):
        # Use the same MongoDB connection as your login2.py
        self.MONGO_URI = os.getenv(
            "MONGO_URI",
            "mongodb+srv://shaibinkb16_db_user:Shaibin@cluster0.rpxtsc4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        )
        self.client = MongoClient(self.MONGO_URI)
        self.db = self.client["posh"]
        self.authorized_emails_collection = self.db["authorized_emails"]

        # Create unique index on email field to prevent duplicates
        self.authorized_emails_collection.create_index("email", unique=True)

    def test_connection(self):
        """Test MongoDB connection"""
        try:
            self.client.admin.command("ping")
            print("✅ Successfully connected to MongoDB Atlas!")
            return True
        except ConnectionFailure as e:
            print("❌ MongoDB connection failed:", e)
            return False

    def add_emails_from_excel(self, excel_file_path):
        """Read Excel file and add authorized emails to MongoDB"""
        try:
            # Read Excel file
            df = pd.read_excel(excel_file_path)

            # Ensure the required columns exist
            if 'name' not in df.columns or 'email' not in df.columns:
                print("Error: Excel file must contain 'name' and 'email' columns")
                return False

            added_count = 0
            duplicate_count = 0

            for index, row in df.iterrows():
                name = str(row['name']).strip()
                email = str(row['email']).strip().lower()

                # Skip empty rows
                if not name or not email or name == 'nan' or email == 'nan':
                    continue

                try:
                    # Create document to insert
                    email_doc = {
                        "name": name,
                        "email": email,
                        "added_date": pd.Timestamp.now(),
                        "status": "active"
                    }

                    # Insert into MongoDB
                    self.authorized_emails_collection.insert_one(email_doc)
                    added_count += 1
                    print(f"✅ Added: {name} ({email})")

                except DuplicateKeyError:
                    # Email already exists
                    duplicate_count += 1
                    print(f"⚠️  Duplicate email: {email}")
                except Exception as e:
                    print(f"❌ Error adding {email}: {str(e)}")

            print(f"\n📊 Summary:")
            print(f"✅ Successfully added {added_count} new authorized emails")
            if duplicate_count > 0:
                print(f"⚠️  Skipped {duplicate_count} duplicate emails")

            return True

        except FileNotFoundError:
            print(f"❌ Error: Excel file '{excel_file_path}' not found")
            return False
        except Exception as e:
            print(f"❌ Error reading Excel file: {str(e)}")
            return False

    def check_email_authorized(self, email):
        """Check if an email is in the authorized list"""
        try:
            result = self.authorized_emails_collection.find_one({"email": email.lower()})
            if result:
                return True, result["name"]
            else:
                return False, None
        except Exception as e:
            print(f"❌ Error checking email: {str(e)}")
            return False, None

    def get_all_authorized_emails(self):
        """Get all authorized emails"""
        try:
            results = list(self.authorized_emails_collection.find({}, {"_id": 0}))
            return results
        except Exception as e:
            print(f"❌ Error fetching emails: {str(e)}")
            return []

    def remove_authorized_email(self, email):
        """Remove an email from authorized list"""
        try:
            result = self.authorized_emails_collection.delete_one({"email": email.lower()})
            return result.deleted_count > 0
        except Exception as e:
            print(f"❌ Error removing email: {str(e)}")
            return False

    def get_stats(self):
        """Get statistics about authorized emails"""
        try:
            total_count = self.authorized_emails_collection.count_documents({})
            active_count = self.authorized_emails_collection.count_documents({"status": "active"})
            return {
                "total_emails": total_count,
                "active_emails": active_count
            }
        except Exception as e:
            print(f"❌ Error getting stats: {str(e)}")
            return {"total_emails": 0, "active_emails": 0}


def main():
    # Initialize email manager
    email_manager = AuthorizedEmailManager()

    # Test connection
    if not email_manager.test_connection():
        print("❌ Cannot connect to MongoDB. Please check your connection.")
        return

    while True:
        print("\n" + "="*50)
        print("📧 AUTHORIZED EMAIL MANAGER")
        print("="*50)
        print("1. Add emails from Excel file")
        print("2. Check if email is authorized")
        print("3. View all authorized emails")
        print("4. Remove authorized email")
        print("5. View statistics")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == '1':
            excel_path = input("Enter Excel file path: ").strip().strip('"')
            if os.path.exists(excel_path):
                email_manager.add_emails_from_excel(excel_path)
            else:
                print("❌ File not found. Please check the path.")

        elif choice == '2':
            email = input("Enter email to check: ").strip()
            is_authorized, name = email_manager.check_email_authorized(email)
            if is_authorized:
                print(f"✅ Email '{email}' is AUTHORIZED (Name: {name})")
            else:
                print(f"❌ Email '{email}' is NOT AUTHORIZED")

        elif choice == '3':
            emails = email_manager.get_all_authorized_emails()
            if emails:
                print(f"\n📋 Authorized Emails ({len(emails)} total):")
                print("-" * 60)
                for email_doc in emails:
                    print(f"Name: {email_doc['name']} | Email: {email_doc['email']} | Status: {email_doc['status']}")
            else:
                print("📭 No authorized emails found")

        elif choice == '4':
            email = input("Enter email to remove: ").strip()
            if email_manager.remove_authorized_email(email):
                print(f"✅ Email '{email}' removed from authorized list")
            else:
                print(f"❌ Email '{email}' not found or error occurred")

        elif choice == '5':
            stats = email_manager.get_stats()
            print(f"\n📊 Statistics:")
            print(f"Total authorized emails: {stats['total_emails']}")
            print(f"Active emails: {stats['active_emails']}")

        elif choice == '6':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    print("📧 Authorized Email Manager for POSH Training")
    print("Required: pip install pandas openpyxl pymongo")
    print("Excel file should have columns: 'name' and 'email'")
    main()