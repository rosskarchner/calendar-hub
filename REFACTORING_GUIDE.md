# Calendar Hub - Refactoring Guide

## Branch Purpose
Branch name: `claude/refactor-remove-aws-docker-011CUpsLbRBc8zFTeTZbVAHN`

**Goal**: Remove Docker dependency from development and deployment workflows, simplify AWS configuration, and make the codebase more maintainable for local development.

## Current State vs. Target State

### Current Architecture
```
Development:
├── Docker container with Python environment
├── Docker Compose for local AWS services (LocalStack)
├── Requires Docker Desktop/daemon running
└── Isolated from host system

Production:
├── EC2 instance with systemd service
├── Real AWS services (DynamoDB, SES, KMS, Secrets Manager)
└── gunicorn + nginx
```

### Target Architecture
```
Development:
├── Python virtual environment (venv) on host
├── Local file-based storage for development submissions
├── AWS services optional (mock/stub for testing)
└── No Docker required

Production:
├── EC2 instance unchanged
├── Real AWS services unchanged
└── gunicorn + nginx unchanged
```

## Refactoring Areas

### 1. Remove Docker from Development (PRIORITY: HIGH)

**Current State**: Developers required to run Docker
**Target**: Pure Python venv-based development

**Changes Needed**:
- Delete `Dockerfile` (if exists in previous commits)
- Delete `docker-compose.yml` (if exists)
- Delete `.dockerignore` (if exists)
- Update `dev.sh` to use venv instead of Docker
- Update README.md with venv setup instructions
- Add `venv/` to `.gitignore` (already done)

**Files to Update**:
```
dev.sh                          # Use venv, not docker
README.md                       # Add setup instructions without Docker
DEPLOYMENT.md                   # Remove Docker references
```

### 2. Simplify Local Development Configuration (PRIORITY: HIGH)

**Current**: Requires full AWS configuration for development

**Target**: Support local development with file-based or mock storage

**Option A: Environment-Based Mocking**
```python
# In config.py
class DevelopmentConfig(Config):
    DEBUG = True
    USE_MOCK_AWS = True  # NEW: Use mock services instead of boto3

# In services/aws_clients.py
if Config.USE_MOCK_AWS:
    # Return mock objects instead of real boto3 clients
    return MockDynamoDBTable()
    return MockSESClient()
    # etc.
```

**Option B: File-Based Storage (Simpler)**
```python
# For local development, store submissions in JSON files
# services/dynamodb.py
def __init__(self, table_name, use_file_storage=False):
    self.use_file_storage = use_file_storage
    self.storage_path = f"storage/{table_name}.json"
```

**Benefits**:
- No AWS credentials needed for development
- Faster local iteration
- No DynamoDB/SES costs
- Can still test real AWS when needed

**Files to Create**:
- `services/mock_aws.py` - Mock AWS service implementations
- `storage/` directory - Local JSON storage for dev

**Files to Modify**:
- `services/aws_clients.py` - Add factory for mock vs. real clients
- `config.py` - Add `USE_MOCK_AWS` flag
- `services/dynamodb.py` - Support file-based storage
- `services/ses.py` - Mock email sending (log to stdout/file)
- `services/sesv2.py` - Mock newsletter operations
- `services/kms.py` - Local HMAC instead of KMS for dev

### 3. Simplify Secrets Management (PRIORITY: MEDIUM)

**Current**: All secrets in Secrets Manager in production, only some in .env for dev

**Target**: Local development secrets in .env or local files, production unchanged

**Changes**:
```python
# In config.py
class DevelopmentConfig(Config):
    # Use .env values directly instead of Secrets Manager
    CSRF_SECRET = os.environ.get('CSRF_SECRET', 'dev-secret-key')
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
    NEWSLETTER_CSRF_SECRET = os.environ.get('NEWSLETTER_CSRF_SECRET', 'dev-secret-key')
    CONFIRMATION_KEY_ID = os.environ.get('CONFIRMATION_KEY_ID', 'local-mock-key')

class ProductionConfig(Config):
    # Production still uses Secrets Manager (unchanged)
```

**Files to Update**:
- `config.py` - Add fallback to .env
- `services/aws_clients.py` - Modify `get_secret()` to use config fallback in dev
- `.env.example` - Add optional fields for local development

### 4. Decouple KMS from Newsletter Links (PRIORITY: MEDIUM)

**Current**: Uses AWS KMS HMAC for newsletter confirmation signatures

**Target**: Use local HMAC for development, KMS in production

**Rationale**:
- KMS is slower and costs money
- HMAC locally is instant and free
- Can still use KMS in production for additional security

**Changes**:
```python
# In services/kms.py
class KMSService:
    def __init__(self, key_id, use_local_hmac=False):
        self.use_local_hmac = use_local_hmac
        self.key_id = key_id
    
    def generate_confirmation_signature(self, email, contact_list, topic, timestamp):
        if self.use_local_hmac:
            return self._generate_local_hmac(email, contact_list, topic, timestamp)
        else:
            return self._generate_kms_hmac(email, contact_list, topic, timestamp)
```

**Files to Create/Modify**:
- `services/kms.py` - Add local HMAC fallback
- `config.py` - Add `USE_LOCAL_HMAC` flag

