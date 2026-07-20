import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = path => readFileSync(resolve(root, path), "utf8");

describe("frontend smoke coverage", () => {
  it("keeps authentication wired to httpOnly cookie APIs", () => {
    const app = read("src/main.jsx");
    const api = read("src/services/api.js");
    const login = read("src/pages/Login.jsx");
    const register = read("src/pages/Register.jsx");

    assert.match(app, /api\.get\("\/profile"\)/);
    assert.match(app, /<Login .*setToken=\{\(\)=>setAuthenticated\(true\)\}/);
    assert.match(app, /<Register setPage=\{setPage\}/);
    assert.match(api, /withCredentials:\s*true/);
    assert.match(api, /axios\.post\("\/api\/refresh"/);
    assert.match(login, /api\.post\("\/login",form\)/);
    assert.match(register, /api\.post\("\/register",form\)/);
    assert.doesNotMatch(api, /localStorage\.setItem/);
  });

  it("exposes every main dashboard page through sidebar navigation", () => {
    const dashboard = read("src/pages/Dashboard.jsx");
    const expectedPages = [
      ["home", "Dashboard"],
      ["accounts", "Accounts"],
      ["transactions", "Transactions"],
      ["ledger", "Ledger"],
      ["budget", "Budget"],
      ["goals", "Goals"],
      ["analytics", "Analytics"],
      ["reports", "Reports"],
      ["ai", "Finance Chat"],
      ["hub", "Smart Tools"],
      ["profile", "Profile"]
    ];

    for (const [key, label] of expectedPages) {
      assert.match(dashboard, new RegExp(`${key}.*${label}`));
    }

    assert.match(dashboard, /setTransactionType\(options\.type\)/);
    assert.match(dashboard, /api\.post\("\/logout"\)/);
  });

  it("keeps transaction workflows available for manual entry and statement import", () => {
    const transactions = read("src/pages/Transactions.jsx");

    for (const endpoint of [
      "/accounts",
      "/transactions",
      "/ai/categorize",
      "/statements/preview",
      "/statements/confirm",
      "/statements/history",
      "/transactions/duplicates",
      "/transactions/bulk"
    ]) {
      assert.match(transactions, new RegExp(endpoint.replaceAll("/", "\\/")));
    }

    for (const label of [
      "Income",
      "Expense",
      "Transfer",
      "Preview Statement",
      "Confirm Import",
      "Make recurring",
      "Scan duplicates",
      "Split Transaction"
    ]) {
      assert.match(transactions, new RegExp(label));
    }
  });

  it("guards the password reset and registration form requirements", () => {
    const login = read("src/pages/Login.jsx");
    const register = read("src/pages/Register.jsx");

    assert.match(login, /api\.post\("\/password\/forgot"/);
    assert.match(login, /api\.post\("\/password\/reset"/);
    assert.match(login, /Password must contain at least 8 characters/);
    assert.match(login, /Passwords do not match/);
    assert.match(register, /minLength="8"/);
    assert.match(register, /Registration successful/);
  });
});
