import React, { useEffect, useState } from "react";
import api from "../services/api";
import {Notice,ConfirmDialog} from "../components/Notice";

export default function Transactions({ initialType = "Expense" }) {
  const [accounts, setAccounts] = useState([]);
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState("");
  const [aiHint, setAiHint] = useState("");
  const [statement, setStatement] = useState({ account_id: "", file: null });
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [importHistory, setImportHistory] = useState([]);
  const [selected, setSelected] = useState([]);
  const [bulkCategory, setBulkCategory] = useState("Other");
  const [message, setMessage] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [undoTarget, setUndoTarget] = useState(null);
  const [splitTarget, setSplitTarget] = useState(null);
  const [splitForm, setSplitForm] = useState({ category: "Other", amount: "" });
  const [form, setForm] = useState({
    account_id: "",
    type: initialType,
    category: "Food",
    amount: "",
    description: "",
    transaction_date: new Date().toISOString().slice(0,10),
    payment_method: "UPI",
    transfer_to_account: "",
    merchant: "",
    tags: "",
    make_recurring: false,
    frequency: "Monthly"
  });

  const categories = ["Salary","Food","Groceries","Travel","Shopping","Bills","Rent","College","Education","Medical","Insurance","Entertainment","Fuel","EMI","Transfer","Other"];
  const transferMode = form.type === "Transfer";
  const availableTransferTargets = accounts.filter(a => String(a.id) !== String(form.account_id));
  const describeAccount = a => `${a.account_name} - Rs ${Number(a.current_balance || 0).toLocaleString()}`;
  const accountNameFor = row => row.type === "Transfer" && row.transfer_to_account_name ? `${row.account_name} -> ${row.transfer_to_account_name}` : row.account_name;
  const amountClassFor = row => row.type === "Income" ? "text-success fw-bold" : row.type === "Expense" ? "text-danger fw-bold" : "text-info fw-bold";
  const amountPrefixFor = row => row.type === "Income" ? "+" : row.type === "Expense" ? "-" : "";
  const selectTransactionType = type => {
    setForm(current => ({
      ...current,
      type,
      category: type === "Transfer" ? "Transfer" : current.category === "Transfer" ? (type === "Income" ? "Salary" : "Food") : current.category,
      payment_method: type === "Transfer" ? "Bank Transfer" : current.payment_method,
      transfer_to_account: type === "Transfer" ? current.transfer_to_account : ""
    }));
  };
  const changeSourceAccount = account_id => {
    setForm(current => ({
      ...current,
      account_id,
      transfer_to_account: String(current.transfer_to_account) === String(account_id) ? "" : current.transfer_to_account
    }));
  };

  const load = async () => {
    const a = (await api.get("/accounts")).data;
    setAccounts(a);
    setStatement(s => ({...s, account_id:s.account_id || a[0]?.id || ""}));
    if (a.length && !form.account_id) setForm(f => ({...f, account_id:a[0].id}));
    const t = (await api.get(`/transactions?search=${search}`)).data;
    setRows(t);
    try { setImportHistory((await api.get("/statements/history")).data); } catch { setImportHistory([]); }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    selectTransactionType(initialType);
  }, [initialType]);

  const smartDescription = async (value) => {
    setForm(current => ({...current, description:value}));
    if (value.trim().length < 3) { setAiHint(""); return; }
    try {
      const {data} = await api.post("/ai/categorize", {description:value});
      if (data.matched) {
        setForm(current => ({...current, description:value, category:data.category}));
        setAiHint(`${data.algorithm || "AI"} selected ${data.category} (${data.confidence}% confidence)`);
      } else setAiHint("No keyword match — choose a category manually");
    } catch { setAiHint(""); }
  };

  const previewStatement = async (e) => {
    e.preventDefault(); setMessage(null);
    if (!statement.account_id || !statement.file) return setMessage({type:"warning",text:"Choose an account and statement file"});
    const body=new FormData(); body.append("file",statement.file); body.append("account_id",statement.account_id); setImporting(true);
    try {
      const {data}=await api.post("/statements/preview",body);
      const duplicates=data.rows.filter(r=>r.duplicate).length;
      setPreview({...data,account_id:statement.account_id});
      setMessage({type:duplicates?"warning":"info",text:duplicates?`${duplicates} duplicate rows were detected and unselected.`:"Statement preview ready."});
    }
    catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Statement preview failed"})} finally{setImporting(false)}
  };
  const updatePreview=(index,changes)=>setPreview(p=>({...p,rows:p.rows.map((r,i)=>i===index?{...r,...changes}:r)}));
  const confirmImport=async()=>{const selectedRows=preview.rows.filter(r=>r.selected);if(!selectedRows.length)return setMessage({type:"warning",text:"Select at least one row"});setImporting(true);setMessage(null);try{const{data}=await api.post("/statements/confirm",preview);setMessage({type:"success",text:`Imported ${data.imported} transactions${data.skippedDuplicates?`; skipped ${data.skippedDuplicates} duplicates`:""}.`});setPreview(null);setStatement(s=>({...s,file:null}));load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Import failed"})}finally{setImporting(false)}};
  const undoImport=async()=>{if(!undoTarget)return;try{const{data}=await api.delete("/statements/"+undoTarget.id);setMessage({type:"success",text:data.message||"Import undone"});setUndoTarget(null);load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not undo import"});setUndoTarget(null)}};

  const submit = async (e) => {
    e.preventDefault();
    setMessage(null);
    if (!form.account_id) return setMessage({type:"warning",text:"Add/select an account first"});
    if (!form.amount || Number(form.amount) <= 0) return setMessage({type:"warning",text:"Enter valid amount"});
    if (form.type === "Transfer" && accounts.length < 2) return setMessage({type:"warning",text:"Add at least two accounts to transfer money"});
    if (form.type === "Transfer" && !form.transfer_to_account) return setMessage({type:"warning",text:"Select target account"});
    if (form.type === "Transfer" && String(form.account_id) === String(form.transfer_to_account)) return setMessage({type:"warning",text:"Choose two different accounts"});
    try {
      const {data} = await api.post("/transactions", form);
      setMessage({type:"success",text:data.message||"Transaction saved"});
      setForm({...form, amount:"", description:"", merchant:"", tags:"", transfer_to_account:"", make_recurring:false});
      load();
    } catch (err) {
      setMessage({type:"danger",text:err.response?.data?.error || "Failed to save transaction"});
    }
  };

  const del = async () => {
    if (!deleteTarget) return;
    try{await api.delete(`/transactions/${deleteTarget.id}`);setMessage({type:"success",text:"Transaction deleted and balance restored"});setDeleteTarget(null);load()}
    catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not delete transaction"});setDeleteTarget(null)}
  };
  const attachReceipt = (id) => {
    const picker=document.createElement("input");picker.type="file";picker.accept=".jpg,.jpeg,.png,.pdf";
    picker.onchange=async()=>{if(!picker.files[0])return;const body=new FormData();body.append("file",picker.files[0]);try{await api.post(`/transactions/${id}/receipt`,body);setMessage({type:"success",text:"Receipt attached"});load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Upload failed"})}};
    picker.click();
  };
  const scanDuplicates=async()=>{const{data}=await api.get("/transactions/duplicates");setMessage({type:data.length?"warning":"success",text:data.length?`${data.length} possible duplicate groups found. Review matching date, amount and description records.`:"No duplicates found."})};
  const bulkEdit=async()=>{if(!selected.length)return setMessage({type:"warning",text:"Select transactions first"});try{await api.patch("/transactions/bulk",{ids:selected,changes:{category:bulkCategory}});setSelected([]);setMessage({type:"success",text:"Selected transactions updated"});load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not update selected transactions"})}};
  const openSplit=row=>{setSplitTarget(row);setSplitForm({category:"Other",amount:String(Number(row.amount)/2)})};
  const saveSplit=async e=>{e.preventDefault();const amount=Number(splitForm.amount);if(!amount||amount>=Number(splitTarget.amount))return setMessage({type:"warning",text:"Enter an amount below the transaction total"});try{await api.post(`/transactions/${splitTarget.id}/splits`,{splits:[{category:splitTarget.category,amount:Number(splitTarget.amount)-amount},{category:splitForm.category,amount}]});setMessage({type:"success",text:"Transaction split saved"});setSplitTarget(null)}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not split transaction"})}};

  const income = rows.filter(r=>r.type==="Income").reduce((s,r)=>s+Number(r.amount||0),0);
  const expense = rows.filter(r=>r.type==="Expense").reduce((s,r)=>s+Number(r.amount||0),0);

  return (
    <>
      <div className="dashboard-header">
        <div>
          <h2 className="page-title mb-1">Transactions</h2>
          <p className="text-muted mb-0">Add income, expenses, transfers and manage history.</p>
        </div>
        <div className="quick-date"><i className="bi bi-arrow-left-right"></i>{rows.length} Records</div>
      </div>
      <Notice message={message} onClose={()=>setMessage(null)}/>

      <div className="statement-import panel mb-4">
        <div className="statement-copy"><span className="statement-icon"><i className="bi bi-file-earmark-spreadsheet"/></span><div><h5 className="fw-bold mb-1">Import Bank Statement</h5><p className="text-muted mb-0">Preview and correct CSV, Excel or text-based PDF transactions before importing.</p></div></div>
        <form className="statement-form" onSubmit={previewStatement}><select className="form-select" value={statement.account_id} onChange={e=>setStatement({...statement,account_id:e.target.value})}><option value="">Select account</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.account_name}</option>)}</select><input key={statement.file?statement.file.name:"empty"} className="form-control" type="file" accept=".csv,.xlsx,.xls,.pdf" onChange={e=>setStatement({...statement,file:e.target.files[0]||null})}/><button className="btn btn-primary" disabled={importing}>{importing?"Analysing...":"Preview Statement"}</button></form>
      </div>
      {preview&&<div className="panel mb-4"><div className="d-flex justify-content-between align-items-center mb-3"><div><h5 className="fw-bold mb-1">Review Transactions</h5><small className="text-muted">{preview.rows.filter(r=>r.selected).length} of {preview.rows.length} selected</small></div><div className="d-flex gap-2"><button className="btn btn-outline-secondary" onClick={()=>setPreview(null)}>Cancel</button><button className="btn btn-success" disabled={importing} onClick={confirmImport}>Confirm Import</button></div></div><div className="table-responsive statement-preview"><table className="table modern-table"><thead><tr><th><input type="checkbox" checked={preview.rows.every(r=>r.selected)} onChange={e=>setPreview(p=>({...p,rows:p.rows.map(r=>({...r,selected:e.target.checked&&!r.duplicate}))}))}/></th><th>Date</th><th>Description</th><th>Type</th><th>Category</th><th>Amount</th></tr></thead><tbody>{preview.rows.map((r,i)=><tr key={i} className={!r.selected?"opacity-50":""}><td><input type="checkbox" checked={r.selected} disabled={r.duplicate} onChange={e=>updatePreview(i,{selected:e.target.checked})}/></td><td>{r.transaction_date}</td><td className="statement-description">{r.description}{r.duplicate&&<span className="badge bg-warning text-dark ms-2">Duplicate</span>}</td><td><select className="form-select form-select-sm" value={r.type} disabled={r.duplicate} onChange={e=>updatePreview(i,{type:e.target.value})}><option>Income</option><option>Expense</option></select></td><td><select className="form-select form-select-sm" value={r.category} disabled={r.duplicate} onChange={e=>updatePreview(i,{category:e.target.value})}>{categories.map(c=><option key={c}>{c}</option>)}</select></td><td className="fw-bold">₹{Number(r.amount).toLocaleString()}</td></tr>)}</tbody></table></div></div>}
      {importHistory.length>0&&<div className="panel mb-4"><h5 className="fw-bold mb-3">Statement Import History</h5><div className="table-responsive"><table className="table modern-table"><thead><tr><th>Date</th><th>File</th><th>Account</th><th>Rows</th><th>Income</th><th>Expense</th><th></th></tr></thead><tbody>{importHistory.map(x=><tr key={x.id}><td>{new Date(x.created_at).toLocaleDateString()}</td><td>{x.file_name}</td><td>{x.account_name}</td><td>{x.imported_rows}</td><td className="text-success">₹{Number(x.income).toLocaleString()}</td><td className="text-danger">₹{Number(x.expense).toLocaleString()}</td><td><button className="btn btn-sm btn-outline-danger" onClick={()=>setUndoTarget(x)} title={x.linked_rows?"Undo import":"Clean import history"}><i className="bi bi-arrow-counterclockwise"/></button></td></tr>)}</tbody></table></div></div>}

      <div className="row g-3 mb-3">
        <div className="col-md-4"><div className="mini-stat income-stat"><span>Total Income</span><h4>₹{income.toLocaleString()}</h4></div></div>
        <div className="col-md-4"><div className="mini-stat expense-stat"><span>Total Expense</span><h4>₹{expense.toLocaleString()}</h4></div></div>
        <div className="col-md-4"><div className="mini-stat balance-stat"><span>Net Flow</span><h4>₹{(income-expense).toLocaleString()}</h4></div></div>
      </div>

      <div className="panel">
        <div className="transaction-form-header">
          <div>
            <h5 className="fw-bold mb-1">{transferMode ? "Transfer Between Accounts" : "Add Transaction"}</h5>
            <small className="text-muted">{transferMode ? "Move money from one account to another." : "Add income or expense activity."}</small>
          </div>
          <div className="transaction-mode-switch" role="group" aria-label="Transaction type">
            <button type="button" className={form.type==="Income"?"active":""} onClick={()=>selectTransactionType("Income")}><i className="bi bi-plus-circle"/>Income</button>
            <button type="button" className={form.type==="Expense"?"active":""} onClick={()=>selectTransactionType("Expense")}><i className="bi bi-dash-circle"/>Expense</button>
            <button type="button" className={transferMode?"active":""} onClick={()=>selectTransactionType("Transfer")}><i className="bi bi-arrow-left-right"/>Transfer</button>
          </div>
        </div>
        <form className="row g-3" onSubmit={submit}>
          <div className="col-md-3">
            <label className="form-label">{transferMode ? "From Account" : "Account"}</label>
            <select className="form-select" value={form.account_id} onChange={e=>changeSourceAccount(e.target.value)}>
              {accounts.length===0 ? <option value="">No account</option> : accounts.map(a=><option key={a.id} value={a.id}>{describeAccount(a)}</option>)}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label">Type</label>
            <select className="form-select" value={form.type} onChange={e=>selectTransactionType(e.target.value)}>
              <option>Income</option><option>Expense</option><option>Transfer</option>
            </select>
          </div>
          {!transferMode && <div className="col-md-2">
            <label className="form-label">Category</label>
            <select className="form-select" value={form.category} onChange={e=>setForm({...form, category:e.target.value})}>
              {categories.filter(c=>c!=="Transfer").map(c=><option key={c}>{c}</option>)}
            </select>
          </div>}
          <div className="col-md-2">
            <label className="form-label">Amount</label>
            <input className="form-control" value={form.amount} placeholder="500" onChange={e=>setForm({...form, amount:e.target.value})}/>
          </div>
          <div className="col-md-3">
            <label className="form-label">Date</label>
            <input type="date" className="form-control" value={form.transaction_date} onChange={e=>setForm({...form, transaction_date:e.target.value})}/>
          </div>
          <div className="col-md-3">
            <label className="form-label">Payment Method</label>
            <select className="form-select" value={form.payment_method} onChange={e=>setForm({...form, payment_method:e.target.value})}>
              <option>UPI</option><option>Cash</option><option>Debit Card</option><option>Credit Card</option><option>Bank Transfer</option>
            </select>
          </div>
          {form.type==="Transfer" && (
            <div className="col-md-3">
              <label className="form-label">To Account</label>
              <select className="form-select" value={form.transfer_to_account} onChange={e=>setForm({...form, transfer_to_account:e.target.value})}>
                <option value="">Select destination account</option>{availableTransferTargets.map(a=><option key={a.id} value={a.id}>{describeAccount(a)}</option>)}
              </select>
            </div>
          )}
          <div className="col-md-6">
            <label className="form-label">Description</label>
            <input className="form-control" value={form.description} placeholder="Notes" onChange={e=>smartDescription(e.target.value)}/>
            {aiHint && <small className="ai-category-hint"><i className="bi bi-stars"></i> {aiHint}</small>}
          </div>
          <div className="col-md-3"><label className="form-label">Merchant</label><input className="form-control" value={form.merchant} placeholder="Merchant or payer" onChange={e=>setForm({...form,merchant:e.target.value})}/></div>
          <div className="col-md-3"><label className="form-label">Tags</label><input className="form-control" value={form.tags} placeholder="tax, work, college" onChange={e=>setForm({...form,tags:e.target.value})}/></div>
          <div className="col-md-3"><div className="form-check form-switch mt-4"><input className="form-check-input" type="checkbox" checked={form.make_recurring} onChange={e=>setForm({...form,make_recurring:e.target.checked})}/><label className="form-check-label">Make recurring</label></div></div>
          {form.make_recurring&&<div className="col-md-3"><label className="form-label">Frequency</label><select className="form-select" value={form.frequency} onChange={e=>setForm({...form,frequency:e.target.value})}><option>Weekly</option><option>Monthly</option><option>Quarterly</option><option>Yearly</option></select></div>}
          <div className="col-12"><button className="btn btn-success px-4"><i className="bi bi-check-circle me-2"></i>{transferMode ? "Save Transfer" : "Save Transaction"}</button></div>
        </form>
      </div>

      <div className="panel mt-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="d-flex align-items-center gap-2"><h5 className="fw-bold mb-0">Transaction History</h5><button className="btn btn-sm btn-outline-warning" onClick={scanDuplicates}><i className="bi bi-copy me-1"/>Scan duplicates</button></div>
          <div className="d-flex gap-2 flex-wrap"><div className="input-group transaction-search">
            <input className="form-control" placeholder="Search" value={search} onChange={e=>setSearch(e.target.value)}/>
            <button className="btn btn-primary" onClick={load}><i className="bi bi-search"></i></button>
          </div>{selected.length>0&&<div className="input-group transaction-search"><select className="form-select" value={bulkCategory} onChange={e=>setBulkCategory(e.target.value)}>{categories.map(c=><option key={c}>{c}</option>)}</select><button className="btn btn-outline-primary" onClick={bulkEdit}>Update {selected.length}</button></div>}</div>
        </div>
        <div className="table-responsive">
          <table className="table table-hover modern-table">
            <thead><tr><th><input type="checkbox" checked={rows.length>0&&selected.length===rows.length} onChange={e=>setSelected(e.target.checked?rows.map(r=>r.id):[])}/></th><th>Date</th><th>Account</th><th>Type</th><th>Category</th><th>Amount</th><th>Payment</th><th>Description</th><th>Tags</th><th>Action</th></tr></thead>
            <tbody>{rows.length===0 ? <tr><td colSpan="10" className="text-center text-muted py-4">No transactions found.</td></tr> :
              rows.map(r=>(
                <tr key={r.id}>
                  <td><input type="checkbox" checked={selected.includes(r.id)} onChange={e=>setSelected(e.target.checked?[...selected,r.id]:selected.filter(x=>x!==r.id))}/></td><td>{r.transaction_date}</td><td>{accountNameFor(r)}</td>
                  <td><span className={`badge ${r.type==="Income"?"bg-success":r.type==="Expense"?"bg-danger":"bg-info"}`}>{r.type}</span></td>
                  <td>{r.category}</td>
                  <td className={amountClassFor(r)}>{amountPrefixFor(r)}₹{Number(r.amount).toLocaleString()}</td>
                  <td>{r.payment_method}</td><td>{r.description}</td><td><small>{r.tags||"—"}</small></td>
                  <td><div className="d-flex gap-1"><button className="btn btn-sm btn-outline-info" onClick={()=>openSplit(r)} title="Split transaction"><i className="bi bi-diagram-2"/></button><button className={`btn btn-sm ${r.receipt_path?"btn-success":"btn-outline-secondary"}`} onClick={()=>attachReceipt(r.id)} title="Attach receipt"><i className="bi bi-paperclip"/></button><button className="btn btn-sm btn-outline-danger" onClick={()=>setDeleteTarget(r)}><i className="bi bi-trash"></i></button></div></td>
                </tr>
              ))
            }</tbody>
          </table>
        </div>
      </div>
      <ConfirmDialog state={deleteTarget&&{title:"Delete transaction",message:"Delete this transaction and restore the account balance?",confirmText:"Delete"}} onCancel={()=>setDeleteTarget(null)} onConfirm={del}/>
      <ConfirmDialog state={undoTarget&&{title:"Undo statement import",message:undoTarget.linked_rows?"Undo this import and restore the account balance?":"No linked rows remain. Clean this import history record?",confirmText:undoTarget.linked_rows?"Undo Import":"Clean History",confirmClass:"btn-warning"}} onCancel={()=>setUndoTarget(null)} onConfirm={undoImport}/>
      {splitTarget&&<div className="modal-backdrop-custom"><div className="goal-dialog"><div className="d-flex justify-content-between"><h4>Split Transaction</h4><button className="btn-close" onClick={()=>setSplitTarget(null)}/></div><p className="text-muted">{splitTarget.description||splitTarget.category} - ₹{Number(splitTarget.amount).toLocaleString()}</p><form onSubmit={saveSplit}><label className="form-label">Second split category</label><select className="form-select mb-3" value={splitForm.category} onChange={e=>setSplitForm({...splitForm,category:e.target.value})}>{categories.filter(c=>c!=="Transfer").map(c=><option key={c}>{c}</option>)}</select><label className="form-label">Amount for second split</label><input autoFocus className="form-control mb-3" type="number" min="0.01" step="0.01" value={splitForm.amount} onChange={e=>setSplitForm({...splitForm,amount:e.target.value})}/><button className="btn btn-success w-100">Save Split</button></form></div></div>}
    </>
  );
}
