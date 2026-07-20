USE expense_manager_web;

START TRANSACTION;

SET @backup_id = DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s');

CREATE TEMPORARY TABLE bank_tx_to_delete AS
SELECT DISTINCT t.id
FROM transactions t
JOIN accounts source ON source.id = t.account_id
LEFT JOIN accounts target ON target.id = t.transfer_to_account
WHERE source.account_type = 'Bank' OR target.account_type = 'Bank';

CREATE TABLE IF NOT EXISTS bank_transaction_delete_backups (
  backup_id VARCHAR(32) NOT NULL,
  backed_up_at DATETIME NOT NULL,
  transaction_id INT NOT NULL,
  user_id INT NOT NULL,
  account_id INT NOT NULL,
  type VARCHAR(20) NOT NULL,
  category VARCHAR(100),
  amount DECIMAL(12,2) NOT NULL,
  description VARCHAR(255),
  transaction_date DATE NOT NULL,
  payment_method VARCHAR(50),
  receipt_path VARCHAR(255),
  statement_import_id INT,
  transfer_to_account INT,
  tags VARCHAR(255),
  recurring_transaction_id INT,
  merchant VARCHAR(160),
  review_status VARCHAR(20),
  created_at TIMESTAMP NULL,
  source_account_name VARCHAR(100),
  source_account_type VARCHAR(50),
  target_account_name VARCHAR(100),
  target_account_type VARCHAR(50),
  INDEX idx_backup_id (backup_id),
  INDEX idx_transaction_id (transaction_id)
);

INSERT INTO bank_transaction_delete_backups (
  backup_id, backed_up_at, transaction_id, user_id, account_id, type, category,
  amount, description, transaction_date, payment_method, receipt_path,
  statement_import_id, transfer_to_account, tags, recurring_transaction_id,
  merchant, review_status, created_at, source_account_name, source_account_type,
  target_account_name, target_account_type
)
SELECT
  @backup_id, NOW(), t.id, t.user_id, t.account_id, t.type, t.category,
  t.amount, t.description, t.transaction_date, t.payment_method, t.receipt_path,
  t.statement_import_id, t.transfer_to_account, t.tags, t.recurring_transaction_id,
  t.merchant, t.review_status, t.created_at, source.account_name, source.account_type,
  target.account_name, target.account_type
FROM transactions t
JOIN bank_tx_to_delete todo ON todo.id = t.id
JOIN accounts source ON source.id = t.account_id
LEFT JOIN accounts target ON target.id = t.transfer_to_account;

UPDATE accounts a
JOIN (
  SELECT
    account_id,
    SUM(CASE
      WHEN type = 'Income' THEN -amount
      WHEN type = 'Expense' THEN amount
      WHEN type = 'Transfer' THEN amount
      ELSE 0
    END) AS balance_delta
  FROM transactions
  WHERE id IN (SELECT id FROM bank_tx_to_delete)
  GROUP BY account_id
) x ON x.account_id = a.id
SET a.current_balance = a.current_balance + x.balance_delta;

UPDATE accounts a
JOIN (
  SELECT transfer_to_account AS account_id, SUM(-amount) AS balance_delta
  FROM transactions
  WHERE id IN (SELECT id FROM bank_tx_to_delete)
    AND type = 'Transfer'
    AND transfer_to_account IS NOT NULL
  GROUP BY transfer_to_account
) x ON x.account_id = a.id
SET a.current_balance = a.current_balance + x.balance_delta;

DELETE t
FROM transactions t
JOIN bank_tx_to_delete todo ON todo.id = t.id;

SET @deleted_transactions = ROW_COUNT();

DELETE s
FROM statement_imports s
LEFT JOIN transactions t ON t.statement_import_id = s.id
WHERE t.id IS NULL;

SELECT @backup_id AS backup_id, @deleted_transactions AS deleted_transactions, ROW_COUNT() AS stale_imports_removed;

COMMIT;
