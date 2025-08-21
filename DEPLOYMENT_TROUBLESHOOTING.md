# Deployment Troubleshooting Guide

## 500 Error on Signup - Common Issues and Solutions

### 1. Database Connection Issues

**Symptoms:**
- 500 error on signup
- "Something went wrong on our end" message
- Database connection errors in logs

**Solutions:**

#### Check Database Connection
```bash
# Test database connection locally
python test_db_connection.py

# Check health endpoint
curl https://storyboom.ai/health
```

#### Verify Environment Variables
Ensure these environment variables are set in Render:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Application secret key
- `JWT_SECRET_KEY` - JWT secret key
- `BASE_URL` - Application base URL (https://storyboom.ai)

#### Database Initialization
The app now automatically:
- Tests database connection on startup
- Creates tables if they don't exist
- Provides detailed error logging

### 2. PostgreSQL URL Format Issue

**Problem:** Render provides PostgreSQL URLs in `postgres://` format, but SQLAlchemy expects `postgresql://`

**Solution:** The app now automatically converts the URL format in `app/__init__.py`

### 3. Missing Dependencies

**Problem:** Some required packages might be missing

**Solution:** Updated `requirements.txt` with specific versions

### 4. Database Migration Issues

**Problem:** Database schema might be out of sync

**Solution:**
```bash
# Run migrations manually if needed
flask db upgrade
```

### 5. Debugging Steps

#### 1. Check Application Logs
In Render dashboard, check the logs for:
- Database connection errors
- Import errors
- Missing environment variables

#### 2. Test Health Endpoint
```bash
curl https://storyboom.ai/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "healthy",
  "environment": {
    "flask_env": "production",
    "database_url_set": true,
    "secret_key_set": true
  }
}
```

#### 3. Test Database Connection
```bash
curl https://storyboom.ai/api/health
```

#### 4. Check Database Tables
If database is unhealthy, the issue is likely:
- Missing environment variables
- Incorrect database URL
- Database permissions
- Network connectivity

### 6. Render-Specific Issues

#### Free Tier Limitations
- Database connections might be limited
- Cold starts can cause delays
- Memory constraints

#### Solutions:
1. **Upgrade to paid plan** for better performance
2. **Add connection pooling** for database efficiency
3. **Implement retry logic** for database operations

### 7. Code Changes Made

#### Enhanced Error Handling
- Added comprehensive logging
- Better database connection testing
- Graceful fallbacks for email sending
- Detailed error messages

#### Database Initialization
- Automatic table creation
- Connection testing on startup
- Better PostgreSQL URL handling

#### Health Monitoring
- Added `/health` and `/api/health` endpoints
- Database status monitoring
- Environment variable checking

### 8. Testing Locally

```bash
# Test database connection
python test_db_connection.py

# Initialize database
python init_db.py

# Run the application
python run.py
```

### 9. Common Error Messages

#### "Database connection failed"
- Check `DATABASE_URL` environment variable
- Verify database is running
- Check network connectivity

#### "Table does not exist"
- Run database initialization
- Check migration status
- Verify database permissions

#### "Email sending failed"
- This is non-critical - signup continues
- Check email configuration
- Verify SMTP settings

### 10. Next Steps

1. **Deploy the updated code** to Render
2. **Check the health endpoint** after deployment
3. **Monitor logs** for any remaining issues
4. **Test signup functionality** with a new user

### 11. Contact Support

If issues persist:
1. Check Render status page
2. Review application logs
3. Test with the provided debugging tools
4. Contact Render support if database issues continue 