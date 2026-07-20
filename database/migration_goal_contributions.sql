USE expense_manager_web;

CREATE TABLE IF NOT EXISTS goal_contributions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  goal_id INT NOT NULL,
  account_id INT NOT NULL,
  action ENUM('Deposit','Withdraw') NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (goal_id) REFERENCES savings_goals(id) ON DELETE CASCADE,
  FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);
