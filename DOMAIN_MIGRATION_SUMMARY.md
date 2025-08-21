# Domain Migration Summary

## Overview
This document summarizes the changes made to migrate the application from `boomai.onrender.com` to `storyboom.ai` while maintaining support for both local development and production deployment.

## Changes Made

### 1. Render Configuration (`render.yaml`)
- Updated `BASE_URL` from `https://boomai.onrender.com` to `https://storyboom.ai`
- This ensures all production deployments use the new domain

### 2. Application Configuration (`config.py`)
- Added `BASE_URL` configuration support
- Defaults to local development URL: `http://127.0.0.1:10000`
- Can be overridden by environment variables

### 3. Email Verification Links (`app/routes/auth.py`)
- Updated default `BASE_URL` from `https://boomai.onrender.com` to `https://storyboom.ai`
- Now uses configuration system for better flexibility
- Verification links will point to the correct domain based on environment

### 4. Client Interview Links (`app/routes/main.py`)
- Updated to use configuration system for `BASE_URL`
- Maintains local development support
- Production links will use `https://storyboom.ai`

### 5. CORS Configuration (`app/__init__.py`)
- Added `https://storyboom.ai` to allowed origins
- Kept `https://boomai.onrender.com` for backward compatibility
- Maintains local development origins
- Supports both domains during transition period

### 6. Documentation Updates
- Updated `DEPLOYMENT_TROUBLESHOOTING.md` with new domain references
- Updated `README.md` with configuration instructions
- Created `env.example` for local development setup

## Configuration Priority

The application now follows this priority for `BASE_URL`:

1. **Environment Variable**: `BASE_URL` environment variable (highest priority)
2. **App Config**: Flask app configuration
3. **Default**: Local development URL (`http://127.0.0.1:10000`)

## Environment Setup

### Local Development
```bash
# Copy the example file
cp env.example .env

# Edit .env and set your local BASE_URL
BASE_URL=http://127.0.0.1:10000
```

### Production (Render)
- `BASE_URL` is automatically set to `https://storyboom.ai`
- No additional configuration needed

### Custom Domain
```bash
# Set your preferred domain
BASE_URL=https://yourdomain.com
```

## What This Affects

### Email Verification
- New signup verification emails will use the configured `BASE_URL`
- Links will point to the correct domain

### Client Interview Links
- Generated client interview links will use the configured `BASE_URL`
- Works for both local development and production

### CORS Support
- Application accepts requests from both domains
- Maintains backward compatibility
- Supports local development

## Testing

### Local Development
1. Set `BASE_URL=http://127.0.0.1:10000` in your `.env` file
2. Start the application: `python run.py`
3. Test signup and verification
4. Test client interview link generation

### Production
1. Deploy to Render (automatically sets `BASE_URL=https://storyboom.ai`)
2. Test signup and verification
3. Test client interview link generation
4. Verify all links point to `storyboom.ai`

## Rollback Plan

If issues arise, you can:
1. Temporarily set `BASE_URL=https://boomai.onrender.com` in Render
2. The application will continue to work with the old domain
3. CORS is already configured to support both domains

## Next Steps

1. **Deploy to Render** - The new configuration will automatically use `storyboom.ai`
2. **Test thoroughly** - Verify all email verification and client links work
3. **Monitor logs** - Check for any domain-related issues
4. **Update DNS** - Ensure `storyboom.ai` points to your Render deployment
5. **Remove old domain** - Once confirmed working, remove `boomai.onrender.com` from CORS origins

## Benefits

- **Flexible Configuration**: Works in any environment
- **Backward Compatibility**: Supports both domains during transition
- **Local Development**: Easy local testing with configurable URLs
- **Production Ready**: Automatic domain configuration on Render
- **Future Proof**: Easy to change domains in the future 