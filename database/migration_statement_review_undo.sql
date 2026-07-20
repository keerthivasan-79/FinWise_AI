USE expense_manager_web;
ALTER TABLE transactions
  ADD COLUMN statement_import_id INT NULL AFTER receipt_path,
  ADD INDEX idx_statement_import_id (statement_import_id),
  ADD CONSTRAINT fk_transactions_statement_import
    FOREIGN KEY (statement_import_id) REFERENCES statement_imports(id)
    ON DELETE SET NULL;
