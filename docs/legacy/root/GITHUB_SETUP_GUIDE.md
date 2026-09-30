# GitHub Repository Setup Guide

## 🚀 GitHub တင်နည်း - အပြည့်စုံ လမ်းညွှန်

### **အဆင့် ၁: GitHub Repository အသစ်ဖန်တီးခြင်း**

1. **GitHub.com** သို့ login လုပ်ပါ
2. **+** icon ကို click ပြီး **"New repository"** ကိုရွေးပါ
3. Repository details ထည့်သွင်းပါ:
   - **Repository name**: `enterprise-ai-dms`
   - **Description**: `Enterprise AI Document Management System - Logistics-focused DMS with AI-powered OCR, classification, and duplicate detection`
   - **Visibility**: Public သို့ဟုတ် Private ရွေးပါ
4. **"Create repository"** button ကို click ပါ
5. GitHub ကနေ repository URL ကို copy လုပ်ထားပါ (ဥပမာ: `https://github.com/yourusername/enterprise-ai-dms.git`)

### **အဆင့် ၂: Local Git Setup**

အောက်ပါ commands များကို PowerShell တွင် run လုပ်ပါ:

```powershell
# Project directory သို့သွားပါ
cd "D:\1 main\Enterprise AI DMS Blueprint"

# Git initialize လုပ်ပါ (လုပ်ပြီးသားဖြစ်ပါသည်)
git init

# Git user configuration ပြုလုပ်ပါ (ပထမအကြိမ်ပဲ)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# .gitignore file ကို verify လုပ်ပါ (လုပ်ပြီးသားဖြစ်ပါသည်)
# .gitignore file ကိုကြည့်ပါ - sensitive files များပါဝင်ပါသည်
```

### **အဆင့် ၃: Files များကို Stage လုပ်ခြင်း**

```powershell
# အားလုံး files များကို stage လုပ်ပါ
git add .

# Stage လုပ်ထားသော files များကို check လုပ်ပါ
git status
```

### **အဆင့် ၄: Initial Commit လုပ်ခြင်း**

```powershell
# Initial commit လုပ်ပါ
git commit -m "Initial commit: Enterprise AI Document Management System

- Frontend: React + TypeScript with full UI components
- Backend: FastAPI with comprehensive API endpoints
- Features: Document management, user management, authentication
- AI Integration: Multiple AI providers (Gemini, Hugging Face, OpenRouter, Groq)
- Security: JWT authentication, RBAC, encryption
- Database: SQLite with PostgreSQL support ready
- Storage: Filesystem with MinIO integration ready"
```

### **အဆင့် ၅: GitHub Repository ကို Link လုပ်ခြင်း**

```powershell
# GitHub repository ကို add လုပ်ပါ (yourusername ကို သင့် GitHub username နှင့် အစားထိုးပါ)
git remote add origin https://github.com/yourusername/enterprise-ai-dms.git

# Remote ကို verify လုပ်ပါ
git remote -v
```

### **အဆင့် ၆: GitHub သို့ Push လုပ်ခြင်း**

```powershell
# Main branch သို့ push လုပ်ပါ
git branch -M main
git push -u origin main
```

**သတိပေးချက်**: GitHub သို့ push လုပ်ရာတွင် authentication လိုအပ်ပါသည်:

#### **Authentication Method ၁: Personal Access Token (Recommended)**

1. GitHub တွင် **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. **"Generate new token"** → **"Generate new token (classic)"**
3. Token details ထည့်သွင်းပါ:
   - **Note**: `Enterprise DMS Development`
   - **Expiration**: သင်သင့်သဘောရွေးပါ
   - **Scopes**: `repo` (full control of private repositories)
4. **"Generate token"** button ကို click ပါ
5. Token ကို copy လုပ်ပါ (တစ်ချိန်တည်းပဲပြန်မြင်ရမည် မဟုတ်ပါ)

ပြီးရင် push လုပ်ရာတွင် token ကို password အဖြစ်သုံးပါ:
```powershell
git push -u origin main
# Username: your GitHub username
# Password: your personal access token
```

#### **Authentication Method ၂: GitHub CLI (Alternative)**

```powershell
# GitHub CLI ကို install လုပ်ပါ
winget install GitHub.cli

# GitHub သို့ login လုပ်ပါ
gh auth login

# Push လုပ်ပါ
git push -u origin main
```

