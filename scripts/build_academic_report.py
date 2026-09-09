import os
import re
import sys
import math
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Preformatted
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF_DIR = ROOT / "output" / "pdf"
OUTPUT_DOCX_DIR = ROOT / "output" / "docx"

# Student Placeholder Data (Standard Academic Format)
STUDENT_NAME = "[STUDENT_NAME]"
REGISTER_NUMBER = "[REGISTER_NUMBER]"
INSTITUTION_NAME = "[INSTITUTION_NAME]"
GUIDE_NAME = "[GUIDE_NAME]"
HOD_NAME = "[HEAD_OF_DEPARTMENT]"
ACADEMIC_YEAR = "2025 - 2026"

# ------------------ GLOBAL ACADEMIC TEXTS ------------------
INTRO_P1 = (
    "Managing personal finances is a foundational skill for students, working professionals, and families alike. "
    "In today's economy, individuals frequently move money across multiple channels, including traditional savings accounts, "
    "cash on hand, e-wallets, UPI accounts, and credit cards. When loans and investment balances are factored in, tracking "
    "financial health becomes challenging."
)

PROBLEM_P1 = (
    "Many students and individuals record money details manually or keep them spread across bank apps, notes, and spreadsheets. "
    "This makes it difficult to know how much money is currently available, where money is being spent, whether a budget is being "
    "crossed, how much has been saved toward goals, and how loans and transfers affect account balances. Manual methods are "
    "error-prone, spreadsheets lack visual breakdowns, and cloud-based trackers violate privacy by storing logs on third-party servers."
)

MOTIVATION_P1 = (
    "The primary motivation is to empower users to take control of their finances without exposing their sensitive transaction data "
    "to third parties. By compiling data locally, FinWise AI guarantees maximum security and privacy. The integration of offline "
    "algorithms (Naive Bayes) shows that smart financial tracking does not depend on cloud-connected APIs."
)

OVERVIEW_P1 = (
    "FinWise AI is structured as an offline-first single-page application. The React user interface communicates with a local Flask "
    "server, which manages calculations and queries a MySQL database. Users can import transactions in CSV/Excel/PDF formats, "
    "manage double-entry ledger logs, configure categories, establish savings goals, and check budgets in a secure local dashboard."
)

EXISTING_SYS_TEXT = (
    "Currently, most individuals manage their money through manual bookkeeping, offline spreadsheets, or cloud-connected budgeting apps. "
    "In the existing setup, notebook entries require manually calculating running balances, spreadsheets lack visual alerts, "
    "and cloud apps automatically read bank details by linking accounts to third-party servers, raising privacy concerns."
)

PROP_SYS_TEXT = (
    "FinWise AI is a local personal finance tracker that runs on the user's computer. It features: a centralized ledger for multiple accounts, "
    "offline AI categorization using Naive Bayes, a local chat assistant, and bank statement import utilities with duplicate transaction detection."
)

SYSTEM_SW_EXPS = (
    "The project integrates several system software tools and libraries to function:\n\n"
    "1. React.js: Manages the Single Page Application UI. It dynamically updates page components using virtual DOM manipulation "
    "when transaction parameters change.\n\n"
    "2. Flask (Python): Coordinates REST API routes and business logic. It queries the local MySQL instance via mysql-connector, "
    "processes authentication cookies, runs Naive Bayes categorization, and compiles PDF reports.\n\n"
    "3. MySQL Database: Coordinates data persistence. Enforces referential integrity (Cascades deletes) to keep transactions, "
    "accounts, and budget allocations in sync."
)

MAINTENANCE_EXP = (
    "1. Corrective Maintenance: Resolving runtime issues, such as resolving statement parsing discrepancies or balance calculation errors.\n\n"
    "2. Adaptive Maintenance: Updating frontend and backend dependencies to keep the application compatible with updated browsers and library versions.\n\n"
    "3. Perfective Maintenance: Indexing frequently queried database columns (e.g. account_id and user_id) to improve transaction page load speeds."
)

SUMMARY_TEXT = (
    "FinWise AI is a complete, offline-first personal finance management system. The application coordinates financial tracking across "
    "multiple accounts, including bank accounts, cash, UPI wallets, credit cards, investments, and loans. By utilizing local data "
    "management and custom classification algorithms, the system provides personal finance tools while keeping user data secure."
)

# ------------------ GLOBAL IMPLEMENTATION DETAILS ------------------
IMP_FRONTEND = (
    "The Presentation Layer is developed as a Single Page Application (SPA) using React.js and Vite. "
    "Vite coordinates development servers and compiles files into static assets. "
    "Routing parameters are configured using React Router to navigate between Dashboard, Transactions, Accounts, Budgets, "
    "Savings Goals, and Analytics pages. State parameters are managed via local Hooks, such as useState for component variables "
    "and useEffect to fetch database summaries via REST API calls. "
    "Bootstrap CSS styles layout elements to render panels and forms that support responsive resizing. "
    "A custom theme state reads the user profile table to toggle light, dark, or system stylesheets dynamically. "
    "Browser authentication checks JWT tokens stored inside httpOnly cookie parameters, automatically redirecting logged-out "
    "users back to the login screen to protect internal dashboards."
)

IMP_BACKEND = (
    "The Application Layer is developed in Python using the Flask micro-framework. "
    "Flask handles incoming REST API calls, routing requests to corresponding controller functions. "
    "Security is coordinated via a custom @token_required decorator function that intercepts requests, "
    "extracts the JWT session cookie, validates the cryptographic signature using PyJWT, and fetches the user record. "
    "Database operations utilize a dedicated connection pool wrapping mysql.connector. "
    "When transaction edits or goals contributions occur, the Flask backend validates payloads, executes "
    "the necessary SQL commands inside database transactions, and returns standard JSON response payloads."
)

IMP_DATABASE = (
    "The Data Layer is persistent inside a local MySQL relational database schema. "
    "The schema comprises tables for users, accounts, transactions, budgets, savings goals, goal contributions, "
    "and statement imports. Referential integrity is enforced using foreign keys with CASCADE delete constraints. "
    "For example, deleting an account automatically clears all its transactions, keeping the ledger consistent. "
    "Queries are executed using parameterized statements to safeguard against SQL injection exploits. "
    "Critical database balance updates occur inside explicit transaction blocks, confirming updates "
    "are completed successfully before committing changes to disk."
)

IMP_AI_CLASSIFY = (
    "The local AI categorization module is developed natively in Python without relying on external cloud APIs, internet connectivity, or heavy third-party machine learning dependencies. "
    "It implements a Custom Multinomial Naive Bayes classification algorithm designed to execute with near-zero latency entirely on the host machine's CPU.\n\n"
    "1. Feature Extraction & Vocabulary Pipeline:\n"
    "On startup and dynamically during prediction queries, the engine establishes a dual-source training corpus. It combines a static domain taxonomy of 11 distinct financial categories "
    "(Food, Travel, Shopping, Medical, Entertainment, Bills, Groceries, Education, Insurance, Fuel, and Salary) with up to 500 historical transaction descriptions retrieved from the local MySQL database. "
    "Input transaction descriptions (e.g., 'Swiggy Dinner' or 'Amazon Electronics') are normalized and tokenized into lowercase alphanumeric word arrays W = {w1, w2, ..., wk}.\n\n"
    "2. Bayes' Theorem & Logarithmic Formulation:\n"
    "The probability of category class cj given word tokens W is formulated via Bayes' Theorem:\n\n"
    "    P(cj | W) = [ P(cj) * Product( P(wi | cj) ) ] / P(W)\n\n"
    "Because multiplying many fractional probabilities leads to floating-point numerical underflow, the calculation is computed in logarithmic space:\n\n"
    "    log P(cj | W) = log P(cj) + Sum( log P(wi | cj) )\n\n"
    "3. Laplace (Add-1) Smoothing:\n"
    "To handle out-of-vocabulary terms and eliminate zero-probability multiplication errors, Laplace smoothing is applied to both class priors and word likelihoods:\n\n"
    "    P(cj) = ( Doc_Count(cj) + 1 ) / ( Total_Docs + |C| )\n\n"
    "    P(wi | cj) = ( Word_Count(wi, cj) + 1 ) / ( Total_Words(cj) + |V| )\n\n"
    "where |C| is the total number of target categories (11), |V| is the unique vocabulary size, and Total_Words(cj) is the total count of words in category cj.\n\n"
    "4. Confidence Estimation & Fallback Decision Boundary:\n"
    "To generate interpretable percentage confidence values without numerical overflow, log scores are normalized using an exponent-shift transformation:\n\n"
    "    Normalized_Prob(cj) = exp( score(cj) - max_score )\n\n"
    "    Confidence(c_best) = [ Normalized_Prob(c_best) / Sum(Normalized_Prob) ] * 100%\n\n"
    "If the maximum confidence exceeds the 45% threshold and matches recognized vocabulary keywords, the predicted category is returned. Otherwise, the engine safely falls back to 'Other' (matched=False), allowing the user to assign the category manually."
)

IMP_CHAT_ASSIST = (
    "The Financial Chat Assistant operates locally as an interactive query utility. "
    "It implements keyword intent matching combined with database summaries. "
    "User queries are parsed into tokens and evaluated against keyword arrays. "
    "For instance, queries containing 'balance' match the account snapshot category, "
    "while queries with 'budget' trigger budget status. "
    "If a match is found, the system queries the database to build a dynamic report showing "
    "total cash balances, goal savings, or budgets exceeding 80% capacity. "
    "If no intent is matched, it queries help arrays or falls back to default guide prompts."
)

IMP_STATEMENT = (
    "Statement importing allows users to load transactions from bank statement files. "
    "The backend parses CSV statement fields using the Python csv package, Excel files using openpyxl, "
    "and text-based PDF files using pdfplumber to extract transaction dates, descriptions, and amounts. "
    "To prevent importing the same data twice, the backend computes a SHA-256 hash of the uploaded file "
    "and queries the statement_imports table. If a duplicate hash is found, it blocks the process. "
    "Additionally, it compares individual date, description, and amount values against existing entries "
    "to flag potential duplicate records in the preview grid before saving."
)

IMP_LEDGER = (
    "The bookkeeping system is built on a double-entry ledger engine. "
    "Logging manual transactions adjusts balances. Income adds to the account balance, "
    "while Expense subtracts from it. For Transfers, the engine logs matching ledger entries "
    "representing a debit from the source account and a credit to the destination account "
    "within a single SQL transaction. "
    "The ledger fetches transactions chronologically and calculates a running balance: "
    "Running Balance = Opening Balance + Credits - Debits, ensuring the ledger remains balanced."
)

ARCH_EXP = (
    "System design is the process of transforming the system requirements into a structured plan for building the actual software. "
    "It describes how various components interact, how data flows, and how users engage with the application. "
    "The system follows a three-tier architecture consisting of the presentation layer, application layer, and data layer."
)

BIB_TEXT = (
    "1. Roger S. Pressman, Software Engineering: A Practitioner’s Approach, McGraw-Hill Education.\n"
    "2. Ian Sommerville, Software Engineering, Pearson Education.\n"
    "3. Christopher D. Manning, Prabhakar Raghavan, & Hinrich Schütze, Introduction to Information Retrieval (Chapter 13: Naive Bayes text classification), Cambridge University Press.\n"
    "4. React Official Documentation - https://react.dev (Frontend framework reference).\n"
    "5. Flask micro-framework Documentation - https://flask.palletsprojects.com (REST API routing reference).\n"
    "6. MySQL Database Documentation - https://dev.mysql.com/doc (Database design reference)."
)

OBJECTIVES = [
    "Track available balances across Bank, Cash, UPI, Credit Card, Loans, and Investment accounts.",
    "Provide account-wise ledger transactions with debit, credit, and running balance rules.",
    "Import bank statement files (CSV, Excel, PDF) and check for duplicate transactions.",
    "Use local Multinomial Naive Bayes classification to categorize transactions based on description text.",
    "Implement a rule-based offline chat assistant to answer financial queries from database facts.",
    "Enable category-wise budgeting and savings goal contribution tracking.",
    "Generate monthly analytics summaries and export transactions in CSV and PDF formats."
]

DRAWBACKS = [
    "Lack of Centralization: Cash, UPI, credit cards, and loan balances are tracked across separate apps, preventing a unified view.",
    "Data Security and Privacy Risks: Online budget apps store transaction histories on cloud servers, exposing them to potential data leaks.",
    "No Automatic Categorization (Offline): Spreadsheet users must manually assign categories to every transaction, increasing the manual tracking workload.",
    "Internet Dependency: Cloud services are unusable without active network access, limiting accessibility.",
    "Complicated Account Balances: Existing systems often struggle to track savings goals without counting them as standard expenses, which misrepresents available balances.",
    "No Real-Time Guidance: Static ledger books and spreadsheets do not alert users when budgets are close to being exceeded or provide on-demand answers to financial questions."
]

