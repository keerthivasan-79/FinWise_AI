from db import get_conn

TABLES = [
"""CREATE TABLE IF NOT EXISTS recurring_transactions (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, account_id INT NOT NULL,
 type ENUM('Income','Expense','Transfer') NOT NULL, category VARCHAR(100), amount DECIMAL(12,2) NOT NULL,
 description VARCHAR(255), payment_method VARCHAR(50), transfer_to_account INT NULL,
 frequency ENUM('Weekly','Monthly','Quarterly','Yearly') DEFAULT 'Monthly',
 next_run DATE NOT NULL, active BOOLEAN DEFAULT TRUE, last_run DATE NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS transaction_splits (
 id INT AUTO_INCREMENT PRIMARY KEY, transaction_id INT NOT NULL, user_id INT NOT NULL,
 category VARCHAR(100) NOT NULL, amount DECIMAL(12,2) NOT NULL,
 FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS notifications (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, title VARCHAR(160) NOT NULL,
 message VARCHAR(500) NOT NULL, level ENUM('info','success','warning','danger') DEFAULT 'info',
 is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS health_score_history (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, score INT NOT NULL,
 recorded_on DATE NOT NULL, UNIQUE KEY uq_health_day(user_id,recorded_on),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS scheduled_reports (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, frequency ENUM('Weekly','Monthly') DEFAULT 'Monthly',
 format ENUM('csv','xlsx','pdf') DEFAULT 'pdf', email VARCHAR(120), active BOOLEAN DEFAULT TRUE,
 next_send DATE NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS households (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL, owner_user_id INT NOT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS household_members (
 id INT AUTO_INCREMENT PRIMARY KEY, household_id INT NOT NULL, user_id INT NOT NULL,
 role ENUM('Owner','Admin','Member','Viewer') DEFAULT 'Member', status ENUM('Active','Invited') DEFAULT 'Active',
 UNIQUE KEY uq_household_user(household_id,user_id),
 FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS household_invites (
 id INT AUTO_INCREMENT PRIMARY KEY, household_id INT NOT NULL, email VARCHAR(120) NOT NULL,
 role ENUM('Admin','Member','Viewer') DEFAULT 'Member', token CHAR(36) NOT NULL UNIQUE,
 status ENUM('Pending','Accepted','Revoked') DEFAULT 'Pending', expires_at DATETIME NULL,
 accepted_at DATETIME NULL, revoked_at DATETIME NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS transaction_approvals (
 id INT AUTO_INCREMENT PRIMARY KEY, household_id INT NOT NULL, transaction_id INT NULL,
 requested_by INT NOT NULL, status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
 reviewed_by INT NULL, note VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
 FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL)""",
"""CREATE TABLE IF NOT EXISTS account_connections (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, account_id INT NOT NULL,
 provider VARCHAR(80) NOT NULL, status ENUM('Setup Required','Connected','Paused','Error') DEFAULT 'Setup Required',
 last_sync TIMESTAMP NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_account_provider(account_id,provider),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS user_preferences (
 user_id INT PRIMARY KEY, theme ENUM('light','dark','system') DEFAULT 'system',
 compact_mode BOOLEAN DEFAULT FALSE, reduced_motion BOOLEAN DEFAULT FALSE,
 dashboard_widgets JSON NULL, report_email VARCHAR(120) NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""",
"""CREATE TABLE IF NOT EXISTS password_reset_tokens (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, token_hash CHAR(64) NOT NULL UNIQUE,
 expires_at DATETIME NOT NULL, used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"""
,
"""CREATE TABLE IF NOT EXISTS email_verification_tokens (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, token_hash CHAR(64) NOT NULL UNIQUE,
 expires_at DATETIME NOT NULL, used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"""
]

COLUMNS = {
    "users": [
        ("email_verified", "BOOLEAN DEFAULT FALSE"),
        ("failed_login_count", "INT DEFAULT 0"),
        ("locked_until", "DATETIME NULL")
    ],
    "transactions": [
        ("tags", "VARCHAR(255) NULL"),
        ("recurring_transaction_id", "INT NULL"),
        ("merchant", "VARCHAR(160) NULL"),
        ("review_status", "ENUM('Cleared','Pending','Flagged') DEFAULT 'Cleared'")
    ],
    "accounts": [
        ("credit_limit", "DECIMAL(12,2) DEFAULT 0"),
        ("interest_rate", "DECIMAL(6,3) DEFAULT 0"),
        ("institution_value", "DECIMAL(12,2) DEFAULT 0"),
        ("last_reconciled_at", "TIMESTAMP NULL")
    ],
    "savings_goals": [
        ("household_id", "INT NULL")
    ],
    "household_invites": [
        ("expires_at", "DATETIME NULL"),
        ("accepted_at", "DATETIME NULL"),
        ("revoked_at", "DATETIME NULL")
    ]
}

def ensure_schema():
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    try:
        for statement in TABLES:
            cur.execute(statement)
        for table, columns in COLUMNS.items():
            cur.execute("""SELECT COLUMN_NAME FROM information_schema.COLUMNS
                           WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s""", (table,))
            existing={row["COLUMN_NAME"] for row in cur.fetchall()}
            for name, definition in columns:
                if name not in existing:
                    cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}")
        cur.execute("""ALTER TABLE accounts MODIFY account_type
                       ENUM('Bank','Cash','UPI Wallet','Credit Card','Loan','Investment') DEFAULT 'Bank'""")
        conn.commit()
    finally:
        cur.close(); conn.close()
