# 🚀 Railway Deployment Guide

## Prerequisites
- Railway account (you already have one!)
- Railway CLI installed: `npm install -g @railway/cli`

## 🎯 **Step 1: Deploy Backend**

```bash
cd backend

# Login to Railway
railway login

# Initialize Railway project
railway init

# Deploy to Railway
railway up
```

**Set Environment Variables in Railway Dashboard:**
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER` 
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_SCHEMA`
- `SNOWFLAKE_INSECURE`
- `KUMO_KEY`
- `OPENAI_API_KEY`
- `JWT_SECRET`
- `JWT_ISS`
- `JWT_AUD`
- `ENVIRONMENT=production`
- `FRONTEND_URL=https://your-frontend-domain.railway.app`

## 🎨 **Step 2: Deploy Frontend**

```bash
cd frontend

# Initialize Railway project
railway init

# Deploy to Railway
railway up
```

**Set Environment Variables in Railway Dashboard:**
- `VITE_API_URL=https://your-backend-domain.railway.app`

## 🔧 **Step 3: Update Frontend API Calls**

Update your frontend to use the production API URL. In `frontend/src/pages/UserAnalysis.tsx`:

```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api';

const response = await fetch(`${API_BASE}/me/analysis`, {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
});
```

## 🌐 **Step 4: Update Vite Config**

Remove the proxy configuration in `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Remove proxy for production
  },
});
```

## 📱 **Step 5: Test Deployment**

1. **Backend Health Check**: Visit `https://your-backend-domain.railway.app/health`
2. **Frontend**: Visit your frontend Railway URL
3. **Test Authentication**: Try signing up/signing in
4. **Test Analysis**: Like some colleges and test the AI analysis

## 🔍 **Troubleshooting**

### **Backend Issues**
- Check Railway logs: `railway logs`
- Verify environment variables are set
- Check health endpoint: `/health`

### **Frontend Issues**
- Ensure `VITE_API_URL` is set correctly
- Check browser console for CORS errors
- Verify backend URL in frontend config

### **Common Errors**
- **CORS Error**: Check `FRONTEND_URL` in backend env vars
- **Database Error**: Verify Snowflake credentials
- **OpenAI Error**: Check `OPENAI_API_KEY` is set

## 💰 **Cost Optimization**

1. **Use Railway's free tier** (limited hours)
2. **Scale down** when not in use
3. **Monitor usage** in Railway dashboard
4. **Consider database migration** to Railway's PostgreSQL for cost savings

## 🚀 **Production Checklist**

- [ ] Backend deployed and healthy
- [ ] Frontend deployed and accessible
- [ ] Environment variables configured
- [ ] CORS properly configured
- [ ] Health checks working
- [ ] Authentication working
- [ ] AI analysis working
- [ ] Database connections stable

## 🔄 **Continuous Deployment**

Railway automatically redeploys when you push to your main branch. To enable:

1. Connect your GitHub repo in Railway
2. Set branch to `main`
3. Enable auto-deploy

## 📊 **Monitoring**

- **Railway Dashboard**: Monitor app health, logs, and usage
- **Health Endpoint**: `/health` for uptime monitoring
- **Logs**: `railway logs` for debugging

## 🆘 **Support**

- **Railway Docs**: https://docs.railway.app/
- **Railway Discord**: https://discord.gg/railway
- **Railway Status**: https://status.railway.app/

---

**Next Steps**: After deployment, consider migrating from Snowflake to Railway's PostgreSQL for cost savings!