TESTING_OBJS = [
    "Confirm calculations are accurate across accounts, budgets, and savings goals.",
    "Verify the accuracy of the local Naive Bayes categorizer.",
    "Ensure user sessions are secure and API requests require token verification.",
    "Verify the CSV, Excel, and PDF statement processors parse files without errors.",
    "Ensure duplicate transactions are detected and handled correctly during imports."
]

FUTURE_ENH = [
    "Advanced ML Forecasting: Integrate regression models to forecast future utility expenses based on seasonal usage trends.",
    "Optical Character Recognition (OCR): Integrate an offline OCR library to extract transaction details directly from images of receipts.",
    "Automatic Statement Synchronization: Build secure integrations with open banking APIs to allow optional statement updates when internet access is available.",
    "Advanced Calculators: Add interactive planning tools for loan EMI schedules and credit card interest calculations.",
    "Mobile Application: Build a React Native client that shares the local database schema, enabling mobile tracking."
]

SCREENS = [
    ("LOGIN PAGE", "Input email and password, with options to register or trigger password resets."),
    ("REGISTER PAGE", "Create new account using name, email, and password."),
    ("DASHBOARD", "Financial summaries (Total, Balance, Savings), recent transactions list, and budget boundary alerts."),
    ("ACCOUNTS PAGE", "Add and view configured financial accounts."),
    ("TRANSACTIONS PAGE", "Ledger table displaying date, type, category, amount, and descriptions."),
    ("ADD TRANSACTION PAGE", "Input manual income, expense, or transfer details."),
    ("STATEMENT IMPORT PAGE", "Choose a statement file and preview parsed transactions."),
    ("BUDGET PAGE", "Set monthly category limits and monitor utilization progress bars."),
    ("SAVINGS GOALS PAGE", "View progress bars showing saved amounts against goal targets."),
    ("ANALYTICS PAGE", "Dynamic visual charts tracking category-wise expense breakdowns."),
    ("FINANCIAL CHAT PAGE", "Conversational chat interface to query database facts locally.")
]

# Table of Contents split structures
FRONT_MATTER_TOC = [
    ("ABSTRACT", "(i)"),
    ("ACKNOWLEDGEMENT", "(ii)"),
    ("LIST OF TABLES", "(iii)"),
    ("LIST OF FIGURES", "(iv)")
]

CHAPTERS_TOC = [
    ("1", "INTRODUCTION", "01"),
    ("1.1", "PROJECT INTRODUCTION", "01"),
    ("2", "WORKING ENVIRONMENT", "02"),
    ("2.1", "HARDWARE REQUIREMENT", "02"),
    ("2.2", "SOFTWARE REQUIREMENT", "02"),
    ("2.3", "SYSTEM SOFTWARE", "03"),
    ("3", "SYSTEM ANALYSIS", "05"),
    ("3.1", "FEASIBILITY STUDY", "05"),
    ("3.2", "EXISTING SYSTEM", "05"),
    ("3.3", "DRAWBACKS OF EXISTING SYSTEM", "06"),
    ("3.4", "PROPOSED SYSTEM", "06"),
    ("3.5", "BENEFITS OF PROPOSED SYSTEM", "07"),
    ("3.6", "SCOPE OF THE PROJECT", "07"),
    ("4", "SYSTEM DESIGN", "08"),
    ("4.1", "SYSTEM ARCHITECTURE", "08"),
    ("4.2", "SYSTEM DIAGRAMS", "09"),
    ("4.3", "DATABASE DESIGN", "12"),
    ("5", "PROJECT DESCRIPTION", "14"),
    ("5.1", "OBJECTIVE", "14"),
    ("5.2", "MODULE DESCRIPTION", "14"),
    ("5.3", "IMPLEMENTATION", "16"),
    ("5.4", "MAINTENANCE STRATEGY", "19"),
    ("6", "SYSTEM TESTING", "20"),
    ("6.1", "TESTING DEFINITION", "20"),
    ("6.2", "TESTING OBJECTIVE", "20"),
    ("6.3", "TYPES OF TESTING", "21"),
    ("6.4", "TEST CASES", "21"),
    ("7", "CONCLUSION", "23"),
    ("7.1", "SUMMARY", "23"),
    ("7.2", "FUTURE ENHANCEMENT", "23"),
    ("8", "APPENDIX", "25"),
    ("8.1", "SCREENSHOTS", "25"),
    ("8.2", "CODING", "26"),
    ("8.3", "DATA DICTIONARY", "32"),
    ("9", "BIBLIOGRAPHY AND REFERENCES", "35")
]

LIST_OF_FIGURES_DATA = [
    ("4.1", "SYSTEM ARCHITECTURE DIAGRAM", "08"),
    ("4.2", "USE CASE DIAGRAM", "09"),
    ("4.3", "CLASS DIAGRAM", "10"),
    ("4.4", "SEQUENCE DIAGRAM", "11"),
    ("4.5", "ERD DIAGRAM", "12"),
    ("4.6", "DATA FLOW DIAGRAM", "13"),
    ("8.1.1", "LOGIN PAGE", "25"),
    ("8.1.2", "REGISTER PAGE", "25"),
    ("8.1.3", "DASHBOARD", "25"),
    ("8.1.4", "ACCOUNTS PAGE", "25"),
    ("8.1.5", "TRANSACTIONS PAGE", "25"),
    ("8.1.6", "ADD TRANSACTION PAGE", "25"),
    ("8.1.7", "STATEMENT IMPORT PAGE", "25"),
    ("8.1.8", "BUDGET PAGE", "25"),
    ("8.1.9", "SAVINGS GOALS PAGE", "25"),
    ("8.1.10", "ANALYTICS PAGE", "25"),
    ("8.1.11", "FINANCIAL CHAT PAGE", "25")
]

LIST_OF_TABLES_DATA = [
    ("2.1", "HARDWARE REQUIREMENTS", "02"),
    ("2.2", "SOFTWARE REQUIREMENTS", "02"),
    ("3.1", "EXISTING SYSTEM VS PROPOSED SYSTEM", "06"),
    ("5.2", "API DOCUMENTATION", "18"),
    ("6.4", "TEST CASES", "21"),
    ("8.1", "KEY CODING MODULES", "26"),
    ("8.3", "DATA DICTIONARY", "32")
]

# Hardware requirements table format (Component | Requirement)
HW_TABLE_DATA = [
    ("Processor", "Intel Core i5 / AMD Ryzen 5 or comparable (2.0 GHz or above)"),
    ("RAM", "8 GB DDR4 or higher recommended"),
    ("Hard Disk / SSD", "Solid State Drive with 500 MB free space"),
    ("Display", "1366 x 768 pixels or higher resolution"),
    ("Keyboard", "Standard QWERTY Keyboard"),
    ("Mouse", "Standard Optical Mouse"),
    ("Network", "Local Host Loopback Connection (Offline execution)")
]

# Software requirements table format (Software | Version / Requirement)
SW_TABLE_DATA = [
    ("Operating System", "Windows 10 / Windows 11 (64-bit)"),
    ("Python", "v3.10 or higher"),
    ("Node.js", "v18.0 or higher"),
    ("React", "v18.0 or higher"),
    ("Flask", "v3.0 or higher"),
    ("MySQL", "v8.0 or higher"),
    ("Browser", "Google Chrome, Microsoft Edge, Mozilla Firefox"),
    ("Code Editor", "Visual Studio Code / PyCharm")
]

COMPARISONS = [
    ("Data Management", "Manual or scattered across multiple apps", "Centralized, multi-account ledger database"),
    ("Categorization", "Manual category entry", "Local Multinomial Naive Bayes prediction"),
    ("Privacy & Security", "Data stored on external cloud servers", "Data stored locally in a private MySQL database"),
    ("Analytics", "Basic sheets or none", "Dynamic month-wise charts"),
    ("Budgeting", "Manual check or none", "Automatic utilization alerts (>80%)"),
    ("Statement Import", "Manual typing required", "Batch imports (CSV/Excel/PDF) with duplicate checks"),
    ("AI Assistance", "None or cloud chatbots", "Local, rule-based chatbot")
]

BENEFITS = [
    "100% Data Privacy: Personal files and logs stay stored locally in the MySQL instance.",
    "Zero Internet Dependency: Once local dependencies are set up, the application runs entirely offline.",
    "Local Machine Learning: Predictions (Naive Bayes) do not connect to external servers.",
    "Ledger Audit Trails: Dynamic accounting updates keep multi-accounts reconciled."
]

# Chapter 5 modules (Purpose, Working, Input, Processing, Output)
MODULES = [
    {
        "name": "Authentication Module",
        "purpose": "Manages user registration, secure login, profile edits, and preferences.",
        "working": "Encrypts user passwords on signup using scrypt, validates on login, and registers browser session cookies.",
        "input": "User name, email, password, theme details.",
        "processing": "Scrypt hashing, JWT generation, secure cookie settings.",
        "output": "Session verification, personalized view profile."
    },
    {
        "name": "Account Management Module",
        "purpose": "Tracks current asset balances for multiple financial accounts.",
        "working": "Tracks bank balances, cash, UPI, credit card, loan, and investments, logging adjustments.",
        "input": "Account name, account type, opening balance.",
        "processing": "Real-time query calculations, updating current_balance records.",
        "output": "Aggregated current balances on screens."
    },
    {
        "name": "Transaction Management Module",
        "purpose": "Manages manual income, expense, and transfer records.",
        "working": "Records financial entries and automatically adjusts the corresponding account balances.",
        "input": "Type, category, amount, description, source/destination accounts.",
        "processing": "Applies debits and credits to corresponding database balances.",
        "output": "Refreshed dashboard aggregates and ledger records."
    },
    {
        "name": "Statement Import Module",
        "purpose": "Parses statements (CSV, Excel, PDF) into transaction lists.",
        "working": "Processes statements, checks files against hashes, and parses date, amount, and description fields.",
        "input": "CSV, Excel, or text-based PDF statement file.",
        "processing": "Parses files, checks hashes, and maps data columns.",
        "output": "Preview grid of transactions."
    },
    {
        "name": "AI Categorization Module",
        "purpose": "Categorizes transaction descriptions using a local Naive Bayes categorizer.",
        "working": "Tokenizes input strings and computes probabilities based on pre-defined keywords and user transaction history.",
        "input": "Transaction description string (e.g. 'Swiggy Dinner').",
        "processing": "Calculates probability scores for each category.",
        "output": "Suggested category with confidence level."
    },
    {
        "name": "Budget Management Module",
        "purpose": "Enables category budgeting limits and tracks monthly spending.",
        "working": "Defines category-wise boundaries and compares actual expenses to alert users when limits are exceeded.",
        "input": "Category, target month, limit amount.",
        "processing": "Aggregates monthly expense totals and compares them to limits.",
        "output": "Dashboard boundary warnings."
    },
    {
        "name": "Savings Goal Module",
        "purpose": "Manages savings goals and contributions.",
        "working": "Deducts contributions from a source account and updates goal saved totals.",
        "input": "Goal name, target amount, deadline, contribution amount.",
        "processing": "Creates contribution records and updates balances.",
        "output": "Goal progress tracking charts."
    },
    {
        "name": "Analytics Module",
        "purpose": "Provides visual charts showing financial trends.",
        "working": "Processes expense category totals and renders charts.",
        "input": "Date ranges, account filters.",
        "processing": "Queries database and compiles monthly cash flow aggregates.",
        "output": "Interactive graphs on the interface."
    },
    {
        "name": "Financial Chat Assistant",
        "purpose": "Conversational assistant answering help and database questions.",
        "working": "Tokenizes queries and matches them to help topics and database records locally.",
        "input": "User query prompt.",
        "processing": "Matches keywords and fetches account balances.",
        "output": "Chat answer with suggested help chips."
    },
    {
        "name": "Report Generation Module",
        "purpose": "Generates PDF and CSV exports of financial summaries.",
        "working": "Renders transaction tables and aggregates totals into files.",
        "input": "Start date, end date, filter category.",
        "processing": "Generates CSV and PDF streams.",
        "output": "Downloadable file."
    }
]

CODE_FILES = [
    ("frontend/src/main.jsx", "Configures routing and auth session redirection.", "App() wrapper"),
    ("frontend/src/pages/Dashboard.jsx", "Aggregates sidebar layout and coordinates active views.", "Dashboard(), navigate(), render()"),
    ("backend/db.py", "Database connection pool wrapper.", "get_conn(), query()"),
    ("backend/auth.py", "Coordinates encryption hashes and JWT session middleware.", "hash_password(), verify_password(), token_required()"),
    ("backend/app.py", "Coordinates API endpoints and runs Naive Bayes categorizer.", "naive_bayes_category(), ai_insights(), categorize(), chat()")
]

