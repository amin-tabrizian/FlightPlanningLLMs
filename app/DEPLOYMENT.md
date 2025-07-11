# Flight Planning App - Cloud Deployment Guide

## Prerequisites

Before deploying, ensure you have:
- Your API keys ready (OpenAI, Anthropic)
- Git repository with your code
- Account on your chosen cloud platform

## 🚀 Deployment Options

### 1. Railway (Recommended - Easiest)

**Steps:**
1. Visit [railway.app](https://railway.app) and sign up
2. Connect your GitHub repository
3. Click "Deploy from GitHub repo" and select your repository
4. Railway will auto-detect it's a Python app
5. Add environment variables in Railway dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `FLASK_ENV`: production
6. Deploy! Railway will automatically build and deploy

**Pros:** Easy setup, automatic HTTPS, custom domains, good free tier
**Cost:** Free tier available, then $5/month

### 2. Render

**Steps:**
1. Visit [render.com](https://render.com) and sign up
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render will detect the `render.yaml` configuration
5. Add environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
6. Deploy!

**Pros:** Great free tier, automatic SSL, easy to use
**Cost:** Free tier available (with limitations)

### 3. DigitalOcean App Platform

**Steps:**
1. Visit [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Create new app from GitHub repository
3. Configure as Python app
4. Set build command: `pip install -r requirements.txt`
5. Set run command: `gunicorn --bind 0.0.0.0:$PORT app:app`
6. Add environment variables
7. Deploy!

**Pros:** Reliable, good performance, predictable pricing
**Cost:** Starts at $5/month

### 4. Heroku

**Steps:**
1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Add buildpacks:
   ```bash
   heroku buildpacks:add --index 1 heroku/python
   heroku buildpacks:add --index 2 https://github.com/heroku/heroku-geo-buildpack.git
   ```
5. Set environment variables:
   ```bash
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set ANTHROPIC_API_KEY=your_key
   heroku config:set FLASK_ENV=production
   ```
6. Deploy: `git push heroku main`

**Pros:** Well-established, lots of add-ons
**Cons:** More expensive, limited free tier

### 5. Google Cloud Run (Advanced)

**Steps:**
1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Build container: `gcloud builds submit --tag gcr.io/PROJECT-ID/flight-planning-app`
3. Deploy: `gcloud run deploy --image gcr.io/PROJECT-ID/flight-planning-app --platform managed`
4. Set environment variables in Cloud Run console

**Pros:** Serverless, pay-per-use, scales to zero
**Cons:** More complex setup

## 🔧 Environment Variables

All platforms need these environment variables:

```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
FLASK_ENV=production
```

## 📋 Deployment Checklist

- [ ] Code pushed to GitHub/GitLab
- [ ] API keys ready
- [ ] Platform account created
- [ ] Environment variables configured
- [ ] Custom domain configured (optional)
- [ ] SSL certificate enabled (usually automatic)

## 🔍 Troubleshooting

**Build Failures:**
- Check that all dependencies in `requirements.txt` are compatible
- Ensure GDAL/geospatial libraries are properly installed

**Runtime Errors:**
- Verify environment variables are set correctly
- Check logs in your platform's dashboard
- Ensure file upload directories are writable

**Performance Issues:**
- Consider upgrading to a paid tier for better resources
- Optimize image generation for faster response times

## 🌟 Recommended: Railway

For most users, Railway is the best choice because:
- ✅ Automatic detection of Python apps
- ✅ Built-in geospatial library support
- ✅ Easy environment variable management
- ✅ Automatic HTTPS and custom domains
- ✅ Good free tier to get started
- ✅ Simple deployment from GitHub

Simply push your code to GitHub, connect to Railway, add your API keys, and deploy! 