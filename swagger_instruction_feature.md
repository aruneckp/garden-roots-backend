SWAGGER INSTRUCTION FEATURE
TASK: Implement Google OAuth Login in Swagger UI with Automatic Admin Role Verification
REQUIREMENT:
All users should be able to access Swagger docs, login with their Google account, and the system should automatically check if they have admin role in the database. If they are admin, grant access to Swagger UI. If not admin, deny access. No manual token handling - users just login with Google like a normal OAuth flow.

CURRENT SYSTEM:
FastAPI backend with Oracle database
Google OAuth already implemented for customers at /api/v1/auth/google
JWT tokens for authentication
User model with role field (can be "admin" or "customer")
Existing auth utilities in utils/auth.py
Current Swagger docs are disabled in production
EXPECTED USER EXPERIENCE:
User goes to /docs (Swagger UI)
User clicks "Authorize" button in Swagger
User selects "Google OAuth" and logs in with their Google account
System automatically verifies if this user has role: "admin" in database
If admin: User gets full access to Swagger UI and can test all endpoints
If not admin: User sees clear error message "Access denied. Admin role required."
No manual token copying, no Bearer token management - just normal OAuth login






live_607bda1b6c44490af9d8fe587a48d316cee0b8954147a7253e7009ca216b39b1

qeVkWr9ICJwWbIpxNyBvd1WDbZBpQrwfJdLOqJqgWE3vMUEYZjLIzqhVk0GhIZ6d

qeVkWr9ICJwWbIpxNyBvd1WDbZBpQrwfJdLOqJqgWE3vMUEYZjLIzqhVk0GhIZ6d