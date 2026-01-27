from app.core.security import verify_password

password = "Admin123"
hashed = "$2b$12$C9D1E0F8xYF4n9kRZQyNFe7o8oY4z8xE2q1yQ6z2F0Z5W9x2Wqk0a"

print(verify_password(password, hashed))