# ------------------ GLOBAL SYSTEM DIAGRAM TEXTS ------------------
ARCH_DIAG = (
    "+-------------------------------------------------------------+\n"
    "|                 Presentation Layer (React UI)               |\n"
    "+-------------------------------------------------------------+\n"
    "                               | REST API (JSON/HTTP)\n"
    "                               v\n"
    "+-------------------------------------------------------------+\n"
    "|       Application Layer (Flask Backend Engine)              |\n"
    "|  +-------------+  +-------------+  +-------------+          |\n"
    "|  | JWT Session |  | Naive Bayes |  | Chat Matching|          |\n"
    "|  +-------------+  +-------------+  +-------------+          |\n"
    "+-------------------------------------------------------------+\n"
    "                               | SQL Queries (Connector)\n"
    "                               v\n"
    "+-------------------------------------------------------------+\n"
    "|             Data Layer (MySQL Local Database)               |\n"
    "+-------------------------------------------------------------+\n"
)

USECASE_DIAG = (
    "                   +----------------------------------+\n"
    "                   |           FINWISE AI             |\n"
    "                   |   +--------------------------+    |\n"
    "                   |   |      Register/Login      |    |\n"
    "                   |   +--------------------------+    |\n"
    "                   |   +--------------------------+    |\n"
    "  +---------+      |   |      Manage Accounts     |    |\n"
    "  |  User   |----->|   +--------------------------+    |\n"
    "  +---------+      |   +--------------------------+    |\n"
    "                   |   |    Log Manual/Import     |    |\n"
    "                   |   +--------------------------+    |\n"
    "                   |   +--------------------------+    |\n"
    "                   |   |      Query AI Chat       |    |\n"
    "                   |   +--------------------------+    |\n"
    "                   +----------------------------------+\n"
)

CLASS_DIAG = (
    "+--------------------+     1      *     +--------------------+\n"
    "|       User         |----------------->|      Account       |\n"
    "| - id: int          |                  | - id: int          |\n"
    "| - name: string     |                  | - current_bal: dec |\n"
    "| + register()       |                  | + reconcile()      |\n"
    "+--------------------+                  +--------------------+\n"
    "          | 1                                     | 1\n"
    "          |                                       |\n"
    "          v *                                     v *\n"
    "+--------------------+                  +--------------------+\n"
    "|      Budget        |                  |    Transaction     |\n"
    "| - id: int          |                  | - id: int          |\n"
    "| - category: string |                  | - type: enum       |\n"
    "| - amount: decimal  |                  | - amount: decimal  |\n"
    "+--------------------+                  +--------------------+\n"
)

SEQ_DIAG = (
    "User          React UI          Flask API          Naive Bayes          MySQL DB\n"
    " |               |                  |                   |                   |\n"
    " |---(Input)---->|                  |                   |                   |\n"
    " |               |----(POST MNB)--->|                   |                   |\n"
    " |               |                  |----(Train Data)-->|                   |\n"
    " |               |                  |<---(Calculations)-|                   |\n"
    " |               |<---(Response)----|                   |                   |\n"
    " |<-(Suggest)----|                  |                   |                   |\n"
    " |---(Submit)--->|                  |                   |                   |\n"
    " |               |----(POST Tx)---->|                   |                   |\n"
    " |               |                  |-------------------------------------->| (INSERT)\n"
    " |               |<---(201 OK)------|                   |                   |\n"
    " |<-(Refresh)----|                  |                   |                   |\n"
)

# Database tables schema data
DB_TABLES_DATA = {
    "USERS": {
        "desc": "Stores core user profile data and secure credentials.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique ID of the user"),
            ("name", "VARCHAR(100)", "-", "NO", "Full name of the user"),
            ("email", "VARCHAR(120)", "UNIQUE", "NO", "Primary login email address"),
            ("password", "VARCHAR(255)", "-", "NO", "Secure scrypt password hash"),
            ("created_at", "TIMESTAMP", "-", "NO", "Account creation date")
        ]
    },
    "ACCOUNTS": {
        "desc": "Maintains user accounts and their current balances.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique account ID"),
            ("user_id", "INT", "FK", "NO", "User ID mapping"),
            ("account_name", "VARCHAR(100)", "-", "NO", "User assigned account name"),
            ("account_type", "ENUM", "-", "NO", "Bank, Cash, UPI, Credit Card, Loan, Investment"),
            ("opening_balance", "DECIMAL(12,2)", "-", "YES", "Starting account balance"),
            ("current_balance", "DECIMAL(12,2)", "-", "YES", "Real-time running balance")
        ]
    },
    "TRANSACTIONS": {
        "desc": "Logs all income, expense, and transfer movements.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique transaction ID"),
            ("user_id", "INT", "FK", "NO", "Owner user ID"),
            ("account_id", "INT", "FK", "NO", "Primary account ID source"),
            ("type", "ENUM", "-", "NO", "Income, Expense, Transfer"),
            ("category", "VARCHAR(100)", "-", "YES", "Category classification"),
            ("amount", "DECIMAL(12,2)", "-", "NO", "Numerical transaction amount"),
            ("description", "VARCHAR(255)", "-", "YES", "Memo/note description"),
            ("transaction_date", "DATE", "-", "NO", "Actual financial date")
        ]
    },
    "BUDGETS": {
        "desc": "Stores monthly category limits.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique budget ID"),
            ("user_id", "INT", "FK", "NO", "User ID mapping"),
            ("category", "VARCHAR(100)", "-", "NO", "Target expense category"),
            ("month_year", "VARCHAR(7)", "-", "NO", "Format: YYYY-MM"),
            ("budget_amount", "DECIMAL(12,2)", "-", "NO", "Monthly spending limit")
        ]
    },
    "SAVINGS_GOALS": {
        "desc": "Tracks target savings markers.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique goal ID"),
            ("user_id", "INT", "FK", "NO", "User ID mapping"),
            ("goal_name", "VARCHAR(100)", "-", "NO", "Goal name (e.g. laptop, trip)"),
            ("target_amount", "DECIMAL(12,2)", "-", "NO", "Target money required"),
            ("saved_amount", "DECIMAL(12,2)", "-", "YES", "Total amount saved"),
            ("deadline", "DATE", "-", "YES", "Target target date")
        ]
    },
    "GOAL_CONTRIBUTIONS": {
        "desc": "Logs goal deposits and withdrawals.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique contribution record"),
            ("user_id", "INT", "FK", "NO", "User ID mapping"),
            ("goal_id", "INT", "FK", "NO", "Savings goal target"),
            ("account_id", "INT", "FK", "NO", "Deducted/added source account"),
            ("action", "ENUM", "-", "NO", "Deposit, Withdraw"),
            ("amount", "DECIMAL(12,2)", "-", "NO", "Transferred contribution amount")
        ]
    },
    "STATEMENT_IMPORTS": {
        "desc": "Maintains details of imported bank statements.",
        "cols": [
            ("id", "INT", "PK", "NO", "Unique import task ID"),
            ("user_id", "INT", "FK", "NO", "Import user mapping"),
            ("account_id", "INT", "FK", "NO", "Target account mapping"),
            ("file_name", "VARCHAR(255)", "-", "NO", "Imported statement file name"),
            ("file_hash", "CHAR(64)", "-", "NO", "SHA-256 hash of statement (prevents re-imports)"),
            ("imported_rows", "INT", "-", "NO", "Number of imported entries")
        ]
    }
}

# Test cases (TEST CASE ID | TEST CASE | INPUT | EXPECTED OUTPUT | ACTUAL OUTPUT | STATUS)
TEST_CASES = [
    ("TC001", "User Registration", "Submit sign-up form with unique email.", "User account created and saved in user table.", "User account created and saved in user table.", "PASS"),
    ("TC002", "User Login", "Enter valid registered credentials.", "Access token generated, login success.", "Access token generated, login success.", "PASS"),
    ("TC003", "Invalid Login", "Enter incorrect password or email.", "Error message displayed.", "Error message displayed.", "PASS"),
    ("TC004", "Create Account", "Add Bank Account, opening balance Rs 10000.", "Account created in DB, current_balance is 10000.", "Account created in DB, current_balance is 10000.", "PASS"),
    ("TC005", "Add Expense Entry", "Record manual Expense of Rs 1500.", "Deducts Rs 1500 from bank balance.", "Deducts Rs 1500 from bank balance.", "PASS"),
    ("TC006", "Add Income Entry", "Record manual Income of Rs 25000.", "Adds Rs 25000 to bank balance.", "Adds Rs 25000 to bank balance.", "PASS"),
    ("TC007", "Add Transfer Entry", "Record Transfer of Rs 3000 from Bank to UPI.", "Bank decremented by 3000, UPI incremented by 3000.", "Bank decremented by 3000, UPI incremented by 3000.", "PASS"),
    ("TC008", "Ledger calculation", "View Ledger of Cash account.", "Displays running balance: opening + credits - debits.", "Displays running balance: opening + credits - debits.", "PASS"),
    ("TC009", "Upload CSV statement", "Upload valid bank statement CSV file.", "Parses file, displays grid preview of rows.", "Parses file, displays grid preview of rows.", "PASS"),
    ("TC010", "Duplicate check", "Upload same statement CSV twice.", "Flags rows already present as duplicate.", "Flags rows already present as duplicate.", "PASS"),
    ("TC011", "Naive Bayes Categorizer", "Provide text 'Swiggy Dinner'.", "Returns Food category with confidence.", "Returns Food category with confidence.", "PASS"),
    ("TC012", "Set category budget", "Define Rs 10000 limit for Food.", "Budget added to table for current month-year.", "Budget added to table for current month-year.", "PASS"),
    ("TC013", "Budget limit warning", "Log food expense pushing total to Rs 8500.", "Dashboard displays warning alert (usage >80%).", "Dashboard displays warning alert (usage >80%).", "PASS"),
    ("TC014", "Create goal contribution", "Contribute Rs 5000 from Bank to Laptop Goal.", "Laptop saved amount increases, Bank decremented.", "Laptop saved amount increases, Bank decremented.", "PASS"),
    ("TC015", "Chat help request", "Submit question: 'how to add transfer?'.", "Returns help answer for transfer transactions.", "Returns help answer for transfer transactions.", "PASS"),
    ("TC016", "Chat data query", "Submit question: 'what is my balance?'.", "Queries database, returns balance summary.", "Queries database, returns balance summary.", "PASS"),
    ("TC017", "Export reports", "Request CSV transaction report download.", "Generates CSV byte stream download.", "Generates CSV byte stream download.", "PASS"),
    ("TC018", "Session Timeout / Logout", "Click logout button.", "Access token cookie cleared, session terminated.", "Access token cookie cleared, session terminated.", "PASS")
]

