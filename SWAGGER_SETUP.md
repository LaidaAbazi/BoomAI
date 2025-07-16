# StoryBoom AI API - Swagger Documentation Setup

## Overview

This document explains how to access and use the Swagger/OpenAPI documentation for the StoryBoom AI API.

## What is Swagger?

Swagger (OpenAPI) is a tool that automatically generates interactive API documentation from your Flask routes. It provides:

- **Interactive API Explorer**: Test endpoints directly from the browser
- **Automatic Documentation**: Generates docs from your code
- **Request/Response Examples**: Shows expected data formats
- **Authentication Support**: Handles session-based auth

## Accessing the Swagger UI

### Local Development
1. Start your Flask application:
   ```bash
   python run.py
   ```

2. Open your browser and go to:
   ```
   http://localhost:10000/apidocs/
   ```

### Production (When Deployed)
Replace `localhost:10000` with your production domain:
```
https://your-domain.com/apidocs/
```

## API Endpoints Overview

### Authentication Endpoints
- `POST /api/signup` - Register a new user
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/user` - Get current user info

### Case Studies
- `GET /api/case_studies` - Get all case studies
- `GET /api/case_studies/{id}` - Get specific case study
- `POST /api/generate_full_case_study` - Generate complete case study
- `POST /api/save_final_summary` - Save final summary

### Labels
- `GET /api/labels` - Get all labels
- `POST /api/labels` - Create new label
- `PATCH /api/labels/{id}` - Rename label
- `DELETE /api/labels/{id}` - Delete label

### Feedback
- `POST /api/feedback/start` - Start feedback session
- `POST /api/feedback/submit` - Submit feedback
- `GET /api/feedback/history` - Get feedback history
- `POST /api/feedback/analyze` - Analyze all feedback

### Interviews
- `POST /api/save_provider_summary` - Save provider interview
- `POST /api/save_client_transcript` - Save client transcript
- `POST /api/generate_client_summary` - Generate client summary

### Media Generation
- `POST /api/generate_video` - Generate HeyGen video
- `GET /api/video_status/{id}` - Check video status
- `POST /api/generate_pictory_video` - Generate Pictory video
- `POST /api/generate_podcast` - Generate podcast

### Metadata
- `POST /api/metadata/analyze` - Analyze case study metadata
- `POST /api/metadata/regenerate/{id}` - Regenerate metadata
- `GET /api/sentiment_chart/{id}` - Get sentiment chart

## Authentication

Most endpoints require authentication. The API uses session-based authentication:

1. **Login First**: Use `POST /api/login` with your email and password
2. **Session Cookie**: The server will set a session cookie
3. **Automatic Auth**: Subsequent requests will automatically include the session

### Example Login Request:
```json
{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

## Testing Endpoints

### Using Swagger UI
1. Go to `/apidocs/`
2. Click on any endpoint
3. Click "Try it out"
4. Fill in the required parameters
5. Click "Execute"

### Using cURL
```bash
# Login
curl -X POST "http://localhost:10000/api/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}' \
  -c cookies.txt

# Get case studies (using session cookie)
curl -X GET "http://localhost:10000/api/case_studies" \
  -b cookies.txt
```

### Using JavaScript/Frontend
```javascript
// Login
const loginResponse = await fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'your-email@example.com',
    password: 'your-password'
  }),
  credentials: 'include' // Important for session cookies
});

// Get case studies
const caseStudiesResponse = await fetch('/api/case_studies', {
  credentials: 'include' // Include session cookies
});
```

## IP Access for Production

For production access, contact support to whitelist your IP address:
- **Support Email**: storyboomai@gmail.com
- **Your IP**: 91.99.166.133 (as mentioned in your request)

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (not logged in)
- `404` - Not Found
- `409` - Conflict (e.g., user already exists)
- `423` - Locked (account temporarily locked)
- `500` - Internal Server Error

Error responses include a message:
```json
{
  "error": "Error description",
  "message": "User-friendly error message"
}
```

## Rate Limiting

To prevent abuse, API calls are rate-limited. Contact support if you need higher limits.

## Development vs Production

### Development (localhost:10000)
- Debug mode enabled
- Detailed error messages
- No rate limiting
- CORS enabled for all origins

### Production
- Debug mode disabled
- Generic error messages
- Rate limiting enabled
- CORS restricted to specific domains

## Adding New Endpoints

To add Swagger documentation to new endpoints:

1. Import the decorator:
   ```python
   from flasgger import swag_from
   ```

2. Add the decorator to your route:
   ```python
   @bp.route('/your-endpoint', methods=['POST'])
   @swag_from({
       'tags': ['Your Tag'],
       'summary': 'Brief description',
       'description': 'Detailed description',
       'requestBody': {
           'required': True,
           'content': {
               'application/json': {
                   'schema': {
                       'type': 'object',
                       'properties': {
                           'field': {'type': 'string'}
                       }
                   }
               }
           }
       },
       'responses': {
           200: {'description': 'Success'},
           400: {'description': 'Bad Request'}
       }
   })
   def your_endpoint():
       # Your code here
       pass
   ```

## Troubleshooting

### Swagger UI Not Loading
- Check if Flask app is running
- Verify the URL: `http://localhost:10000/apidocs/`
- Check browser console for errors

### Authentication Issues
- Make sure you're logged in first
- Check if session cookies are enabled
- Try logging out and logging back in

### CORS Issues (Frontend)
- Ensure `credentials: 'include'` is set in fetch requests
- Check if your domain is whitelisted in production

## Support

For technical support or questions about the API:
- **Email**: storyboomai@gmail.com
- **Documentation**: `/apidocs/` (when server is running)

## Next Steps

1. **Test the API**: Use the Swagger UI to explore and test endpoints
2. **Integrate with Frontend**: Use the provided examples to integrate with your frontend
3. **Production Setup**: Contact support for production access and IP whitelisting
4. **Customization**: Modify the Swagger configuration in `app/__init__.py` as needed 