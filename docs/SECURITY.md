# Repository security and secrets handling

ဤ repo တွင် API key, private key, credentials များကို commit မလုပ်ရန် ဤအချက်များကို လိုက်နာပါ။

- .env ဖိုင်များနှင့် secret ဖိုင်များကို `.gitignore` ထဲထည့်ထားပါ။
- လုပ်ဆောင်ရန် - အလုပ်အသစ်စတင်မည်ဆို `scripts/scan_secrets.sh` ကို chạy နောက်ဆုံး commit မတင်ခင် run လုပ်ပါ။
- GitHub တွင် secret များသိမ်းရန်: `Settings -> Secrets` (သို့) Actions secrets အသုံးပြုပါ။
- အကယ်၍ secret များကို commit လုပ်ပြီးသားဖြစ်လျှင် history မှ ဖယ်ရှားရန် `git filter-repo` သို့မဟုတ် `bfg-repo-cleaner` ကို အသုံးပြုပါ။

ဥပမာ အချက်ပြ (ပြန်လည်ရေးသားခြင်း):

1. `git filter-repo --path .env --invert-paths` (သို့) BFG ကို အသုံးပြုပါ။
2. ပြန်လည်ရေးသားပြီးနောက် remote ကို force push မလုပ်ပါမနည်း သေချာစစ်ဆေးပါ။

ပိုမိုကောင်းမွန်ရန် GitHub Secret Scanning and Dependabot ကို အလုပ်ချိတ်ပါ။
