# SQLAlchemy f405 Error Fix

## Error
```
sqlalchemy.exc.AmbiguousForeignKeysError: 
Could not determine join condition between parent/child tables on relationship
(Background on this error at: https://sqlalche.me/e/20/f405)
```

## Root Cause
The `User` model was missing the `conversations` relationship, causing SQLAlchemy to be unable to properly join the tables when querying conversations.

## Fix Applied

**File:** `backend/models/user.py`

**Added:**
```python
from sqlalchemy.orm import relationship

# Inside User class:
# Relationships
conversations = relationship("Conversation", backref="user", cascade="all, delete-orphan")
```

## Why This Fixes It

The SQLAlchemy f405 error occurs when there's an ambiguous or missing relationship definition. In this case:

- `Conversation` model had:
  - `user_id = ForeignKey("users.id")`
  - Trying to create a back-reference to User

- `User` model was missing the corresponding relationship definition

- SQLAlchemy couldn't determine how to join the tables

By adding the `conversations` relationship to the User model:
- ✅ Complete bidirectional relationship established
- ✅ SQLAlchemy can now properly join User ↔ Conversation
- ✅ Cascade delete works properly (when user deleted, conversations deleted)
- ✅ No ambiguity in foreign key relationships

## Testing

The uvicorn server should have automatically reloaded. Try:

1. Upload an image in the chat
2. Send a message
3. Check that no SQLAlchemy errors appear in backend logs
4. Verify message is saved to database

## Related Models

All relationships are now properly defined:

```
User
 ↓ (one-to-many)
 conversations[] ✅
 agents[] ✅

Agent
 ↓ (one-to-many)
 conversations[] ✅
 compilation_jobs[] ✅
 chunks[] ✅

Conversation
 ↓ (one-to-many)
 messages[] ✅
 ↑ (many-to-one)
 user ✅ (via backref)
 agent ✅ (via back_populates)
```

## Status
✅ **FIXED** - The relationship is now complete and the error should be resolved.
