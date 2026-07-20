USE expense_manager_web;
CREATE TABLE IF NOT EXISTS statement_imports (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 account_id INT NOT NULL,
 file_name VARCHAR(255) NOT NULL,
 file_hash CHAR(64) NOT NULL,
 imported_rows INT NOT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY unique_statement (user_id,file_hash),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);
