# Deployment Guide for StoryBoom AI

## Deploying to Render

### Prerequisites
1. A Render account (free tier available)
2. Your API keys for external services
3. Git repository with your code

### Step 1: Prepare Your Repository
Ensure your repository contains:
- `render.yaml` - Render configuration
- `requirements.txt` - Python dependencies
- `gunicorn.conf.py` - Gunicorn configuration
- `run.py` - Application entry point
- `Procfile` - Alternative deployment configuration

### Step 2: Set Up on Render

1. **Connect Repository**
   - Go to [render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New +" and select "Blueprint"
   - Connect your GitHub repository

2. **Deploy with Blueprint**
   - Render will automatically detect the `render.yaml` file
   - Click "Apply" to create both the web service and database
   - This will create:
     - A PostgreSQL database
     - A web service running your Flask app

### Step 3: Configure Environment Variables

After deployment, go to your web service dashboard and set these environment variables:

#### Required Variables (set these in Render dashboard):
- `OPENAI_API_KEY` - Your OpenAI API key
- `HEYGEN_API_KEY` - Your HeyGen API key
- `PICTORY_CLIENT_ID` - Your Pictory client ID
- `PICTORY_CLIENT_SECRET` - Your Pictory client secret
- `PICTORY_USER_ID` - Your Pictory user ID
- `WONDERCRAFT_API_KEY` - Your Wondercraft API key

#### Auto-generated Variables:
- `SECRET_KEY` - Automatically generated by Render
- `JWT_SECRET_KEY` - Automatically generated by Render
- `DATABASE_URL` - Automatically set from the database service

### Step 4: Database Migration

After the first deployment, you'll need to run database migrations:

1. Go to your web service dashboard
2. Click on "Shell" tab
3. Run the following commands:
   ```bash
   flask db upgrade
   ```

### Step 5: Verify Deployment

1. Check your service URL (provided by Render)
2. Test the API endpoints
3. Check the logs for any errors

### Environment Variables Reference

| Variable | Description | Required | Auto-generated |
|----------|-------------|----------|----------------|
| `SECRET_KEY` | Flask secret key | Yes | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes | No |
| `HEYGEN_API_KEY` | HeyGen API key | Yes | No |
| `PICTORY_CLIENT_ID` | Pictory client ID | Yes | No |
| `PICTORY_CLIENT_SECRET` | Pictory client secret | Yes | No |
| `PICTORY_USER_ID` | Pictory user ID | Yes | No |
| `WONDERCRAFT_API_KEY` | Wondercraft API key | Yes | No |
| `FLASK_ENV` | Environment (production) | No | Yes |
| `PYTHON_VERSION` | Python version | No | Yes |

### Troubleshooting

#### Common Issues:

1. **Build Failures**
   - Check the build logs in Render dashboard
   - Ensure all dependencies are in `requirements.txt`

2. **Database Connection Issues**
   - Verify `DATABASE_URL` is set correctly
   - Check if database service is running

3. **API Key Errors**
   - Ensure all required API keys are set in environment variables
   - Check the application logs for specific error messages

4. **Migration Issues**
   - Run `flask db upgrade` in the shell
   - Check if database tables exist

#### Logs and Monitoring:
- View logs in the Render dashboard
- Monitor service health and performance
- Set up alerts for downtime

### Alternative Deployment Options

#### Heroku
Use the `Procfile` for Heroku deployment:
```bash
heroku create your-app-name
git push heroku main
```

#### Railway
Railway can also use the `render.yaml` configuration with minimal changes.

### Security Notes

1. **Never commit API keys** to your repository
2. **Use environment variables** for all sensitive data
3. **Enable HTTPS** (handled automatically by Render)
4. **Regular security updates** for dependencies

### Cost Optimization

- Free tier includes:
  - 750 hours/month for web services
  - 1GB PostgreSQL database
  - Automatic sleep after 15 minutes of inactivity

- For production use, consider upgrading to paid plans for:
  - Always-on services
  - Larger databases
  - Better performance 