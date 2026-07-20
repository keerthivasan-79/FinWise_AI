# FinWise AI Demo Checklist

Use this order when showing the project to your guide.

## 1. Start the App

```powershell
cd C:\FinWise_AI
.\run.cmd
```

Open:

```text
http://127.0.0.1:5000
```

## 2. Login

- Show login page.
- Login with your test account.
- Mention that passwords are stored as hashes.

## 3. Dashboard

Show these cards:

- Total Money.
- Balance Money.
- Income.
- Expense.
- Savings.

Explain:

```text
Total Money = Balance Money + Goal Savings
```

## 4. Accounts

Show account types:

- Bank.
- Cash.
- UPI Wallet.
- Credit Card.
- Loan.
- Investment.

Add or show two bank accounts, one credit card, and one loan account.

## 5. Transactions

Show three transaction types:

- Income.
- Expense.
- Transfer.

Explain that transfer is used for moving money from one own account to another own account.

## 6. Ledger

Open Ledger and explain:

```text
Running Balance = Opening Balance + Credits - Debits
```

Show how income, expense, and transfer affect debit and credit.

## 7. Bank Statement Import

Open Transactions and show Import Bank Statement.

Explain:

- CSV, Excel, and text-based PDF are supported.
- Preview appears before saving.
- Duplicates are marked before import.

## 8. Analytics

Open Analytics.

Show:

- Month selector.
- Income.
- Expense.
- Net flow.
- Saved to goals.
- Top category.
- Category chart.

Explain that the page filters transactions by selected month.

## 9. Budget

Open Budget.

Show category-wise budget limit and spending usage.

Explain:

```text
Budget Usage Percent = Actual Expense / Budget Limit * 100
```

## 10. Savings Goals

Open Savings Goals.

Show:

- Goal target.
- Saved amount.
- Still needed.
- Add savings to goal.

Explain that goal saving is not counted as normal expense because the money is still owned by the user.

## 11. Finance Chat

Open Finance Chat and ask these questions:

```text
What algorithms are used here?
Is this offline?
What is balance money?
How does transfer work?
Explain ledger.
```

Mention that the answers come from local rules and local finance data.

## 12. Smart Tools

Open Smart Tools.

Show auto entries for repeated income or expenses such as:

- Salary.
- Rent.
- EMI.
- Bills.
- Subscription.

## 13. Profile

Open Profile.

Show:

- Name.
- Email.
- Password change.
- Theme selection.
- Logout button.

## 14. Reports

Open Reports.

Show export or report options available in the app.

## 15. Final Explanation

End with this short summary:

```text
FinWise AI is an offline personal finance management system. It tracks accounts, income, expenses, transfers, loans, credit cards, budgets, savings goals, analytics, reports, ledger, statement import, and local finance chat. The main algorithms are Naive Bayes category prediction, ledger running balance, duplicate detection, budget usage, savings rate, goal progress, and month-wise analytics.
```

## Screenshot List For Report

Take screenshots of:

- Login page.
- Dashboard.
- Accounts page.
- Transactions page.
- Statement import preview.
- Ledger page.
- Analytics page.
- Budget page.
- Savings goals page.
- Finance chat page.
- Profile page.
