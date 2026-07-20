import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function Home({ onNavigate }) {
  const [data, setData] = useState(null);

  const load = async () => {
    const res = await api.get("/dashboard");
    setData(res.data);
  };

  useEffect(() => {
    load();
  }, []);

  if (!data) return <div className="panel"><h5>Loading dashboard...</h5></div>;

  const cashBalance = Number(data.balance || 0);
  const goalSavings = Number(data.goalSavings || 0);
  const totalTrackedMoney = Number(data.totalTrackedMoney || cashBalance + goalSavings);
  const income = Number(data.income || 0);
  const expense = Number(data.expense || 0);
  const savings = income - expense;
  const savingsRate = income > 0 ? Math.round((savings / income) * 100) : 0;

  const cards = [
    ["Total Money", totalTrackedMoney, "bi-safe", "Balance plus goal savings", "blue-card"],
    ["Balance Money", cashBalance, "bi-wallet2", "Available in accounts", "teal-card"],
    ["Income", income, "bi-cash-stack", "Money received", "green-card"],
    ["Expense", expense, "bi-cart-dash", "Money spent", "red-card"],
    ["Savings", goalSavings, "bi-piggy-bank", "Saved in goals", "purple-card"]
  ];
  const accountNameFor = t => t.type === "Transfer" && t.transfer_to_account_name ? `${t.account_name} -> ${t.transfer_to_account_name}` : t.account_name;
  const amountClassFor = t => t.type === "Income" ? "text-success fw-bold" : t.type === "Expense" ? "text-danger fw-bold" : "text-info fw-bold";
  const amountPrefixFor = t => t.type === "Income" ? "+" : t.type === "Expense" ? "-" : "";

  return (
    <>
      <div className="dashboard-header">
        <div>
          <h2 className="page-title mb-1">Professional Dashboard</h2>
          <p className="text-muted mb-0">Track balance, income, expenses, savings and financial health.</p>
        </div>
        <div className="quick-date">
          <i className="bi bi-calendar3"></i>{new Date().toLocaleDateString()}
        </div>
      </div>

      {data.budgetAlerts?.length > 0 && <div className="budget-alert mb-3"><i className="bi bi-exclamation-triangle"/><div><strong>Budget warning</strong><p>{data.budgetAlerts.map(x => x.category + " " + Math.round(Number(x.spent) / Number(x.budget_amount) * 100) + "%").join(" · ")}</p></div></div>}

      <div className="row g-3 mt-1">
        {cards.map((c, i) => (
          <div className="col-xl col-lg-4 col-md-6" key={i}>
            <div className={`modern-card ${c[4]}`}>
              <div className="d-flex justify-content-between align-items-start">
                <div>
                  <p className="card-label">{c[0]}</p>
                  <h3>₹{c[1].toLocaleString()}</h3>
                  <span>{c[3]}</span>
                </div>
                <div className="card-icon"><i className={`bi ${c[2]}`}></i></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row g-3 mt-2">
        <div className="col-lg-7">
          <div className="panel h-100">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold mb-0">Monthly Overview</h5>
              <span className="badge bg-primary">Live Summary</span>
            </div>

            <div className="summary-row"><span>Monthly Income</span><strong>₹{Number(data.monthIncome || 0).toLocaleString()}</strong></div>
            <div className="summary-row"><span>Monthly Expense</span><strong>₹{Number(data.monthExpense || 0).toLocaleString()}</strong></div>
            <div className="summary-row"><span>Balance Money</span><strong>Rs {cashBalance.toLocaleString()}</strong></div>
            <div className="summary-row"><span>Top Spending Category</span><strong>{data.topCategory?.category || "No expenses yet"}</strong></div>
            <div className="summary-row"><span>Goal Savings</span><strong>₹{goalSavings.toLocaleString()}</strong></div>
            <div className="summary-row"><span>Savings Rate</span><strong>{savingsRate}%</strong></div>

            <div className="mt-4">
              <div className="d-flex justify-content-between mb-2">
                <span className="fw-semibold">Financial Health Score</span>
                <span className="fw-bold">{data.healthScore}/100</span>
              </div>
              <div className="progress big-progress">
                <div className="progress-bar" style={{ width: `${data.healthScore}%` }}>{data.healthScore}%</div>
              </div>
              <small className="text-muted">Score is based on income, expenses, cash and savings.</small>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="panel h-100">
            <h5 className="fw-bold mb-3">Quick Actions</h5>
            <div className="quick-grid">
              <button className="quick-action" onClick={() => onNavigate("transactions", { type: "Income" })}><i className="bi bi-plus-circle"></i>Add Income</button>
              <button className="quick-action" onClick={() => onNavigate("transactions", { type: "Expense" })}><i className="bi bi-dash-circle"></i>Add Expense</button>
              <button className="quick-action" onClick={() => onNavigate("transactions", { type: "Transfer" })}><i className="bi bi-arrow-left-right"></i>Transfer Money</button>
              <button className="quick-action" onClick={() => onNavigate("accounts")}><i className="bi bi-bank"></i>Add Account</button>
              <button className="quick-action" onClick={() => onNavigate("reports")}><i className="bi bi-file-earmark-text"></i>Export Report</button>
            </div>

            <div className="insight-box mt-4">
              <h6 className="fw-bold"><i className="bi bi-lightbulb"></i> Smart Insight</h6>
              <p className="mb-0">
                {expense > income && income > 0
                  ? "Your expenses are higher than your income. Reduce spending to improve savings."
                  : savings > 0
                  ? `Good job! You saved ₹${savings.toLocaleString()} overall.`
                  : "Add income and expense records to generate insights."}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="panel mt-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Recent Transactions</h5>
          <span className="text-muted">Latest 8 records</span>
        </div>

        <div className="table-responsive">
          <table className="table table-hover modern-table">
            <thead><tr><th>Date</th><th>Account</th><th>Type</th><th>Category</th><th>Amount</th></tr></thead>
            <tbody>
              {data.recent.length === 0 ? (
                <tr><td colSpan="5" className="text-center text-muted py-4">No transactions yet.</td></tr>
              ) : (
                data.recent.map((t) => (
                  <tr key={t.id}>
                    <td>{t.transaction_date}</td>
                    <td>{accountNameFor(t)}</td>
                    <td><span className={`badge ${t.type === "Income" ? "bg-success" : t.type === "Expense" ? "bg-danger" : "bg-info"}`}>{t.type}</span></td>
                    <td>{t.category}</td>
                    <td className={amountClassFor(t)}>
                      {amountPrefixFor(t)}₹{Number(t.amount).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