# API Endpoints (42 routes)
API_ENDPOINTS = [
    ("GET", "/", "Serves frontend index.html page.", "No", "None", "HTML Page Stream"),
    ("POST", "/api/register", "Register a new user.", "No", "name, email, password", "success / error message"),
    ("POST", "/api/login", "Logs in user and sets secure JWT httpOnly cookies.", "No", "email, password", "user info or error"),
    ("POST", "/api/refresh", "Refresh user session JWT token.", "No", "cookie token", "token refresh confirm"),
    ("POST", "/api/logout", "Clears cookies and invalidates session.", "Yes", "None", "logout confirm message"),
    ("POST", "/api/password/forgot", "Initiate password reset (generates local token).", "No", "email", "reset instructions"),
    ("POST", "/api/email/verify", "Verify email address via token.", "No", "token", "verification status"),
    ("POST", "/api/password/reset", "Reset password with token.", "No", "token, password", "success / error status"),
    ("GET", "/api/profile", "Fetch logged-in user profile details.", "Yes", "cookie token", "user profile JSON"),
    ("PUT", "/api/profile", "Update user profile details.", "Yes", "name, email", "updated profile details"),
    ("PUT", "/api/profile/password", "Update user login password.", "Yes", "old_password, new_password", "success / error status"),
    ("GET", "/api/dashboard", "Fetch combined financial stats and overview.", "Yes", "cookie token", "aggregated balances and alerts"),
    ("GET", "/api/accounts", "Fetch all user account objects.", "Yes", "cookie token", "list of accounts"),
    ("POST", "/api/accounts", "Add a new financial account.", "Yes", "name, type, opening_balance", "created account object"),
    ("PUT", "/api/accounts/<int:account_id>", "Edit account parameters.", "Yes", "name, credit_limit, last4", "updated account object"),
    ("DELETE", "/api/accounts/<int:account_id>", "Remove account and related transactions.", "Yes", "account_id", "success confirmation"),
    ("GET", "/api/transactions", "Fetch transaction list with filters.", "Yes", "page, account_id, search", "paginated transaction array"),
    ("GET", "/api/ledger", "Fetch double-entry ledger rows.", "Yes", "account_id", "ledger statements with balances"),
    ("POST", "/api/transactions", "Create manual transaction.", "Yes", "type, amount, account_id, date", "created transaction object"),
    ("DELETE", "/api/transactions/<int:tid>", "Remove transaction entry.", "Yes", "tid", "success confirmation"),
    ("GET", "/api/budgets", "Fetch monthly budget limits & spent statistics.", "Yes", "cookie token", "budget utilization list"),
    ("POST", "/api/budgets", "Create new budget limit.", "Yes", "category, month_year, budget_amount", "budget confirm"),
    ("PUT", "/api/budgets/<int:budget_id>", "Edit budget limit.", "Yes", "category, budget_amount", "updated budget"),
    ("DELETE", "/api/budgets/<int:budget_id>", "Delete budget limit.", "Yes", "budget_id", "delete confirm"),
    ("GET", "/api/goals", "Fetch savings goals list.", "Yes", "cookie token", "savings goals array"),
    ("POST", "/api/goals", "Create a new savings goal.", "Yes", "goal_name, target_amount, deadline", "created goal object"),
    ("PUT", "/api/goals/<int:goal_id>", "Update goal details.", "Yes", "goal_name, target_amount, deadline", "updated goal object"),
    ("DELETE", "/api/goals/<int:goal_id>", "Delete savings goal.", "Yes", "goal_id", "delete confirm"),
    ("POST", "/api/goals/<int:goal_id>/contributions", "Add savings goal deposit/withdrawal.", "Yes", "account_id, action, amount", "updated goal object"),
    ("GET", "/api/goals/<int:goal_id>/contributions", "Fetch contribution history for goal.", "Yes", "goal_id", "contributions array"),
    ("GET", "/api/savings/activity", "Fetch total goal activities log.", "Yes", "cookie token", "list of all contributions"),
    ("GET", "/api/analytics/category", "Group expenses by category.", "Yes", "cookie token", "categories with total sums"),
    ("GET", "/api/analytics/monthly", "Fetch monthly income/expense trends.", "Yes", "cookie token", "month lists with cash flow stats"),
    ("GET", "/api/reports/csv", "Export all transactions in CSV format.", "Yes", "start_date, end_date", "CSV file download"),
    ("POST", "/api/ai/categorize", "Predict category from text description.", "Yes", "description", "predicted category, confidence"),
    ("GET", "/api/ai/insights", "Fetch automated data insights.", "Yes", "cookie token", "health score and text list"),
    ("POST", "/api/ai/chat", "Submit prompt to offline chat advisor.", "Yes", "message", "bot answer text & chips"),
    ("POST", "/api/statements/preview", "Upload statement and check duplicates.", "Yes", "file (multipart)", "parsed rows preview array"),
    ("POST", "/api/statements/confirm", "Import confirmed transactions.", "Yes", "transactions (array)", "import statistics summary"),
    ("GET", "/api/statements/history", "View history of imported statement files.", "Yes", "cookie token", "statement imports list"),
    ("DELETE", "/api/statements/<int:import_id>", "Undo statement import and delete rows.", "Yes", "import_id", "undo confirmation"),
    ("GET", "/<path:path>", "Fallback route to serve static UI files.", "No", "None", "Asset File Stream")
]

# Helper for cell margins in Word tables
def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_paragraph_with_spacing(doc, text, style=None, space_before=0, space_after=6, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15):
    p = doc.add_paragraph(text, style=style)
    p.alignment = align
    p_format = p.paragraph_format
    p_format.space_before = Pt(space_before)
    p_format.space_after = Pt(space_after)
    p_format.line_spacing = line_spacing
    return p

