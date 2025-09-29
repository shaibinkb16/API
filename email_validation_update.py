# Add this function to your login2.py file to validate emails against authorized_emails collection

def is_email_authorized(email: str) -> tuple[bool, str]:
    """
    Check if an email is in the authorized_emails collection
    Returns: (is_authorized: bool, name: str)
    """
    try:
        # Access the authorized_emails collection
        authorized_emails_collection = db["authorized_emails"]

        result = authorized_emails_collection.find_one({"email": email.lower()})
        if result:
            return True, result["name"]
        else:
            return False, ""
    except Exception as e:
        print(f"Error checking email authorization: {e}")
        return False, ""


# Updated /auth endpoint with email validation
# Replace your existing @app.post("/auth", response_model=Token) function with this:

@app.post("/auth", response_model=Token)
async def authenticate_user(email: Annotated[str, Form()]):
    # First, check if email is authorized
    is_authorized, name = is_email_authorized(email)
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email '{email}' is not authorized to access this training. Please contact your administrator."
        )

    # Proceed with existing logic if email is authorized
    user = users_collection.find_one({"email": email})
    if user:
        login_count = user["login_count"] + 1
        users_collection.update_one({"email": email}, {"$set": {"login_count": login_count}})
    else:
        user_id = str(uuid.uuid4())
        user = {
            "_id": user_id,
            "email": email,
            "name": name,  # Add the name from authorized_emails
            "completed_slides": 0,
            "total_login_time": 0.0,
            "login_count": 1,
            "status": "in_progress",
            "start_time": None
        }
        users_collection.insert_one(user)
        login_count = 1

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "email": email, "login_count": login_count}


# Optional: Add an endpoint to check email authorization status
@app.get("/check-email/{email}")
async def check_email_authorization(email: str):
    """Check if an email is authorized (for admin purposes)"""
    is_authorized, name = is_email_authorized(email)
    return {
        "email": email,
        "is_authorized": is_authorized,
        "name": name if is_authorized else None
    }