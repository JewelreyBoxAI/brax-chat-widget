# Brax Fine Jewelers AI Assistant - Deployment Guide

## Environment Variables

Create a `.env` file with the following configuration:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Brax Integration APIs
BRAX_API_KEY=your_brax_api_key_here
JEWELRY_INVENTORY_URL=https://inventory.braxjewelers.com/api
APPOINTMENT_BOOKING_URL=https://booking.braxjewelers.com/api

# CORS Configuration
ALLOWED_ORIGINS=https://braxjewelers.com,https://shop.braxjewelers.com

# Optional: Analytics and Monitoring
BRAX_ANALYTICS_ID=your_analytics_id
SENTRY_DSN=your_sentry_dsn_for_error_tracking
```

## Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

3. **Run the Application**
   ```bash
   uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Test the Widget**
   - Navigate to `http://localhost:8000/widget`
   - Chat with Elena Marchetti about jewelry

## Production Deployment

### Option 1: Railway Deployment

1. **Connect Repository**
   - Link your GitHub repository to Railway
   - Railway will auto-detect the FastAPI application

2. **Environment Variables**
   ```bash
   OPENAI_API_KEY=prod_openai_key
   BRAX_API_KEY=prod_brax_key
   JEWELRY_INVENTORY_URL=https://prod-inventory.braxjewelers.com/api
   ALLOWED_ORIGINS=https://braxjewelers.com,https://shop.braxjewelers.com
   ```

3. **Custom Domain**
   - Set up `assistant.braxjewelers.com`
   - Configure SSL certificate

### Option 2: AWS Lambda Deployment

1. **Install Mangum**
   ```bash
   pip install mangum
   ```

2. **Update app.py**
   ```python
   from mangum import Mangum
   
   # Add at the end of app.py
   handler = Mangum(app)
   ```

3. **Deploy with Serverless Framework**
   ```yaml
   # serverless.yml
   service: brax-jewelry-assistant
   
   provider:
     name: aws
     runtime: python3.9
     environment:
       OPENAI_API_KEY: ${env:OPENAI_API_KEY}
       BRAX_API_KEY: ${env:BRAX_API_KEY}
   
   functions:
     api:
       handler: src.app.handler
       events:
         - http:
             path: /{proxy+}
             method: ANY
   ```

### Option 3: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY src/ ./src/
   
   EXPOSE 8000
   CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and Run**
   ```bash
   docker build -t brax-jewelry-assistant .
   docker run -p 8000:8000 --env-file .env brax-jewelry-assistant
   ```

## Widget Integration

### Embed on Brax Website

Add this script to your website's HTML:

```html
<!-- Brax Fine Jewelers AI Assistant -->
<script>
  (function() {
    const braxWidget = document.createElement('iframe');
    braxWidget.src = 'https://assistant.braxjewelers.com/widget';
    braxWidget.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 400px;
      height: 600px;
      border: none;
      border-radius: 16px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.15);
      z-index: 9999;
    `;
    braxWidget.setAttribute('title', 'Brax Jewelry Consultant');
    document.body.appendChild(braxWidget);
  })();
</script>
```

### Custom Integration Options

```javascript
// Option 1: Direct API Integration
const chatWithElena = async (message) => {
  const response = await fetch('https://assistant.braxjewelers.com/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_input: message,
      history: []
    })
  });
  return response.json();
};

// Option 2: Jewelry Recommendations
const getRecommendations = async (occasion, budget) => {
  const response = await fetch('https://assistant.braxjewelers.com/jewelry/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      occasion: occasion,
      budget_min: budget.min,
      budget_max: budget.max
    })
  });
  return response.json();
};
```

## Monitoring and Analytics

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Brax Fine Jewelers AI Assistant"}
```

### Logging Configuration

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('brax_assistant.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

## Security Considerations

1. **API Key Management**
   - Use environment variables for all secrets
   - Rotate API keys regularly
   - Implement rate limiting

2. **CORS Configuration**
   - Restrict origins to Brax domains only
   - Use HTTPS in production

3. **Input Validation**
   - Sanitize all user inputs
   - Implement request size limits
   - Add authentication for admin endpoints

## Performance Optimization

1. **Caching**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_jewelry_recommendations(occasion: str, budget: str):
       # Cache frequent recommendations
       pass
   ```

2. **Database Connection Pooling**
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.pool import QueuePool
   
   engine = create_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=10,
       max_overflow=20
   )
   ```

3. **CDN for Static Assets**
   - Host avatar images on CDN
   - Optimize image formats (WebP)
   - Enable gzip compression

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   ```bash
   # Check API key validity
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

2. **CORS Issues**
   - Verify ALLOWED_ORIGINS includes your domain
   - Check browser console for CORS errors

3. **Widget Not Loading**
   - Verify iframe src URL is correct
   - Check for JavaScript errors in console
   - Ensure proper HTTPS configuration

### Logs and Debugging

```bash
# View application logs
tail -f brax_assistant.log

# Check specific error patterns
grep "ERROR" brax_assistant.log | tail -20
```

## Support

For technical support or integration assistance:
- Email: tech-support@braxjewelers.com
- Phone: (949) 250-9949
- Documentation: https://docs.braxjewelers.com/ai-assistant
