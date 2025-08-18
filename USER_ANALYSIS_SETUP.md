# User Analysis Feature Setup Guide

## Overview
This feature provides AI-powered analysis of student college preferences and admission chances using OpenAI's GPT-4 model.

## Setup Requirements

### 1. OpenAI API Key
You need to add your OpenAI API key to the `.local.env` file:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

**Important**: Replace `your_openai_api_key_here` with your actual OpenAI API key.

### 2. Dependencies
The backend now requires the `openai` package, which has been installed.

## Features

### 1. General Description
- Analyzes the types of schools the student has liked
- Identifies patterns (selective, party schools, sports-focused, small schools, etc.)
- Provides a brief 2-3 sentence overview

### 2. College Preferences Analysis
- Identifies common themes among liked schools
- Highlights what the student values most
- Shows unique factors that make each school distinct

### 3. Admission Chances Assessment
- Classifies each liked college as:
  - **REACH**: Very competitive, low chance
  - **TARGET**: Good match, moderate chance
  - **LIKELY**: Strong candidate, high chance
  - **SAFETY**: Very likely to get in
- Based on student's test scores vs. college's 50th percentile scores

## API Endpoint

### GET `/me/analysis`
- **Authentication**: Required (Bearer token)
- **Response**: JSON with three sections:
  ```json
  {
    "general_description": "Brief overview of preferences",
    "college_preferences": "Analysis of what they value",
    "admission_chances": [
      {
        "college_name": "University Name",
        "assessment": "REACH - Your SAT scores are below the 25th percentile"
      }
    ]
  }
  ```

## Frontend Integration

### Navigation
- Added "🧠 Analysis" link in the top navigation bar
- Route: `/analysis`
- Protected by AuthGuard

### UI Components
- Loading states with spinner
- Error handling for API failures
- Color-coded admission chance classifications
- Responsive design using existing CSS system

## Testing

### 1. Start the Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```

### 3. Test the Feature
1. Sign in to the application
2. Like some colleges using the swipe interface
3. Navigate to "🧠 Analysis" in the top bar
4. View your personalized college analysis

## Error Handling

- **503 Error**: OpenAI API not configured
- **401 Error**: Authentication required
- **404 Error**: User profile not found
- **500 Error**: Analysis processing failed

## Customization

### Prompt Engineering
The OpenAI prompt can be customized in `backend/app/main.py` around line 650. The current prompt:
- Provides clear structure for the three analysis sections
- Includes student profile and college data
- Requests specific formatting for admission chances
- Limits response to 800 tokens for cost efficiency

### Model Selection
Currently uses GPT-4, but can be changed to other models by modifying the `model` parameter in the OpenAI API call.

## Cost Considerations

- Each analysis request costs approximately $0.02-0.05 depending on response length
- Consider implementing caching for repeated requests
- Monitor API usage in your OpenAI dashboard

## Security Notes

- API key is stored in environment variables
- All requests require valid JWT authentication
- User data is only accessible to authenticated users
- No sensitive data is sent to OpenAI beyond what's necessary for analysis