### 5. Simplify Service Dependencies (PRIORITY: LOW)

**Current**: All services require AWS client initialization

**Target**: Services gracefully degrade in mock mode

**Changes**:
```python
# In services/dynamodb.py
class SubmissionsService:
    def __init__(self, table_name, client=None):
        self.table_name = table_name
        self._client = client or AWSClients.get_dynamodb()
    
    @property
    def table(self):
        if isinstance(self._client, MockDynamoDB):
            return self._client  # Already a mock object
        return self._client.Table(self.table_name)
```

### 6. Update Documentation (PRIORITY: MEDIUM)

**Files to Update**:

1. **README.md**
   - Remove Docker setup instructions
   - Add venv setup instructions
   - Clarify dev vs. production setup

2. **DEPLOYMENT.md**
   - Remove Docker references
   - Keep EC2 deployment guide as-is
   - Add local development section

3. **dev.sh**
   - Replace Docker commands with venv commands
   - Example:
     ```bash
     # OLD: docker-compose up
     # NEW:
     python -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     export FLASK_ENV=development
     python app.py
     ```

4. **New file: DEVELOPMENT.md**
   - How to set up local development environment
   - Mock AWS behavior explanation
   - Testing without AWS credentials
   - Debugging tips

### 7. Testing & Validation (PRIORITY: HIGH)

**Add Test Coverage**:
- Test mock AWS services work correctly
- Test file-based storage operations
- Test local HMAC signatures
- Test that services can switch between mock and real

**Test Files to Create**:
```
tests/
├── test_mock_dynamodb.py
├── test_mock_ses.py
├── test_mock_kms.py
├── test_local_hmac.py
└── test_config.py
```

## Implementation Plan

### Phase 1: Prepare Mock Services (Week 1)
- [ ] Create `services/mock_aws.py` with mock implementations
- [ ] Create `services/local_hmac.py` for local HMAC
- [ ] Update `config.py` to add feature flags
- [ ] Update `.env.example` with mock-friendly defaults

### Phase 2: Update AWS Clients (Week 1)
- [ ] Modify `aws_clients.py` to return mock objects in dev
- [ ] Modify service classes to work with mock objects
- [ ] Test mock implementations with routes

### Phase 3: Remove Docker References (Week 1)
- [ ] Delete Docker files (already done?)
- [ ] Update `dev.sh` script
- [ ] Update README.md
- [ ] Update DEPLOYMENT.md

### Phase 4: Add Tests (Week 2)
- [ ] Create test suite for mock services
- [ ] Create integration tests
- [ ] Test local HMAC signatures
- [ ] Test file-based storage

### Phase 5: Documentation (Week 2)
- [ ] Create DEVELOPMENT.md
- [ ] Update all README files
- [ ] Add troubleshooting guide
- [ ] Document environment variables

## Migration Checklist

- [ ] All Docker files removed
- [ ] dev.sh uses venv, not Docker
- [ ] Mock AWS services implemented
- [ ] Local HMAC signatures working
- [ ] File-based storage for local dev
- [ ] Tests pass with mock services
- [ ] README updated with venv instructions
- [ ] DEVELOPMENT.md created
- [ ] DEPLOYMENT.md updated
- [ ] .env.example includes dev-friendly defaults
- [ ] All services gracefully degrade in mock mode
- [ ] Production deployment unchanged
- [ ] Git history cleaned up (no Docker commits)

## Breaking Changes

None - Production deployment remains unchanged. This is purely a local development improvement.

## Backwards Compatibility

The refactoring should maintain backwards compatibility:
- Production code unchanged
- AWS service calls still work the same way
- Environment variables still recognized
- Configuration still loads from Secrets Manager in production

## Testing Strategy

### Local Development Testing
```bash
# Test with mock services
FLASK_ENV=development
USE_MOCK_AWS=true
USE_LOCAL_HMAC=true
python app.py

# Test event submission flow (no AWS needed)
# Test newsletter signup flow (no AWS needed)
```

### Production Testing
```bash
# Test with real AWS services
FLASK_ENV=production
# (No feature flags needed, always uses real services)
```

## Performance Impact

- **Development**: Much faster iteration, no Docker startup time
- **Production**: No change (uses real AWS services as before)

## Cost Impact

- **Development**: Reduced AWS calls during testing
- **Production**: No change

## Rollback Plan

If issues arise, the changes can be safely reverted:
- Restore Docker files from git history (if needed)
- Revert `config.py` to only support real AWS
- Revert service classes to always use boto3
- Keep documentation updates (non-breaking)

## Success Criteria

1. Developers can run the application without Docker
2. Developers can test without AWS credentials
3. Local development is faster than Docker-based setup
4. Production deployment is unaffected
5. All tests pass with mock services
6. All tests pass with real AWS services

## Questions for Clarification

1. Should we keep CloudFormation setup intact for production?
   - Answer: Yes, keep as-is

2. Should we support both mock and real AWS in same environment?
   - Answer: Yes, use environment flags to switch

3. Should we remove DynamoDB entirely for local dev?
   - Answer: No, just use file-based mock instead

4. Should we add a way to test with real AWS locally?
   - Answer: Yes, allow override of mock with real services if needed

5. Should GitHub PR creation be mocked for local dev?
   - Answer: Yes, log what would be created instead of actual PR
