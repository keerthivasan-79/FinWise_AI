USE expense_manager_web;
ALTER TABLE accounts ADD COLUMN account_subtype VARCHAR(50) DEFAULT 'Savings Account' AFTER account_type;
