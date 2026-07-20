USE expense_manager_web;

SELECT COUNT(DISTINCT t.id) AS bank_linked_transactions
FROM transactions t
JOIN accounts source ON source.id = t.account_id
LEFT JOIN accounts target ON target.id = t.transfer_to_account
WHERE source.account_type = 'Bank' OR target.account_type = 'Bank';

SELECT
  source.account_name,
  source.account_type,
  COUNT(DISTINCT t.id) AS transactions
FROM transactions t
JOIN accounts source ON source.id = t.account_id
LEFT JOIN accounts target ON target.id = t.transfer_to_account
WHERE source.account_type = 'Bank' OR target.account_type = 'Bank'
GROUP BY source.id, source.account_name, source.account_type
ORDER BY transactions DESC, source.account_name;
