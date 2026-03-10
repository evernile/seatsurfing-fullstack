diff --git a/c:\Users\A1136apulia\Downloads\seatsurfing-main\seatsurfing-main\server_py/app/core/security.py b/c:\Users\A1136apulia\Downloads\seatsurfing-main\seatsurfing-main\server_py/app/core/security.py
--- a/c:\Users\A1136apulia\Downloads\seatsurfing-main\seatsurfing-main\server_py/app/core/security.py
+++ b/c:\Users\A1136apulia\Downloads\seatsurfing-main\seatsurfing-main\server_py/app/core/security.py
@@ -1,15 +1,32 @@
-from fastapi import Depends, HTTPException
-from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
-from sqlalchemy.orm import Session
-
-from app.core.database import get_db
-from app.core.jwt import decode_access_token
-from app.models import User
-
-bearer_scheme = HTTPBearer(auto_error=False)
+from fastapi import Depends, HTTPException
+from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
+from sqlalchemy.orm import Session
+import bcrypt
+
+from app.core.database import get_db
+from app.core.jwt import decode_access_token
+from app.models import User
 
-def get_current_user(
-    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
-    db: Session = Depends(get_db),
-) -> User:
+bearer_scheme = HTTPBearer(auto_error=False)
+
+def hash_password(password: str) -> str:
+    if not password:
+        raise ValueError("Password cannot be empty")
+    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
+
+def verify_password(password: str, hashed_password: str) -> bool:
+    if not password or not hashed_password:
+        return False
+    try:
+        return bcrypt.checkpw(
+            password.encode("utf-8"),
+            hashed_password.encode("utf-8"),
+        )
+    except ValueError:
+        return False
+
+def get_current_user(
+    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
+    db: Session = Depends(get_db),
+) -> User:
     if credentials is None:
@@ -28,2 +45,2 @@
 
-    return user
\ No newline at end of file
+    return user