def add_code_block(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.right_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Courier New'
    run.font.size = Pt(8.5)
    return p

def add_structured_text_to_docx(doc, text_content):
    paragraphs = text_content.strip().split("\n\n")
    for block in paragraphs:
        block = block.strip()
        if not block:
            continue
        if any(sym in block for sym in ["P(cj | W)", "log P(cj", "P(wi | cj)", "Normalized_Prob", "Confidence("]):
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            for line in lines:
                p = add_paragraph_with_spacing(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=2, space_after=2)
                p.runs[0].font.name = 'Courier New'
                p.runs[0].font.size = Pt(10)
                p.runs[0].font.bold = True
        elif block.startswith(("1. ", "2. ", "3. ", "4. ", "5. ")):
            if ":\n" in block:
                header, body = block.split(":\n", 1)
                p = add_paragraph_with_spacing(doc, "", space_before=6, space_after=2, align=WD_ALIGN_PARAGRAPH.LEFT)
                p.add_run(header + ":").bold = True
                add_paragraph_with_spacing(doc, body.strip(), align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=4)
            elif ":" in block.split("\n")[0]:
                first_line, rest = block.split("\n", 1) if "\n" in block else (block, "")
                p = add_paragraph_with_spacing(doc, "", space_before=6, space_after=2, align=WD_ALIGN_PARAGRAPH.LEFT)
                p.add_run(first_line).bold = True
                if rest.strip():
                    add_paragraph_with_spacing(doc, rest.strip(), align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=4)
            else:
                add_paragraph_with_spacing(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=4, space_after=4)
        else:
            add_paragraph_with_spacing(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=3, space_after=6)

# Generate Word (.docx) document
def build_docx_report():
    print("Building MS Word Project Report...")
    doc = docx.Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1)
        
    # Styles config
    styles = doc.styles
    normal = styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(12)
    
    # ------------------ COVER PAGE ------------------
    add_paragraph_with_spacing(doc, "\n\n\n\n\nPROJECT REPORT ON", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    
    p_title = add_paragraph_with_spacing(doc, "FINWISE AI", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    p_title.runs[0].font.size = Pt(28)
    p_title.runs[0].font.bold = True
    p_title.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    p_sub = add_paragraph_with_spacing(doc, "SMART PERSONAL FINANCE MANAGEMENT SYSTEM", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p_sub.runs[0].font.size = Pt(14)
    p_sub.runs[0].font.bold = True
    p_sub.runs[0].font.color.rgb = RGBColor(55, 65, 81)
    
    add_paragraph_with_spacing(doc, "\n\nSubmitted in partial fulfillment of the requirements for the award of the degree of", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    
    p_degree = add_paragraph_with_spacing(doc, "MASTER OF COMPUTER APPLICATIONS / BACHELOR OF COMPUTER APPLICATIONS", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)
    p_degree.runs[0].font.bold = True
    p_degree.runs[0].font.size = Pt(12)
    
    add_paragraph_with_spacing(doc, "Under the guidance of\n" + GUIDE_NAME, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=48)
    
    add_paragraph_with_spacing(doc, "Submitted by:\n" + STUDENT_NAME + "\nRegister Number: " + REGISTER_NUMBER, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=60)
    
    add_paragraph_with_spacing(doc, f"DEPARTMENT OF COMPUTER APPLICATIONS\n{INSTITUTION_NAME}\nAcademic Year: {ACADEMIC_YEAR}", align=WD_ALIGN_PARAGRAPH.CENTER)
    
    doc.add_page_break()
    
    # ------------------ CERTIFICATE PAGE ------------------
    p = add_paragraph_with_spacing(doc, "CERTIFICATE", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    cert_text = (
        f"This is to certify that the project report entitled 'FinWise AI - Smart Personal Finance Management System' "
        f"is a bonafide record of work done by {STUDENT_NAME} (Reg No: {REGISTER_NUMBER}) in partial fulfillment of the "
        f"requirements for the award of the degree of MCA/BCA in Department of Computer Applications, "
        f"{INSTITUTION_NAME} during the academic year {ACADEMIC_YEAR}."
    )
    add_paragraph_with_spacing(doc, cert_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=12, space_after=48)
    
    add_paragraph_with_spacing(doc, "Project Guide\t\t\tHead of the Department", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=60)
    add_paragraph_with_spacing(doc, "Date: ____________\t\t\tExternal Examiner", align=WD_ALIGN_PARAGRAPH.LEFT)
    
    doc.add_page_break()
    
    # ------------------ DECLARATION PAGE ------------------
    p = add_paragraph_with_spacing(doc, "DECLARATION", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    decl_text = (
        f"I, {STUDENT_NAME}, hereby declare that the project work entitled 'FinWise AI - Smart Personal Finance Management System' "
        f"submitted to the Department of Computer Applications, {INSTITUTION_NAME}, is a record of independent project work carried out "
        f"by me under the supervision of {GUIDE_NAME}, Project Guide, and that it has not previously formed the basis for the award of "
        f"any other degree or similar titles."
    )
    add_paragraph_with_spacing(doc, decl_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=12, space_after=48)
    
    add_paragraph_with_spacing(doc, f"Place: ____________\nDate: ____________\t\t\t\t\t{STUDENT_NAME}", align=WD_ALIGN_PARAGRAPH.LEFT)
    
    doc.add_page_break()
    
    # ------------------ ACKNOWLEDGEMENT PAGE ------------------
    p = add_paragraph_with_spacing(doc, "ACKNOWLEDGEMENT", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    ack_text = (
        "I express my deepest gratitude to all who provided guidance and support during the design and development "
        "of FinWise AI. I thank our Institution Principal and Head of the Department for providing the resources and "
        "facilities needed to execute this project successfully.\n\n"
        f"I am deeply indebted to my project guide, {GUIDE_NAME}, for their valuable guidance, structural recommendations, "
        "and critical reviews during the software engineering and testing lifecycles.\n\n"
        "Finally, I thank my family members and peers for their continuous support and helpful feedback during "
        "the user acceptance testing iterations."
    )
    add_paragraph_with_spacing(doc, ack_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=24)
    
    doc.add_page_break()
    
    # ------------------ ABSTRACT PAGE ------------------
    p = add_paragraph_with_spacing(doc, "ABSTRACT", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    abs_text = (
        "FinWise AI is a comprehensive, offline-first personal finance management system designed to assist users in tracking their "
        "educational and professional financial transactions, managing budgets, and planning savings goals. Traditional finance apps "
        "depend on cloud databases and external servers, raising concerns about data privacy and internet reliability. FinWise AI resolves "
        "these issues by utilizing a local-first deployment model where user records, statements, and intelligent advice are processed "
        "entirely on the client’s machine.\n\n"
        "Central to the system is a local intelligent categorizer based on a Multinomial Naive Bayes category prediction model that matches "
        "transaction descriptions to categories without sending transaction logs to third-party services. Additionally, an offline rule-based "
        "chat assistant answers finance-related queries, retrieves real-time database summaries, and offers actionable financial insights.\n\n"
        "Using modern web technologies—a React frontend, a Flask (Python) backend, and a MySQL database—FinWise AI separates responsibilities "
        "through a classic three-tier architecture. The system supports multi-account ledgers (Bank, Cash, UPI, Loans, Credit Cards, "
        "Investments), bank statement imports (CSV, Excel, text-based PDF) with automatic duplicate detection, and visual month-wise analytics. "
        "By consolidating accounting principles with local artificial intelligence, FinWise AI significantly reduces manual tracking workloads, "
        "secures private financial data, and enables users to establish sound budgets and savings habits."
    )
    add_paragraph_with_spacing(doc, abs_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    doc.add_page_break()
    
    # ------------------ TABLE OF CONTENTS ------------------
    p = add_paragraph_with_spacing(doc, "TABLE OF CONTENTS", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    t_toc = doc.add_table(rows=1, cols=3)
    t_toc.style = 'Table Grid'
    hdr_cells = t_toc.rows[0].cells
    hdr_cells[0].text = 'S.NO'
    hdr_cells[1].text = 'TITLE'
    hdr_cells[2].text = 'PAGE NO.'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    # Front Matter Row (combined cell strings)
    row = t_toc.add_row()
    row.cells[0].text = ''
    row.cells[1].text = "ABSTRACT\nACKNOWLEDGEMENT\nLIST OF TABLES\nLIST OF FIGURES"
    row.cells[2].text = "(i)\n(ii)\n(iii)\n(iv)"
    for cell in row.cells:
        set_cell_margins(cell)
         
    # Chapters header
    row = t_toc.add_row()
    row.cells[0].text = 'CHAPTERS'
    row.cells[1].text = 'TITLE'
    row.cells[2].text = 'PAGE NO.'
    for cell in row.cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    # Combined Chapter sections as shown in reference image
    ch_rows = [
        ("1", "INTRODUCTION\n1.1 PROJECT INTRODUCTION", "01"),
        ("2", "WORKING ENVIRONMENT\n2.1 HARDWARE REQUIREMENT\n2.2 SOFTWARE REQUIREMENT\n2.3 SYSTEM SOFTWARE", "02"),
        ("3", "SYSTEM ANALYSIS\n3.1 FEASIBILITY STUDY\n3.2 EXISTING SYSTEM\n3.3 DRAWBACKS OF EXISTING SYSTEM\n3.4 PROPOSED SYSTEM\n3.5 BENEFITS OF PROPOSED SYSTEM\n3.6 SCOPE OF THE PROJECT", "05"),
        ("4", "SYSTEM DESIGN\n4.1 SYSTEM ARCHITECTURE\n4.2 SYSTEM DIAGRAMS\n4.3 DATABASE DESIGN", "08"),
        ("5", "PROJECT DESCRIPTION\n5.1 OBJECTIVE\n5.2 MODULE DESCRIPTION\n5.3 IMPLEMENTATION\n5.4 MAINTENANCE STRATEGY", "14"),
        ("6", "SYSTEM TESTING\n6.1 TESTING DEFINITION\n6.2 TESTING OBJECTIVE\n6.3 TYPES OF TESTING\n6.4 TEST CASES", "20"),
        ("7", "CONCLUSION\n7.1 SUMMARY\n7.2 FUTURE ENHANCEMENT", "23"),
        ("8", "APPENDIX\n8.1 SCREENSHOTS\n8.2 CODING\n8.3 DATA DICTIONARY", "25"),
        ("9", "BIBLIOGRAPHY AND REFERENCES", "35")
    ]
    for s_no, text, pg in ch_rows:
        row = t_toc.add_row()
        row.cells[0].text = s_no
        row.cells[1].text = text
        row.cells[2].text = pg
        for cell in row.cells:
            set_cell_margins(cell)
            
    doc.add_page_break()
    
    # ------------------ LIST OF TABLES PAGE ------------------
    p = add_paragraph_with_spacing(doc, "LIST OF TABLES", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    t_lot = doc.add_table(rows=1, cols=3)
    t_lot.style = 'Table Grid'
    hdr_cells = t_lot.rows[0].cells
    hdr_cells[0].text = 'TABLE NO'
    hdr_cells[1].text = 'TITLE'
    hdr_cells[2].text = 'PAGE NO'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for tbl_no, title, pg in LIST_OF_TABLES_DATA:
        row = t_lot.add_row()
        row.cells[0].text = tbl_no
        row.cells[1].text = title
        row.cells[2].text = pg
        for cell in row.cells:
            set_cell_margins(cell)
            
    doc.add_page_break()
    
    # ------------------ LIST OF FIGURES PAGE ------------------
    p = add_paragraph_with_spacing(doc, "LIST OF FIGURES", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    t_lof = doc.add_table(rows=1, cols=3)
    t_lof.style = 'Table Grid'
    hdr_cells = t_lof.rows[0].cells
    hdr_cells[0].text = 'FIGURE NO'
    hdr_cells[1].text = 'TITLE'
    hdr_cells[2].text = 'PAGE NO'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for fig_no, title, pg in LIST_OF_FIGURES_DATA:
        row = t_lof.add_row()
        row.cells[0].text = fig_no
        row.cells[1].text = title
        row.cells[2].text = pg
        for cell in row.cells:
            set_cell_margins(cell)
            
    doc.add_page_break()

    # ------------------ CHAPTER 1 ------------------
    add_paragraph_with_spacing(doc, "1. INTRODUCTION", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "1.1 PROJECT INTRODUCTION", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, INTRO_P1, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_paragraph_with_spacing(doc, PROBLEM_P1, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_paragraph_with_spacing(doc, MOTIVATION_P1, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_paragraph_with_spacing(doc, OVERVIEW_P1, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    doc.add_page_break()

    # ------------------ CHAPTER 2 ------------------
    add_paragraph_with_spacing(doc, "2. WORKING ENVIRONMENT", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "2.1 HARDWARE REQUIREMENT", style="Heading 2", space_before=6, space_after=6)
    
    add_paragraph_with_spacing(doc, "TABLE 2.1 HARDWARE REQUIREMENTS", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_hw = doc.add_table(rows=1, cols=2)
    t_hw.style = 'Table Grid'
    hdr_cells = t_hw.rows[0].cells
    hdr_cells[0].text = 'COMPONENT'
    hdr_cells[1].text = 'REQUIREMENT'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for comp, req in HW_TABLE_DATA:
        row = t_hw.add_row()
        row.cells[0].text = comp
        row.cells[1].text = req
        for cell in row.cells:
            set_cell_margins(cell)
            
    add_paragraph_with_spacing(doc, "2.2 SOFTWARE REQUIREMENT", style="Heading 2", space_before=18, space_after=6)
    
    add_paragraph_with_spacing(doc, "TABLE 2.2 SOFTWARE REQUIREMENTS", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_sw = doc.add_table(rows=1, cols=2)
    t_sw.style = 'Table Grid'
    hdr_cells = t_sw.rows[0].cells
    hdr_cells[0].text = 'SOFTWARE'
    hdr_cells[1].text = 'VERSION / REQUIREMENT'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for sw, req in SW_TABLE_DATA:
        row = t_sw.add_row()
        row.cells[0].text = sw
        row.cells[1].text = req
        for cell in row.cells:
            set_cell_margins(cell)
            
    add_paragraph_with_spacing(doc, "2.3 SYSTEM SOFTWARE", style="Heading 2", space_before=18, space_after=6)
    add_paragraph_with_spacing(doc, SYSTEM_SW_EXPS, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    doc.add_page_break()

    # ------------------ CHAPTER 3 ------------------
    add_paragraph_with_spacing(doc, "3. SYSTEM ANALYSIS", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "3.1 FEASIBILITY STUDY", style="Heading 2", space_before=6, space_after=6)
    
    add_paragraph_with_spacing(doc, "Technical Feasibility", style="Heading 3", space_before=4, space_after=4)
    add_paragraph_with_spacing(doc, "The system runs on React, Flask, and MySQL, which are widely-supported and lightweight tools. Since all AI/ML models run locally on the CPU, no expensive cloud services are required.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "Operational Feasibility", style="Heading 3", space_before=4, space_after=4)
    add_paragraph_with_spacing(doc, "The interface features a sidebar structure with forms and tables. Users can quickly enter details, preview imports, and chat in natural language, making the system easy to use.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "Economic Feasibility", style="Heading 3", space_before=4, space_after=4)
    add_paragraph_with_spacing(doc, "Built using free, open-source libraries, FinWise AI requires no ongoing server hosting costs, API charges, or cloud fees, making it highly cost-effective.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "3.2 EXISTING SYSTEM", style="Heading 2", space_before=12, space_after=6)
    add_paragraph_with_spacing(doc, EXISTING_SYS_TEXT, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "3.3 DRAWBACKS OF EXISTING SYSTEM", style="Heading 2", space_before=12, space_after=6)
    for idx, dw in enumerate(DRAWBACKS, 1):
        add_paragraph_with_spacing(doc, f"{idx}) {dw.split(': ', 1)[1] if ': ' in dw else dw}", space_after=4)
        
    add_paragraph_with_spacing(doc, "3.4 PROPOSED SYSTEM", style="Heading 2", space_before=12, space_after=6)
    add_paragraph_with_spacing(doc, PROP_SYS_TEXT, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12)
    
    add_paragraph_with_spacing(doc, "TABLE 3.1 EXISTING SYSTEM VS PROPOSED SYSTEM", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_comp = doc.add_table(rows=1, cols=3)
    t_comp.style = 'Table Grid'
    hdr_cells = t_comp.rows[0].cells
    hdr_cells[0].text = 'ASPECT'
    hdr_cells[1].text = 'EXISTING SYSTEM'
    hdr_cells[2].text = 'PROPOSED SYSTEM'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for aspect, ex, prop in COMPARISONS:
        row = t_comp.add_row()
        row.cells[0].text = aspect
        row.cells[1].text = ex
        row.cells[2].text = prop
        for cell in row.cells:
            set_cell_margins(cell)
            
    add_paragraph_with_spacing(doc, "3.5 BENEFITS OF PROPOSED SYSTEM", style="Heading 2", space_before=18, space_after=6)
    for ben in BENEFITS:
        add_paragraph_with_spacing(doc, ben, space_after=4)
        
    add_paragraph_with_spacing(doc, "3.6 SCOPE OF THE PROJECT", style="Heading 2", space_before=12, space_after=6)
    add_paragraph_with_spacing(doc, "The current scope covers single-user offline finance tracking including multiple asset ledgers, CSV statement parsing, automatic duplicate check parameters, and monthly budget alerts. Future scopes include adding OCR, time-series forecasting, and direct local bank connectivity.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    doc.add_page_break()

    # ------------------ CHAPTER 4 ------------------
    add_paragraph_with_spacing(doc, "4. SYSTEM DESIGN", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "4.1 SYSTEM ARCHITECTURE", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, ARCH_EXP, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "FIGURE 4.1 SYSTEM ARCHITECTURE DIAGRAM", style="Normal", space_before=12, space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    add_code_block(doc, ARCH_DIAG)
    
    add_paragraph_with_spacing(doc, "4.2 SYSTEM DIAGRAMS", style="Heading 2", space_before=12, space_after=6)
    
    add_paragraph_with_spacing(doc, "FIGURE 4.2 USE CASE DIAGRAM", style="Normal", space_before=6, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    add_code_block(doc, USECASE_DIAG)
    
    add_paragraph_with_spacing(doc, "FIGURE 4.3 CLASS DIAGRAM", style="Normal", space_before=8, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    add_code_block(doc, CLASS_DIAG)
    
    add_paragraph_with_spacing(doc, "FIGURE 4.4 SEQUENCE DIAGRAM", style="Normal", space_before=8, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    add_code_block(doc, SEQ_DIAG)
    
    add_paragraph_with_spacing(doc, "4.3 DATABASE DESIGN", style="Heading 2", space_before=12, space_after=6)
    
    for tbl_name, t_meta in DB_TABLES_DATA.items():
        add_paragraph_with_spacing(doc, f"TABLE: {tbl_name}", style="Heading 3", space_before=6, space_after=2)
        add_paragraph_with_spacing(doc, t_meta["desc"], space_after=4)
        
        t_db = doc.add_table(rows=1, cols=5)
        t_db.style = 'Table Grid'
        hdr_cells = t_db.rows[0].cells
        for idx, header in enumerate(["FIELD", "TYPE", "KEY", "NULL", "DESCRIPTION"]):
            hdr_cells[idx].text = header
            hdr_cells[idx].paragraphs[0].runs[0].font.bold = True
            set_cell_margins(hdr_cells[idx])
            
        for row_data in t_meta["cols"]:
            row = t_db.add_row()
            for idx, text in enumerate(row_data):
                row.cells[idx].text = text
                set_cell_margins(row.cells[idx])
                
    doc.add_page_break()

    # ------------------ CHAPTER 5 ------------------
    add_paragraph_with_spacing(doc, "5. PROJECT DESCRIPTION", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "5.1 OBJECTIVE", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, "The objective of FinWise AI is to deliver private, offline-first personal financial control. It establishes an accounting double-ledger that tracks transaction records across multiple accounts without connecting to cloud systems.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "5.2 MODULE DESCRIPTION", style="Heading 2", space_before=12, space_after=6)
    
    for idx, mod in enumerate(MODULES, 1):
        add_paragraph_with_spacing(doc, f"{idx}. {mod['name']}", style="Heading 3", space_before=6, space_after=2)
        
        p = add_paragraph_with_spacing(doc, "", space_after=2)
        p.add_run("Purpose: ").bold = True
        p.add_run(mod['purpose'])
        
        p = add_paragraph_with_spacing(doc, "", space_after=2)
        p.add_run("Working: ").bold = True
        p.add_run(mod['working'])
        
        p = add_paragraph_with_spacing(doc, "", space_after=2)
        p.add_run("Input: ").bold = True
        p.add_run(mod['input'])
        
        p = add_paragraph_with_spacing(doc, "", space_after=2)
        p.add_run("Processing: ").bold = True
        p.add_run(mod['processing'])
        
        p = add_paragraph_with_spacing(doc, "", space_after=6)
        p.add_run("Output: ").bold = True
        p.add_run(mod['output'])
        
    add_paragraph_with_spacing(doc, "5.3 IMPLEMENTATION", style="Heading 2", space_before=12, space_after=6)
    
    add_paragraph_with_spacing(doc, "Frontend Development (React, Vite, Bootstrap)", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_FRONTEND, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "Backend Development (Flask API, Python)", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_BACKEND, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "Database Implementation (MySQL)", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_DATABASE, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "AI/ML implementation (Multinomial Naive Bayes)", style="Heading 3", space_before=6, space_after=4)
    add_structured_text_to_docx(doc, IMP_AI_CLASSIFY)
    
    add_paragraph_with_spacing(doc, "Conversational Chat Engine", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_CHAT_ASSIST, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "Bank Statement Processing", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_STATEMENT, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "Double-Entry Ledger Engine", style="Heading 3", space_before=6, space_after=4)
    add_paragraph_with_spacing(doc, IMP_LEDGER, align=WD_ALIGN_PARAGRAPH.LEFT)
    
    add_paragraph_with_spacing(doc, "API Documentation", style="Heading 3", space_before=12, space_after=4)
    add_paragraph_with_spacing(doc, "TABLE 5.2 API DOCUMENTATION", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_api = doc.add_table(rows=1, cols=6)
    t_api.style = 'Table Grid'
    hdr_cells = t_api.rows[0].cells
    for idx, header in enumerate(["Method", "Endpoint", "Purpose", "Auth Required", "Payload Request", "Response Type"]):
        hdr_cells[idx].text = header
        hdr_cells[idx].paragraphs[0].runs[0].font.bold = True
        set_cell_margins(hdr_cells[idx])
        
    for method, path, purpose, auth, req, resp in API_ENDPOINTS:
        row = t_api.add_row()
        row.cells[0].text = method
        row.cells[1].text = path
        row.cells[2].text = purpose
        row.cells[3].text = auth
        row.cells[4].text = req
        row.cells[5].text = resp
        for cell in row.cells:
            set_cell_margins(cell)
            
    add_paragraph_with_spacing(doc, "5.4 MAINTENANCE STRATEGY", style="Heading 2", space_before=12, space_after=6)
    add_paragraph_with_spacing(doc, MAINTENANCE_EXP, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    doc.add_page_break()

    # ------------------ CHAPTER 6 ------------------
    add_paragraph_with_spacing(doc, "6. SYSTEM TESTING", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "6.1 TESTING DEFINITION", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, "System testing evaluates the integrated FinWise AI application to verify it meets design requirements. The testing process checks frontend components, backend API logic, and the local database connection as a unified system.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "6.2 TESTING OBJECTIVE", style="Heading 2", space_before=6, space_after=6)
    for idx, obj in enumerate(TESTING_OBJS, 1):
        add_paragraph_with_spacing(doc, f"{idx}. {obj}", style="List Bullet", space_after=4)
        
    add_paragraph_with_spacing(doc, "6.3 TYPES OF TESTING", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, "Unit, Integration, and end-to-end System testing are performed offline.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "6.4 TEST CASES", style="Heading 2", space_before=12, space_after=6)
    
    add_paragraph_with_spacing(doc, "TABLE 6.4 TEST CASES", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_tc = doc.add_table(rows=1, cols=6)
    t_tc.style = 'Table Grid'
    hdr_cells = t_tc.rows[0].cells
    for idx, header in enumerate(["TEST CASE ID", "TEST CASE", "INPUT", "EXPECTED OUTPUT", "ACTUAL OUTPUT", "STATUS"]):
        hdr_cells[idx].text = header
        hdr_cells[idx].paragraphs[0].runs[0].font.bold = True
        set_cell_margins(hdr_cells[idx])
        
    for id_val, scenario, inp, exp, act, status in TEST_CASES:
        row = t_tc.add_row()
        row.cells[0].text = id_val
        row.cells[1].text = scenario
        row.cells[2].text = inp
        row.cells[3].text = exp
        row.cells[4].text = act
        row.cells[5].text = status
        for cell in row.cells:
            set_cell_margins(cell)
            
    doc.add_page_break()

    # ------------------ CHAPTER 7 ------------------
    add_paragraph_with_spacing(doc, "7. CONCLUSION", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "7.1 SUMMARY", style="Heading 2", space_before=6, space_after=6)
    add_paragraph_with_spacing(doc, SUMMARY_TEXT, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    
    add_paragraph_with_spacing(doc, "7.2 FUTURE ENHANCEMENT", style="Heading 2", space_before=12, space_after=6)
    for idx, item in enumerate(FUTURE_ENH, 1):
        add_paragraph_with_spacing(doc, f"{idx}. {item}", style="List Bullet", space_after=4)
        
    doc.add_page_break()

    # ------------------ CHAPTER 8 ------------------
    add_paragraph_with_spacing(doc, "8. APPENDIX", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    
    add_paragraph_with_spacing(doc, "8.1 SCREENSHOTS", style="Heading 2", space_before=6, space_after=6)
    for idx, (name, scr_desc) in enumerate(SCREENS, 1):
        add_paragraph_with_spacing(doc, f"FIGURE 8.1.{idx}\n{name}", style="Normal", space_before=12, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
        add_paragraph_with_spacing(doc, scr_desc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12)
        
    add_paragraph_with_spacing(doc, "8.2 CODING", style="Heading 2", space_before=12, space_after=6)
    
    add_paragraph_with_spacing(doc, "TABLE 8.1 KEY CODING MODULES", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_code = doc.add_table(rows=1, cols=3)
    t_code.style = 'Table Grid'
    hdr_cells = t_code.rows[0].cells
    hdr_cells[0].text = 'FILE PATH'
    hdr_cells[1].text = 'PURPOSE'
    hdr_cells[2].text = 'KEY METHODS'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    for path, purpose, fn in CODE_FILES:
        row = t_code.add_row()
        row.cells[0].text = path
        row.cells[1].text = purpose
        row.cells[2].text = fn
        for cell in row.cells:
            set_cell_margins(cell)
            
    add_paragraph_with_spacing(doc, "8.3 DATA DICTIONARY", style="Heading 2", space_before=12, space_after=6)
    
    # Large single table data dictionary format
    add_paragraph_with_spacing(doc, "TABLE 8.3 DATA DICTIONARY", style="Normal", space_after=6, align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.bold = True
    t_dict = doc.add_table(rows=1, cols=6)
    t_dict.style = 'Table Grid'
    hdr_cells = t_dict.rows[0].cells
    for idx, header in enumerate(["TABLE NAME", "FIELD NAME", "DATA TYPE", "KEY", "NULL", "DESCRIPTION"]):
        hdr_cells[idx].text = header
        hdr_cells[idx].paragraphs[0].runs[0].font.bold = True
        set_cell_margins(hdr_cells[idx])
        
    for tbl_name, t_meta in DB_TABLES_DATA.items():
        for col_data in t_meta["cols"]:
            row = t_dict.add_row()
            row.cells[0].text = tbl_name
            row.cells[1].text = col_data[0] # Field
            row.cells[2].text = col_data[1] # Type
            row.cells[3].text = col_data[2] # Key
            row.cells[4].text = col_data[3] # Null
            row.cells[5].text = col_data[4] # Desc
            for cell in row.cells:
                set_cell_margins(cell)
                
    doc.add_page_break()

    # ------------------ CHAPTER 9 ------------------
    add_paragraph_with_spacing(doc, "9. BIBLIOGRAPHY AND REFERENCES", style="Heading 1", space_before=12, space_after=12).runs[0].font.color.rgb = RGBColor(15, 118, 110)
    add_paragraph_with_spacing(doc, BIB_TEXT, space_after=12)
    
    # Save document
    OUTPUT_DOCX_DIR.mkdir(parents=True, exist_ok=True)
    target_docx = OUTPUT_DOCX_DIR / "FinWise_AI_Project_Report.docx"
    try:
        doc.save(str(target_docx))
        print(f"MS Word Report saved to: {target_docx}")
    except PermissionError:
        target_docx = OUTPUT_DOCX_DIR / "FinWise_AI_Project_Report_v2.docx"
        doc.save(str(target_docx))
        print(f"MS Word Report saved to fallback (as primary was locked): {target_docx}")

# Generate PDF document
def build_pdf_report():
    print("Building PDF Project Report...")
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    target_pdf = OUTPUT_PDF_DIR / "FinWise_AI_Project_Report.pdf"
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    pdf_styles = {
        "title": ParagraphStyle("TitleStyle", fontName="Helvetica-Bold", fontSize=26, leading=32, alignment=TA_CENTER, textColor=colors.HexColor("#0f766e"), spaceAfter=14),
        "subtitle": ParagraphStyle("SubTitleStyle", fontName="Helvetica-Bold", fontSize=13, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#374151"), spaceAfter=24),
        "h1": ParagraphStyle("Heading1Style", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#0f766e"), spaceBefore=18, spaceAfter=10, keepWithNext=True),
        "h2": ParagraphStyle("Heading2Style", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=colors.HexColor("#1f2937"), spaceBefore=12, spaceAfter=6, keepWithNext=True),
        "h3": ParagraphStyle("Heading3Style", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#374151"), spaceBefore=8, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("BodyStyle", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_LEFT, textColor=colors.HexColor("#111827"), spaceAfter=8),
        "body_justify": ParagraphStyle("BodyJustifyStyle", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY, textColor=colors.HexColor("#111827"), spaceAfter=8),
        "bullet": ParagraphStyle("BulletStyle", fontName="Helvetica", fontSize=10, leading=14, leftIndent=12, firstLineIndent=-8, textColor=colors.HexColor("#111827"), spaceAfter=4),
        "code": ParagraphStyle("CodeStyle", fontName="Courier", fontSize=8, leading=10, backColor=colors.HexColor("#f3f4f6"), borderColor=colors.HexColor("#d1d5db"), borderWidth=0.5, borderPadding=6, spaceBefore=6, spaceAfter=10),
        "table_cell": ParagraphStyle("TableCellStyle", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#111827")),
        "table_cell_bold": ParagraphStyle("TableCellBoldStyle", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#111827")),
        "formula": ParagraphStyle("FormulaStyle", fontName="Courier-Bold", fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a"), spaceBefore=2, spaceAfter=2)
    }
    
    doc = SimpleDocTemplate(
        str(target_pdf),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=25 * mm, # Standard binding margin
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="FinWise AI Project Report",
        author="FinWise AI",
    )
    
    def add_structured_text_to_pdf(story, text_content):
        paragraphs = text_content.strip().split("\n\n")
        for block in paragraphs:
            block = block.strip()
            if not block:
                continue
            if any(sym in block for sym in ["P(cj | W)", "log P(cj", "P(wi | cj)", "Normalized_Prob", "Confidence("]):
                lines = [l.strip() for l in block.split("\n") if l.strip()]
                for line in lines:
                    story.append(Paragraph(f"<b><i>{line}</i></b>", pdf_styles["formula"]))
                story.append(Spacer(1, 4))
            elif block.startswith(("1. ", "2. ", "3. ", "4. ", "5. ")):
                if ":\n" in block:
                    header, body = block.split(":\n", 1)
                    story.append(Paragraph(f"<b>{header}:</b>", pdf_styles["h3"]))
                    story.append(Paragraph(body.strip(), pdf_styles["body"]))
                elif ":" in block.split("\n")[0]:
                    first_line, rest = block.split("\n", 1) if "\n" in block else (block, "")
                    story.append(Paragraph(f"<b>{first_line}</b>", pdf_styles["h3"]))
                    if rest.strip():
                        story.append(Paragraph(rest.strip(), pdf_styles["body"]))
                else:
                    story.append(Paragraph(block, pdf_styles["body"]))
            else:
                story.append(Paragraph(block, pdf_styles["body"]))

    story = []
    
    # ------------------ COVER PAGE ------------------
    story.append(Spacer(1, 40))
    story.append(Paragraph("PROJECT REPORT ON", ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=10)))
    story.append(Paragraph("FINWISE AI", pdf_styles["title"]))
    story.append(Paragraph("SMART PERSONAL FINANCE MANAGEMENT SYSTEM", pdf_styles["subtitle"]))
    story.append(Spacer(1, 30))
    
    story.append(Paragraph("Submitted in partial fulfillment of the requirements for the award of the degree of", ParagraphStyle("CoverMid", fontName="Helvetica", fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=10)))
    story.append(Paragraph("<b>MASTER OF COMPUTER APPLICATIONS / BACHELOR OF COMPUTER APPLICATIONS</b>", ParagraphStyle("CoverDeg", fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=30)))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(f"Under the guidance of<br/><b>{GUIDE_NAME}</b>", ParagraphStyle("CoverGuide", fontName="Helvetica", fontSize=11, leading=15, alignment=TA_CENTER, spaceAfter=40)))
    story.append(Paragraph(f"Submitted by:<br/><b>{STUDENT_NAME}</b><br/>Register Number: <b>{REGISTER_NUMBER}</b>", ParagraphStyle("CoverStud", fontName="Helvetica", fontSize=11, leading=15, alignment=TA_CENTER, spaceAfter=50)))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(f"<b>DEPARTMENT OF COMPUTER APPLICATIONS</b><br/><b>{INSTITUTION_NAME}</b><br/>Academic Year: {ACADEMIC_YEAR}", ParagraphStyle("CoverDept", fontName="Helvetica", fontSize=11, leading=15, alignment=TA_CENTER)))
    
    story.append(PageBreak())
    
    # ------------------ CERTIFICATE PAGE ------------------
    story.append(Paragraph("CERTIFICATE", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    cert_text = (
        f"This is to certify that the project report entitled 'FinWise AI - Smart Personal Finance Management System' "
        f"is a bonafide record of work done by {STUDENT_NAME} (Reg No: {REGISTER_NUMBER}) in partial fulfillment of the "
        f"requirements for the award of the degree of MCA/BCA in Department of Computer Applications, "
        f"{INSTITUTION_NAME} during the academic year {ACADEMIC_YEAR}."
    )
    story.append(Paragraph(cert_text, pdf_styles["body_justify"]))
    story.append(Spacer(1, 60))
    
    sig_data = [
        [Paragraph("<b>Project Guide</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>Head of the Department</b>", pdf_styles["table_cell_bold"])],
        [Paragraph("<br/><br/>Date: ____________", pdf_styles["table_cell"]), Paragraph("<br/><br/>External Examiner", pdf_styles["table_cell"])]
    ]
    t_sig = Table(sig_data, colWidths=[80*mm, 80*mm])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_sig)
    story.append(PageBreak())
    
    # ------------------ DECLARATION PAGE ------------------
    story.append(Paragraph("DECLARATION", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    decl_text = (
        f"I, {STUDENT_NAME}, hereby declare that the project work entitled 'FinWise AI - Smart Personal Finance Management System' "
        f"submitted to the Department of Computer Applications, {INSTITUTION_NAME}, is a record of independent project work carried out "
        f"by me under the supervision of {GUIDE_NAME}, Project Guide, and that it has not previously formed the basis for the award of "
        f"any other degree or similar titles."
    )
    story.append(Paragraph(decl_text, pdf_styles["body_justify"]))
    story.append(Spacer(1, 60))
    
    decl_sig_data = [
        [Paragraph("Place: ____________<br/>Date: ____________", pdf_styles["table_cell"]), Paragraph(f"<b>{STUDENT_NAME}</b>", pdf_styles["table_cell_bold"])]
    ]
    t_decl = Table(decl_sig_data, colWidths=[80*mm, 80*mm])
    t_decl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT')
    ]))
    story.append(t_decl)
    story.append(PageBreak())
    
    # ------------------ ACKNOWLEDGEMENT PAGE ------------------
    story.append(Paragraph("ACKNOWLEDGEMENT", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    ack_text = (
        "I express my deepest gratitude to all who provided guidance and support during the design and development "
        "of FinWise AI. I thank our Institution Principal and Head of the Department for providing the resources and "
        "facilities needed to execute this project successfully.<br/><br/>"
        f"I am deeply indebted to my project guide, {GUIDE_NAME}, for their valuable guidance, structural recommendations, "
        "and critical reviews during the software engineering and testing lifecycles.<br/><br/>"
        "Finally, I thank my family members and peers for their continuous support and helpful feedback during "
        "the user acceptance testing iterations."
    )
    story.append(Paragraph(ack_text, pdf_styles["body_justify"]))
    story.append(PageBreak())
    
    # ------------------ ABSTRACT PAGE ------------------
    story.append(Paragraph("ABSTRACT", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    abs_text = (
        "FinWise AI is a comprehensive, offline-first personal finance management system designed to assist users in tracking their "
        "educational and professional financial transactions, managing budgets, and planning savings goals. Traditional finance apps "
        "depend on cloud databases and external servers, raising concerns about data privacy and internet reliability. FinWise AI resolves "
        "these issues by utilizing a local-first deployment model where user records, statements, and intelligent advice are processed "
        "entirely on the client’s machine.<br/><br/>"
        "Central to the system is a local intelligent categorizer based on a Multinomial Naive Bayes category prediction model that matches "
        "transaction descriptions to categories without sending transaction logs to third-party services. Additionally, an offline rule-based "
        "chat assistant answers finance-related queries, retrieves real-time database summaries, and offers actionable financial insights.<br/><br/>"
        "Using modern web technologies—a React frontend, a Flask (Python) backend, and a MySQL database—FinWise AI separates responsibilities "
        "through a classic three-tier architecture. The system supports multi-account ledgers (Bank, Cash, UPI, Loans, Credit Cards, "
        "Investments), bank statement imports (CSV, Excel, text-based PDF) with automatic duplicate detection, and visual month-wise analytics. "
        "By consolidating accounting principles with local artificial intelligence, FinWise AI significantly reduces manual tracking workloads, "
        "secures private financial data, and enables users to establish sound budgets and savings habits."
    )
    story.append(Paragraph(abs_text, pdf_styles["body_justify"]))
    story.append(PageBreak())
    
    # ------------------ TABLE OF CONTENTS ------------------
    story.append(Paragraph("TABLE OF CONTENTS", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    
    t_toc_data = [
        [Paragraph("<b>S.NO</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>TITLE</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>PAGE NO.</b>", pdf_styles["table_cell_bold"])],
        [
            Paragraph("", pdf_styles["table_cell"]),
            Paragraph("ABSTRACT<br/>ACKNOWLEDGEMENT<br/>LIST OF TABLES<br/>LIST OF FIGURES", pdf_styles["table_cell"]),
            Paragraph("(i)<br/>(ii)<br/>(iii)<br/>(iv)", pdf_styles["table_cell"])
        ],
        [Paragraph("<b>CHAPTERS</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>TITLE</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>PAGE NO.</b>", pdf_styles["table_cell_bold"])]
    ]
    ch_rows = [
        ("1", "INTRODUCTION<br/>1.1 PROJECT INTRODUCTION", "01"),
        ("2", "WORKING ENVIRONMENT<br/>2.1 HARDWARE REQUIREMENT<br/>2.2 SOFTWARE REQUIREMENT<br/>2.3 SYSTEM SOFTWARE", "02"),
        ("3", "SYSTEM ANALYSIS<br/>3.1 FEASIBILITY STUDY<br/>3.2 EXISTING SYSTEM<br/>3.3 DRAWBACKS OF EXISTING SYSTEM<br/>3.4 PROPOSED SYSTEM<br/>3.5 BENEFITS OF PROPOSED SYSTEM<br/>3.6 SCOPE OF THE PROJECT", "05"),
        ("4", "SYSTEM DESIGN<br/>4.1 SYSTEM ARCHITECTURE<br/>4.2 SYSTEM DIAGRAMS<br/>4.3 DATABASE DESIGN", "08"),
        ("5", "PROJECT DESCRIPTION<br/>5.1 OBJECTIVE<br/>5.2 MODULE DESCRIPTION<br/>5.3 IMPLEMENTATION<br/>5.4 MAINTENANCE STRATEGY", "14"),
        ("6", "SYSTEM TESTING<br/>6.1 TESTING DEFINITION<br/>6.2 TESTING OBJECTIVE<br/>6.3 TYPES OF TESTING<br/>6.4 TEST CASES", "20"),
        ("7", "CONCLUSION<br/>7.1 SUMMARY<br/>7.2 FUTURE ENHANCEMENT", "23"),
        ("8", "APPENDIX<br/>8.1 SCREENSHOTS<br/>8.2 CODING<br/>8.3 DATA DICTIONARY", "25"),
        ("9", "BIBLIOGRAPHY AND REFERENCES", "35")
    ]
    for s_no, text, pg in ch_rows:
        t_toc_data.append([
            Paragraph(s_no, pdf_styles["table_cell"]),
            Paragraph(text, pdf_styles["table_cell"]),
            Paragraph(pg, pdf_styles["table_cell"])
        ])
        
    t_toc = Table(t_toc_data, colWidths=[25*mm, 105*mm, 30*mm])
    t_toc.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_toc)
    story.append(PageBreak())
    
    # ------------------ LIST OF TABLES PAGE ------------------
    story.append(Paragraph("LIST OF TABLES", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    
    t_lot_data = [[Paragraph("<b>TABLE NO</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>TITLE</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>PAGE NO</b>", pdf_styles["table_cell_bold"])]]
    for tbl_no, title, pg in LIST_OF_TABLES_DATA:
        t_lot_data.append([Paragraph(tbl_no, pdf_styles["table_cell"]), Paragraph(title, pdf_styles["table_cell"]), Paragraph(pg, pdf_styles["table_cell"])])
        
    t_lot_pdf = Table(t_lot_data, colWidths=[30*mm, 100*mm, 30*mm])
    t_lot_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_lot_pdf)
    story.append(PageBreak())
    
    # ------------------ LIST OF FIGURES PAGE ------------------
    story.append(Paragraph("LIST OF FIGURES", pdf_styles["h1"]))
    story.append(Spacer(1, 10))
    
    t_lof_data = [[Paragraph("<b>FIGURE NO</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>TITLE</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>PAGE NO</b>", pdf_styles["table_cell_bold"])]]
    for fig_no, title, pg in LIST_OF_FIGURES_DATA:
        t_lof_data.append([Paragraph(fig_no, pdf_styles["table_cell"]), Paragraph(title, pdf_styles["table_cell"]), Paragraph(pg, pdf_styles["table_cell"])])
        
    t_lof_pdf = Table(t_lof_data, colWidths=[30*mm, 100*mm, 30*mm])
    t_lof_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_lof_pdf)
    story.append(PageBreak())

    # ------------------ CHAPTER 1 ------------------
    story.append(Paragraph("1. INTRODUCTION", pdf_styles["h1"]))
    story.append(Paragraph("1.1 PROJECT INTRODUCTION", pdf_styles["h2"]))
    story.append(Paragraph(INTRO_P1, pdf_styles["body_justify"]))
    story.append(Paragraph(PROBLEM_P1, pdf_styles["body_justify"]))
    story.append(Paragraph(MOTIVATION_P1, pdf_styles["body_justify"]))
    story.append(Paragraph(OVERVIEW_P1, pdf_styles["body_justify"]))
    story.append(PageBreak())

    # ------------------ CHAPTER 2 ------------------
    story.append(Paragraph("2. WORKING ENVIRONMENT", pdf_styles["h1"]))
    story.append(Paragraph("2.1 HARDWARE REQUIREMENT", pdf_styles["h2"]))
    
    story.append(Paragraph("TABLE 2.1 HARDWARE REQUIREMENTS", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_hw_data = [[Paragraph("<b>COMPONENT</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>REQUIREMENT</b>", pdf_styles["table_cell_bold"])]]
    for comp, req in HW_TABLE_DATA:
        t_hw_data.append([Paragraph(comp, pdf_styles["table_cell"]), Paragraph(req, pdf_styles["table_cell"])])
    t_hw_pdf = Table(t_hw_data, colWidths=[50*mm, 110*mm])
    t_hw_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_hw_pdf)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2.2 SOFTWARE REQUIREMENT", pdf_styles["h2"]))
    story.append(Paragraph("TABLE 2.2 SOFTWARE REQUIREMENTS", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_sw_data = [[Paragraph("<b>SOFTWARE</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>VERSION / REQUIREMENT</b>", pdf_styles["table_cell_bold"])]]
    for sw, req in SW_TABLE_DATA:
        t_sw_data.append([Paragraph(sw, pdf_styles["table_cell"]), Paragraph(req, pdf_styles["table_cell"])])
    t_sw_pdf = Table(t_sw_data, colWidths=[60*mm, 100*mm])
    t_sw_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sw_pdf)
    
    story.append(Paragraph("2.3 SYSTEM SOFTWARE", pdf_styles["h2"]))
    story.append(Paragraph(SYSTEM_SW_EXPS.replace("\n\n", "<br/><br/>"), pdf_styles["body_justify"]))
    story.append(PageBreak())

    # ------------------ CHAPTER 3 ------------------
    story.append(Paragraph("3. SYSTEM ANALYSIS", pdf_styles["h1"]))
    story.append(Paragraph("3.1 FEASIBILITY STUDY", pdf_styles["h2"]))
    story.append(Paragraph("<b>Technical Feasibility:</b> The system runs on React, Flask, and MySQL, which are widely-supported and lightweight tools. Since all AI/ML models run locally on the CPU, no expensive cloud services are required.", pdf_styles["body_justify"]))
    story.append(Paragraph("<b>Operational Feasibility:</b> The interface features a sidebar structure with forms and tables. Users can quickly enter details, preview imports, and chat in natural language, making the system easy to use.", pdf_styles["body_justify"]))
    story.append(Paragraph("<b>Economic Feasibility:</b> Built using free, open-source libraries, FinWise AI requires no ongoing server hosting costs, API charges, or cloud fees, making it highly cost-effective.", pdf_styles["body_justify"]))
    
    story.append(Paragraph("3.2 EXISTING SYSTEM", pdf_styles["h2"]))
    story.append(Paragraph(EXISTING_SYS_TEXT, pdf_styles["body_justify"]))
    
    story.append(Paragraph("3.3 DRAWBACKS OF EXISTING SYSTEM", pdf_styles["h2"]))
    for idx, dw in enumerate(DRAWBACKS, 1):
        story.append(Paragraph(f"{idx}) {dw.split(': ', 1)[1] if ': ' in dw else dw}", pdf_styles["body"]))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("3.4 PROPOSED SYSTEM", pdf_styles["h2"]))
    story.append(Paragraph(PROP_SYS_TEXT, pdf_styles["body_justify"]))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("TABLE 3.1 EXISTING SYSTEM VS PROPOSED SYSTEM", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_comp_data = [[Paragraph("<b>ASPECT</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>EXISTING SYSTEM</b>", pdf_styles["table_cell_bold"]), Paragraph("<b>PROPOSED SYSTEM</b>", pdf_styles["table_cell_bold"])]]
    for aspect, ex, prop in COMPARISONS:
        t_comp_data.append([Paragraph(aspect, pdf_styles["table_cell"]), Paragraph(ex, pdf_styles["table_cell"]), Paragraph(prop, pdf_styles["table_cell"])])
    t_comp_pdf = Table(t_comp_data, colWidths=[40*mm, 60*mm, 60*mm])
    t_comp_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_comp_pdf)
    
    story.append(Paragraph("3.5 BENEFITS OF PROPOSED SYSTEM", pdf_styles["h2"]))
    for ben in BENEFITS:
        story.append(Paragraph(ben, pdf_styles["body"]))
        
    story.append(Paragraph("3.6 SCOPE OF THE PROJECT", pdf_styles["h2"]))
    story.append(Paragraph("The current scope covers single-user offline finance tracking including multiple asset ledgers, CSV statement parsing, automatic duplicate check parameters, and monthly budget alerts. Future scopes include adding OCR, time-series forecasting, and direct local bank connectivity.", pdf_styles["body_justify"]))
    story.append(PageBreak())

    # ------------------ CHAPTER 4 ------------------
    story.append(Paragraph("4. SYSTEM DESIGN", pdf_styles["h1"]))
    story.append(Paragraph("4.1 SYSTEM ARCHITECTURE", pdf_styles["h2"]))
    story.append(Paragraph(ARCH_EXP, pdf_styles["body_justify"]))
    story.append(Paragraph("FIGURE 4.1 SYSTEM ARCHITECTURE DIAGRAM", ParagraphStyle("FigTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)))
    story.append(Preformatted(ARCH_DIAG, pdf_styles["code"]))
    
    story.append(Paragraph("4.2 SYSTEM DIAGRAMS", pdf_styles["h2"]))
    story.append(Paragraph("FIGURE 4.2 USE CASE DIAGRAM", ParagraphStyle("FigTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceBefore=6, spaceAfter=4)))
    story.append(Preformatted(USECASE_DIAG, pdf_styles["code"]))
    
    story.append(Paragraph("FIGURE 4.3 CLASS DIAGRAM", ParagraphStyle("FigTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)))
    story.append(Preformatted(CLASS_DIAG, pdf_styles["code"]))
    
    story.append(Paragraph("FIGURE 4.4 SEQUENCE DIAGRAM", ParagraphStyle("FigTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)))
    story.append(Preformatted(SEQ_DIAG, pdf_styles["code"]))
    
    story.append(Paragraph("4.3 DATABASE DESIGN", pdf_styles["h2"]))
    for tbl_name, t_meta in DB_TABLES_DATA.items():
        story.append(Paragraph(f"TABLE: {tbl_name}", pdf_styles["h3"]))
        story.append(Paragraph(t_meta["desc"], pdf_styles["body"]))
        
        t_db_data = [[Paragraph(f"<b>{x}</b>", pdf_styles["table_cell_bold"]) for x in ["FIELD", "TYPE", "KEY", "NULL", "DESCRIPTION"]]]
        for row_data in t_meta["cols"]:
            t_db_data.append([Paragraph(x, pdf_styles["table_cell"]) for x in row_data])
            
        t_db_pdf = Table(t_db_data, colWidths=[30*mm, 25*mm, 35*mm, 20*mm, 50*mm])
        t_db_pdf.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_db_pdf)
        story.append(Spacer(1, 10))
        
    story.append(PageBreak())

    # ------------------ CHAPTER 5 ------------------
    story.append(Paragraph("5. PROJECT DESCRIPTION", pdf_styles["h1"]))
    story.append(Paragraph("5.1 OBJECTIVE", pdf_styles["h2"]))
    story.append(Paragraph("The objective of FinWise AI is to deliver private, offline-first personal financial control. It establishes an accounting double-ledger that tracks transaction records across multiple accounts without connecting to cloud systems.", pdf_styles["body_justify"]))
    
    story.append(Paragraph("5.2 MODULE DESCRIPTION", pdf_styles["h2"]))
    for idx, mod in enumerate(MODULES, 1):
        story.append(Paragraph(f"<b>{idx}. {mod['name']}</b>", pdf_styles["h3"]))
        story.append(Paragraph(f"<b>Purpose:</b> {mod['purpose']}", pdf_styles["body"]))
        story.append(Paragraph(f"<b>Working:</b> {mod['working']}", pdf_styles["body"]))
        story.append(Paragraph(f"<b>Input:</b> {mod['input']}", pdf_styles["body"]))
        story.append(Paragraph(f"<b>Processing:</b> {mod['processing']}", pdf_styles["body"]))
        story.append(Paragraph(f"<b>Output:</b> {mod['output']}", pdf_styles["body"]))
        story.append(Spacer(1, 4))
        
    story.append(Paragraph("5.3 IMPLEMENTATION", pdf_styles["h2"]))
    
    story.append(Paragraph("<b>Frontend Development (React, Vite, Bootstrap):</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_FRONTEND, pdf_styles["body"]))
    
    story.append(Paragraph("<b>Backend Development (Flask API, Python):</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_BACKEND, pdf_styles["body"]))
    
    story.append(Paragraph("<b>Database Implementation (MySQL):</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_DATABASE, pdf_styles["body"]))
    
    story.append(Paragraph("<b>AI/ML implementation (Multinomial Naive Bayes):</b>", pdf_styles["h3"]))
    add_structured_text_to_pdf(story, IMP_AI_CLASSIFY)
    
    story.append(Paragraph("<b>Conversational Chat Engine:</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_CHAT_ASSIST, pdf_styles["body"]))
    
    story.append(Paragraph("<b>Bank Statement Processing:</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_STATEMENT, pdf_styles["body"]))
    
    story.append(Paragraph("<b>Double-Entry Ledger Engine:</b>", pdf_styles["h3"]))
    story.append(Paragraph(IMP_LEDGER, pdf_styles["body"]))
    
    story.append(Paragraph("<b>API Documentation:</b>", pdf_styles["h3"]))
    story.append(Paragraph("TABLE 5.2 API DOCUMENTATION", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_api_data = [[Paragraph(f"<b>{x}</b>", pdf_styles["table_cell_bold"]) for x in ["Method", "Endpoint", "Purpose", "Auth", "Payload", "Response"]]]
    for method, path, purpose, auth, req, resp in API_ENDPOINTS:
        t_api_data.append([Paragraph(method, pdf_styles["table_cell"]), Paragraph(path, pdf_styles["table_cell"]), Paragraph(purpose, pdf_styles["table_cell"]), Paragraph(auth, pdf_styles["table_cell"]), Paragraph(req, pdf_styles["table_cell"]), Paragraph(resp, pdf_styles["table_cell"])])
        
    t_api_pdf = Table(t_api_data, colWidths=[15*mm, 38*mm, 37*mm, 12*mm, 30*mm, 28*mm])
    t_api_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_api_pdf)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("5.4 MAINTENANCE STRATEGY", pdf_styles["h2"]))
    story.append(Paragraph(MAINTENANCE_EXP.replace("\n\n", "<br/><br/>"), pdf_styles["body_justify"]))
    story.append(PageBreak())

    # ------------------ CHAPTER 6 ------------------
    story.append(Paragraph("6. SYSTEM TESTING", pdf_styles["h1"]))
    story.append(Paragraph("6.1 TESTING DEFINITION", pdf_styles["h2"]))
    story.append(Paragraph("System testing checks the integrated frontend and backend with database transactions.", pdf_styles["body_justify"]))
    
    story.append(Paragraph("6.2 TESTING OBJECTIVE", pdf_styles["h2"]))
    for idx, obj in enumerate(TESTING_OBJS, 1):
        story.append(Paragraph(f"{idx}. {obj}", pdf_styles["bullet"]))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("6.3 TYPES OF TESTING", pdf_styles["h2"]))
    story.append(Paragraph("Unit, Integration, and end-to-end System testing are performed offline.", pdf_styles["body_justify"]))
    
    story.append(Paragraph("6.4 TEST CASES", pdf_styles["h2"]))
    story.append(Paragraph("TABLE 6.4 TEST CASES", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_tc_data = [[Paragraph(f"<b>{x}</b>", pdf_styles["table_cell_bold"]) for x in ["TEST CASE ID", "TEST CASE", "INPUT", "EXPECTED OUTPUT", "ACTUAL OUTPUT", "STATUS"]]]
    for id_val, scenario, inp, exp, act, status in TEST_CASES:
        t_tc_data.append([Paragraph(id_val, pdf_styles["table_cell"]), Paragraph(scenario, pdf_styles["table_cell"]), Paragraph(inp, pdf_styles["table_cell"]), Paragraph(exp, pdf_styles["table_cell"]), Paragraph(act, pdf_styles["table_cell"]), Paragraph(status, pdf_styles["table_cell"])])
        
    t_tc_pdf = Table(t_tc_data, colWidths=[18*mm, 28*mm, 28*mm, 36*mm, 36*mm, 14*mm])
    t_tc_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tc_pdf)
    story.append(PageBreak())

    # ------------------ CHAPTER 7 ------------------
    story.append(Paragraph("7. CONCLUSION", pdf_styles["h1"]))
    story.append(Paragraph("7.1 SUMMARY", pdf_styles["h2"]))
    story.append(Paragraph(SUMMARY_TEXT, pdf_styles["body_justify"]))
    
    story.append(Paragraph("7.2 FUTURE ENHANCEMENT", pdf_styles["h2"]))
    for idx, item in enumerate(FUTURE_ENH, 1):
        story.append(Paragraph(f"{idx}. {item}", pdf_styles["bullet"]))
    story.append(PageBreak())

    # ------------------ CHAPTER 8 ------------------
    story.append(Paragraph("8. APPENDIX", pdf_styles["h1"]))
    story.append(Paragraph("8.1 SCREENSHOTS", pdf_styles["h2"]))
    for idx, (name, scr_desc) in enumerate(SCREENS, 1):
        story.append(Paragraph(f"FIGURE 8.1.{idx} {name}", ParagraphStyle("FigTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)))
        story.append(Paragraph(scr_desc, pdf_styles["body"]))
        story.append(Spacer(1, 4))
        
    story.append(Paragraph("8.2 KEY CODING MODULES", pdf_styles["h2"]))
    story.append(Paragraph("TABLE 8.1 KEY CODING MODULES", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    t_code_data = [[Paragraph(f"<b>{x}</b>", pdf_styles["table_cell_bold"]) for x in ["FILE PATH", "PURPOSE", "KEY METHODS"]]]
    for path, purpose, fn in CODE_FILES:
        t_code_data.append([Paragraph(path, pdf_styles["table_cell"]), Paragraph(purpose, pdf_styles["table_cell"]), Paragraph(fn, pdf_styles["table_cell"])])
    t_code_pdf = Table(t_code_data, colWidths=[40*mm, 60*mm, 60*mm])
    t_code_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_code_pdf)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("8.3 DATA DICTIONARY", pdf_styles["h2"]))
    story.append(Paragraph("TABLE 8.3 DATA DICTIONARY", ParagraphStyle("TableTitle", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, spaceAfter=4)))
    
    t_dict_data = [[Paragraph(f"<b>{x}</b>", pdf_styles["table_cell_bold"]) for x in ["TABLE NAME", "FIELD NAME", "DATA TYPE", "KEY", "NULL", "DESCRIPTION"]]]
    for tbl_name, t_meta in DB_TABLES_DATA.items():
        for col_data in t_meta["cols"]:
            t_dict_data.append([
                Paragraph(tbl_name, pdf_styles["table_cell"]),
                Paragraph(col_data[0], pdf_styles["table_cell"]),
                Paragraph(col_data[1], pdf_styles["table_cell"]),
                Paragraph(col_data[2], pdf_styles["table_cell"]),
                Paragraph(col_data[3], pdf_styles["table_cell"]),
                Paragraph(col_data[4], pdf_styles["table_cell"])
            ])
            
    t_dict_pdf = Table(t_dict_data, colWidths=[25*mm, 25*mm, 25*mm, 20*mm, 15*mm, 50*mm])
    t_dict_pdf.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_dict_pdf)
    story.append(PageBreak())

    # ------------------ CHAPTER 9 ------------------
    story.append(Paragraph("9. BIBLIOGRAPHY AND REFERENCES", pdf_styles["h1"]))
    story.append(Paragraph(BIB_TEXT.replace("\n", "<br/>"), pdf_styles["body"]))

    # Build callback for footers
    def footer_callback(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#d1d5db"))
        canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(18 * mm, 9 * mm, "FinWise AI Project Report")
        canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    try:
        doc.build(story, onFirstPage=footer_callback, onLaterPages=footer_callback)
        print(f"PDF Report saved to: {target_pdf}")
    except PermissionError:
        target_pdf = OUTPUT_PDF_DIR / "FinWise_AI_Project_Report_v2.pdf"
        doc.build(story, onFirstPage=footer_callback, onLaterPages=footer_callback)
        print(f"PDF Report saved to fallback (as primary was locked): {target_pdf}")

if __name__ == "__main__":
    try:
        # Create docx file
        build_docx_report()
        # Create pdf file
        build_pdf_report()
        
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        raise
