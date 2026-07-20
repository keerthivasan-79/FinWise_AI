# FinWise AI - Smart Personal Finance Management

## Features
FinWise tracks accounts, income, expenses, transfers, ledger entries, budgets, savings goals, analytics, reports, statement imports, automation, and local finance guidance.

The AI features are offline and explainable:
- Category prediction uses Multinomial Naive Bayes with finance keywords and your saved transactions.
- Chat guidance uses local rule-based checks over your accounts, budgets, goals, and transactions.
- Ledger running balance uses debit/credit bookkeeping logic.
- It does not require internet access or a paid AI API.

## Important Limits
- Password reset tokens are not shown by default. Real reset delivery needs an email provider. For local testing only, set `SHOW_RESET_TOKEN=true`.
- Scheduled reports are saved as local reminders until SMTP/email credentials are connected.
- Bank connections are setup placeholders unless a real provider integration is added.
- Login sessions use httpOnly cookies instead of browser localStorage tokens.
- Local secrets belong in `.env` or `instance/`, not hard-coded source files.

## Setup
### 1. Database
Open MySQL Workbench and run:
```sql
SOURCE C:/FinWise_AI/database/schema.sql;
```

### 2. Install dependencies first time only
```powershell
cd backend
python -m pip install -r requirements.txt
cd ..\frontend
npm install
```

### Local config
This workspace includes a local ignored `.env` for your MySQL password. For another machine, copy `.env.example` to `.env` and update:
```text
DB_PASSWORD=your-mysql-password
JWT_SECRET=a-long-random-secret
```

### 3. Run the app
```powershell
.\run.cmd
```

Open http://127.0.0.1:5000.

If the browser says the page failed to load, the app is not running yet. Start it with `.\run.cmd` and keep that window open. Use port `5000`, not `5050`.

If the starter says Python is missing or blocked, install Python and run:
```powershell
cd C:\FinWise_AI
python -m pip install -r backend\requirements.txt
```

Then run `.\run.cmd` again.

### Checks
```powershell
python -m unittest discover -s backend/tests
cd frontend
npm run build
npm test
```

Before any real deployment, set strong values for `DB_PASSWORD`, `JWT_SECRET`, and `COOKIE_SECURE=true`.
