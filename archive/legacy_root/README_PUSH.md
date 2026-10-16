# Git push instructions (quick)

နမူနာအဆင့်များ - GitHub repo သို့ ထည့်ရန်

1) Git သတ်မှတ်ခြင်း (မရှိသေးရင်)

```
git init
git add .gitignore
git add -A
```

2) သေချာစေမည့် စစ်ဆေးမှုများ

```
./scripts/scan_secrets.sh
```

3) Remote ထည့်ပြီး push

```
git commit -m "Initial commit"
git remote add origin https://github.com/T2W1-LOGIXA-FLOW/enterprise-ai-dms.git
git branch -M main
git push -u origin main
```

မှတ်ချက်: အကယ်၍ scan တွင် secret တွေ တွေ့ရင် push မလုပ်ပါ။ secret မပါအောင် history ကို သန့်ရှင်းပါ။ GitHub တွင် push လုပ်ဖို့ Personal Access Token (PAT) သို့မဟုတ် SSH key အသုံးပြုရန်လိုပါသည်။