### **အဆင့် ၇: Repository ကို Setup လုပ်ခြင်း**

GitHub တွင် repository ကို open ပြီး အောက်ပါ settings များကို configure လုပ်ပါ:

#### **Repository Settings**
1. **Settings** → **General**
   - **Repository name**: လိုသလိုပြင်ဆင်နိုင်ပါသည်
   - **Description**: လိုသလိုပြင်ဆင်နိုင်ပါသည်
   - **Website**: သင့် project website ရှိပါက ထည့်သွင်းပါ

#### **Topics/Tags**
- **About** section တွင် အောက်ပါ tags များထည့်သွင်းပါ:
  ```
  document-management, ai, ocr, logistics, fastapi, react, typescript, enterprise, python, automation
  ```

#### **Repository Features**
1. **Settings** → **Features**
   - **Issues**: ✅ Enable
   - **Projects**: ✅ Enable (optional)
   - **Wiki**: ✅ Enable (optional)
   - **Discussions**: ✅ Enable (optional)

### **အဆင့် ၈: README.md ကို Update လုပ်ခြင်း**

GitHub repository တွင် README.md ကို update လုပ်ပြီး repository link များထည့်သွင်းပါ:

```powershell
# README.md ကို edit လုပ်ပါ
# GitHub repository URL ကို ထည့်သွင်းပါ

git add README.md
git commit -m "Update README with GitHub repository information"
git push
```

### **အဆင့် ၉: Branch Protection ပြုလုပ်ခြင်း (Optional but Recommended)**

1. **Settings** → **Branches**
2. **"Add rule"** button ကို click ပါ
3. **Branch name pattern**: `main`
4. **Settings**:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals**: 1 approval
   - ✅ **Require status checks to pass before merging**
   - ✅ **Require branches to be up to date before merging**

### **အဆင့် ၁၀: Collaborators ထည့်သွင်းခြင်း (Optional)**

1. **Settings** → **Collaborators**
2. **"Add people"** button ကို click ပါ
3. Collaborator email သို့ဟုတ် username ထည့်သွင်းပါ
4. Permission level ရွေးပါ:
   - **Read**: ကြည့်ရုံသာ
   - **Write**: Code ပြင်ဆင်နိုင်
   - **Admin**: Full control

---

## 📋 နောက်ထပ်လုပ်ဆောင်ရန် လုပ်ငန်းများ

### **Security Notes**
- **.env file** ကို GitHub တွင် မတင်ပါနှင့် (ပါဝင်ပါသည်)
- **API keys** များကို environment variables အဖြစ်သုံးပါ
- **Sensitive data** များကို `.env.example` file တွင် template အဖြစ်သာထည့်ပါ

### **Development Workflow**
```powershell
# New feature branch ဖန်တီးပါ
git checkout -b feature/new-feature

# Changes လုပ်ပြီး commit လုပ်ပါ
git add .
git commit -m "Add new feature"

# Push လုပ်ပါ
git push origin feature/new-feature

# Pull request ဖန်တီးပါ (GitHub တွင်)
```

### **Backup & Maintenance**
```powershell
# Local changes များကို backup လုပ်ပါ
git backup

# Repository ကို clean လုပ်ပါ
git clean -fd

# Large files များကို manage လုပ်ပါ
git gc --aggressive --prune=now
```

---

## 🎯 အဆင့်ဆင့် Summary

1. ✅ GitHub repository အသစ်ဖန်တီးပါ
2. ✅ Local git ကို initialize လုပ်ပါ
3. ✅ .gitignore file ကို setup လုပ်ပါ
4. ✅ Files များကို stage လုပ်ပါ
5. ✅ Initial commit လုပ်ပါ
6. ✅ GitHub remote ကို add လုပ်ပါ
7. ✅ Authentication ပြုလုပ်ပါ
8. ✅ GitHub သို့ push လုပ်ပါ
9. ✅ Repository settings များကို configure လုပ်ပါ
10. ✅ Branch protection ပြုလုပ်ပါ (optional)

---

## 📞 အကူအညီရယူရန်

ပြဿနာရှိပါက:
- GitHub Documentation: https://docs.github.com
- Git Documentation: https://git-scm.com/docs
- သို့ဟုတ် ကျွန်ုပ်ကို မေးနိုင်ပါသည်။