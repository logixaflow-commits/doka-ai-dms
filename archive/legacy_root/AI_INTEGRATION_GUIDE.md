# AI Services Integration Guide

## 🔑 Configured API Keys

Configure provider credentials through a deployment secret manager or an untracked local `.env` file. Never commit live API keys or access tokens.

| Provider | API Key | Model | Status |
|----------|---------|-------|--------|
| **OpenAI** | Set through secret manager | gpt-4o-mini | Not stored in repository |
| **Gemini** | Set through secret manager | gemini-pro | Not stored in repository |
| **Hugging Face** | Set through secret manager | sentence-transformers/all-MiniLM-L6-v2 | Not stored in repository |
| **OpenRouter** | Set through secret manager | anthropic/claude-3-haiku | Not stored in repository |
| **Groq** | Set through secret manager | llama-3.3-70b-versatile | Not stored in repository |

---

## 🚀 AI Features Enabled

### 1. **AI-Enhanced Duplicate Detection**
- **Enabled:** ✅ `AI_ENHANCED_DUPLICATE_DETECTION=True`
- **Provider:** Automatically selects best available provider
- **Features:**
  - Semantic similarity detection
  - Embedding-based comparison
  - Multi-provider fallback

### 2. **AI-Powered Classification**
- **Enabled:** ✅ `AI_CLASSIFICATION_ENABLED=True`
- **Provider:** Supports all configured providers
- **Features:**
  - Automatic document categorization
  - Confidence scoring
  - Entity extraction
  - Suspicious document detection

---

## 📋 Configuration Files Updated

### 1. **dms/.env** (Production)
```env
# AI Services Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-pro

HUGGINGFACE_API_KEY=your_huggingface_api_key_here
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2

OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=anthropic/claude-3-haiku

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

AI_ENHANCED_DUPLICATE_DETECTION=True
AI_CLASSIFICATION_ENABLED=True
```

### 2. **dms/.env.example** (Template)
- Updated with all AI provider configurations
- Can be used as reference for future setups

### 3. **dms/app/core/config.py**
- Added AI provider configurations
- Loaded from environment variables
- Available throughout the application

---

## 🔧 New AI Service: `unified_ai_service.py`

A unified AI service that supports multiple providers:

### **Features:**
- ✅ **Provider Abstraction** - Single interface for multiple AI providers
- ✅ **Automatic Fallback** - Try providers in order if one fails
- ✅ **Embedding Support** - Text embeddings for semantic search
- ✅ **Similarity Calculation** - Cosine similarity for duplicate detection
- ✅ **Document Analysis** - Classification and entity extraction

### **Methods:**
```python
# Get available providers
providers = ai_service.get_available_providers()

# Analyze document for classification
result = await ai_service.analyze_document(text, provider="gemini")

# Get text embeddings
embeddings = await ai_service.get_embedding(text, provider="huggingface")

# Compare semantic similarity
similarity = await ai_service.compare_similarity(text1, text2)

# Call specific providers
await ai_service.call_openai(prompt, system_prompt)
await ai_service.call_gemini(prompt, system_prompt)
await ai_service.call_openrouter(prompt, system_prompt)
await ai_service.call_groq(prompt, system_prompt)
```

---

## 📊 Provider Comparison

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| **Groq** | ⚡⚡⚡⚡⚡ | Low | Fast inference, real-time |
| **OpenRouter** | ⚡⚡⚡⚡ | Medium | Multiple model access |
| **Gemini** | ⚡⚡⚡ | Free | Document analysis |
| **Hugging Face** | ⚡⚡ | Low | Embeddings, classification |
| **OpenAI** | ⚡⚡⚡⚡ | High | Best quality, GPT-4 |

---

## 🎯 Usage Examples

### 1. **Duplicate Detection**
```python
from app.services.ai_duplicate_detector import ai_detector

# Detect duplicates using AI
duplicates = await ai_detector.detect_duplicates(
    documents=[doc1, doc2, doc3],
    threshold=0.85
)
```

### 2. **Document Classification**
```python
# Classify document using AI
result = await ai_detector.classify_document(
    text=document_text,
    metadata={"supplier": "ABC Logistics"}
)

# Returns:
# {
#   "category": "Invoice",
#   "confidence": 0.92,
#   "entities": {...},
#   "is_suspicious": false
# }
```

### 3. **Semantic Search**
```python
from app.services.unified_ai_service import ai_service

# Get embeddings for semantic search
embedding = await ai_service.get_embedding(
    text="search query",
    provider="huggingface"
)

# Compare similarity
similarity = await ai_service.compare_similarity(
    text1="document 1 text",
    text2="document 2 text"
)
```

---

## 🔐 Security Considerations

### **API Key Storage:**
- ✅ Keys stored in `.env` (not in version control)
- ✅ Loaded via environment variables
- ✅ Never logged or exposed in API responses
- ✅ Encrypted at rest (optional)

### **Access Control:**
- AI features respect RBAC (Role-Based Access Control)
- Admin-only for sensitive operations
- Audit logging for all AI API calls

---

## 📈 Performance Monitoring

### **Logging:**
All AI API calls are logged with:
- Provider used
- Model used
- Response time
- Success/Failure status
- Error details (if any)

### **Metrics:**
Track these metrics for optimization:
- API response times per provider
- Success rates per provider
- Cost per provider
- Accuracy of classifications

---

## 🚨 Troubleshooting

### **Issue: Provider Not Available**
**Solution:**
```bash
# Check provider status
python -c "from app.services.unified_ai_service import ai_service; print(ai_service.get_available_providers())"
```

### **Issue: API Rate Limit**
**Solution:**
- The system automatically tries alternative providers
- Implement rate limiting in production
- Use multiple providers for redundancy

### **Issue: High Latency**
**Solution:**
- Use Groq for fastest inference
- Cache embeddings for repeated queries
- Implement async processing with Celery

---

## 🔧 Dependencies Updated

Added to `requirements-dev.txt`:
```txt
openai>=1.3.5
tiktoken>=0.5.1
google-generativeai>=0.3.0  # For Gemini
httpx>=0.24.0                # For async HTTP
numpy>=1.24.3                # For similarity calculations
```

Install with:
```bash
cd dms
pip install -r requirements-dev.txt
```

---

## 🎉 Next Steps

### **1. Install Dependencies**
```bash
cd dms
pip install -r requirements-dev.txt
```

### **2. Test AI Integration**
```bash
python -c "from app.services.unified_ai_service import ai_service; print(ai_service.get_available_providers())"
```

### **3. Test Classification**
```python
from app.services.ai_duplicate_detector import ai_detector
import asyncio

result = asyncio.run(ai_detector.classify_document("Sample document text"))
print(result)
```

### **4. Monitor Usage**
- Check logs for AI API calls
- Track costs per provider
- Monitor classification accuracy

---

**Status:** ✅ AI Integration Complete
**Providers:** 5 (OpenAI, Gemini, Hugging Face, OpenRouter, Groq)
**Features:** Duplicate Detection, Classification, Embeddings, Similarity
**Configuration:** Ready to Use