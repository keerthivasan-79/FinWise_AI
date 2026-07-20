# FinWise AI Viva Notes

## 1. What is FinWise AI?

FinWise AI is a personal finance management system. It helps users track accounts, income, expenses, transfers, budgets, savings goals, statement imports, ledger entries, analytics, reports, and finance guidance.

## 2. Why is it called AI?

It has offline AI-style features:

- It predicts transaction category using Multinomial Naive Bayes.
- It answers finance questions using local rule-based intent matching.
- It gives finance insights from the user's own transaction data.

## 3. Does it need internet?

No. After setup, it can run locally without internet. The frontend, backend, database, finance chat, and category prediction all work on the local machine.

## 4. What algorithms are used?

- Multinomial Naive Bayes for transaction category prediction.
- Rule-based intent matching for offline finance chat.
- Ledger running balance algorithm.
- Duplicate transaction detection during statement import.
- Budget utilization calculation.
- Savings rate calculation.
- Goal progress calculation.
- Month-wise analytics grouping.
- Financial health rules.

## 5. Explain Multinomial Naive Bayes in this project.

The system reads a transaction description and predicts its category.

Example:

```text
"salary july" -> Salary
"swiggy dinner" -> Food
"electricity bill" -> Bills
```

It calculates which category is most likely based on words in the description and previous transaction data.

## 6. Explain the ledger algorithm.

The ledger shows debit, credit, and running balance for each account.

```text
Running Balance = Opening Balance + Credits - Debits
```

Income is a credit. Expense is a debit. Transfer creates a debit in one account and a credit in another account.

## 7. What is Balance Money?

Balance Money means the money currently available in accounts. It is the amount the user can actually use now.

## 8. What is Total Money?

Total Money means balance money plus money saved in goals.

```text
Total Money = Balance Money + Goal Savings
```

## 9. Why are savings goals not shown as expenses?

Goal savings are not normal expenses because the user still owns the money. The money is only moved from an account into a savings goal. So it is tracked separately as savings.

## 10. How are transfers handled?

Transfers are used when money moves from one account to another account owned by the same user. A transfer is not income and not expense. It only changes account balances.

## 11. How should loans and credit cards be added?

Loans and credit cards can be added as account types. This keeps them visible with other accounts and makes tracking easier.

## 12. What is the use of bank statement import?

It saves time. The user can upload CSV, Excel, or text-based PDF statements, preview rows, fix categories, and import them into transactions.

## 13. How does duplicate import prevention work?

Before importing, the system checks if a similar transaction already exists for the same account, date, amount, type, and description. Duplicate rows are marked so the user does not import them again.

## 14. What is the use of Smart Tools?

Smart Tools are for repeated income or expense entries, like salary, rent, EMI, subscriptions, and bills. It helps avoid entering the same transaction manually every time.

## 15. Why was Family removed?

The project is kept simple and focused. The main purpose is personal finance tracking, so removing Family makes the system easier to understand and demonstrate.

## 16. What security is used?

- Password hashing.
- httpOnly cookie sessions.
- User-specific data filtering.
- Hidden reset tokens by default.
- Local environment variables for secrets.

## 17. What are the main modules?

- Login and Profile.
- Dashboard.
- Accounts.
- Transactions.
- Ledger.
- Budgets.
- Savings Goals.
- Analytics.
- Reports.
- Finance Chat.
- Smart Tools.

## 18. What is the database used?

MySQL is used to store users, accounts, transactions, budgets, goals, statement imports, automation entries, and preferences.

## 19. What is the limitation of the AI chat?

It is offline and explainable, but it is not a large online AI model. It answers from local project rules and finance data.

## 20. How do you run the project?

Open the project folder and run:

```powershell
cd C:\FinWise_AI
.\run.cmd
```

Then open:

```text
http://127.0.0.1:5000
```

Keep the run window open.
