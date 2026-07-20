import React,{useEffect,useState}from"react";
import api from"../services/api";
import{Notice}from"../components/Notice";

const money=value=>"Rs "+Number(value||0).toLocaleString("en-IN",{maximumFractionDigits:0});
const today=()=>new Date().toISOString().slice(0,10);
const monthStart=()=>{
 const d=new Date();
 return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-01`;
};

export default function Ledger(){
 const[accounts,setAccounts]=useState([]),[rows,setRows]=useState([]),[summary,setSummary]=useState(null);
 const[filters,setFilters]=useState({account_id:"",start:monthStart(),end:today()});
 const[message,setMessage]=useState(null),[loading,setLoading]=useState(false);

 const loadAccounts=async()=>setAccounts((await api.get("/accounts")).data);
 const loadLedger=async(current=filters)=>{
  setLoading(true);setMessage(null);
  const params=new URLSearchParams(Object.entries(current).filter(([,v])=>v));
  try{
   const{data}=await api.get(`/ledger?${params}`);
   setRows(data.rows||[]);setSummary(data.summary||null);
  }catch(err){
   setMessage({type:"danger",text:err.response?.data?.error||"Could not load ledger"});
  }finally{setLoading(false)}
 };
 useEffect(()=>{loadAccounts();loadLedger()},[]);
 const updateFilter=changes=>{
  const next={...filters,...changes};
  setFilters(next);loadLedger(next);
 };
 const reset=()=>updateFilter({account_id:"",start:"",end:""});
 const selectedName=filters.account_id?accounts.find(x=>String(x.id)===String(filters.account_id))?.account_name:"All accounts";

 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Ledger</h2><p className="text-muted mb-0">Account-wise debit, credit and running balance for every money movement.</p></div><span className="ai-badge"><i className="bi bi-journal-text"/> Running Balance</span></div>
 <Notice message={message} onClose={()=>setMessage(null)}/>
 <div className="panel month-picker-panel">
  <div><h5 className="fw-bold mb-1">Ledger Filters</h5><p className="text-muted mb-0">{selectedName} {loading?"- loading...":""}</p></div>
  <div className="month-controls">
   <select className="form-select" value={filters.account_id} onChange={e=>updateFilter({account_id:e.target.value})}>
    <option value="">All accounts</option>
    {accounts.map(a=><option key={a.id} value={a.id}>{a.account_name}</option>)}
   </select>
   <input className="form-control" type="date" value={filters.start} onChange={e=>updateFilter({start:e.target.value})}/>
   <input className="form-control" type="date" value={filters.end} onChange={e=>updateFilter({end:e.target.value})}/>
   <button className="btn btn-outline-secondary" type="button" onClick={reset}>All Time</button>
  </div>
 </div>
 <div className="row g-3 mb-3">
  <div className="col-lg-3 col-md-6"><div className="mini-stat"><span>Opening Balance</span><h4>{money(summary?.openingBalance)}</h4></div></div>
  <div className="col-lg-3 col-md-6"><div className="mini-stat expense-stat"><span>Debit</span><h4>{money(summary?.debitTotal)}</h4><small>Money out</small></div></div>
  <div className="col-lg-3 col-md-6"><div className="mini-stat income-stat"><span>Credit</span><h4>{money(summary?.creditTotal)}</h4><small>Money in</small></div></div>
  <div className="col-lg-3 col-md-6"><div className="mini-stat balance-stat"><span>Closing Balance</span><h4>{money(summary?.closingBalance)}</h4></div></div>
 </div>
 <div className="panel mb-3"><h5 className="fw-bold mb-2">Ledger Algorithm</h5><p className="text-muted mb-0">Running balance is calculated as opening balance plus credits minus debits. Transfers create two ledger rows: debit from the source account and credit to the destination account.</p></div>
 <div className="panel">
  <div className="d-flex justify-content-between align-items-center mb-3">
   <h5 className="fw-bold mb-0">Ledger Entries</h5>
   <span className="text-muted">{rows.length} rows</span>
  </div>
  <div className="table-responsive month-table">
   <table className="table table-hover modern-table">
    <thead><tr><th>Date</th><th>Account</th><th>Particulars</th><th>Reference</th><th>Debit</th><th>Credit</th><th>Running Balance</th></tr></thead>
    <tbody>
     {rows.length?rows.map((r,i)=><tr key={`${r.source}-${r.source_id}-${r.account_id}-${i}`}>
      <td>{r.date}</td>
      <td><span className="fw-semibold">{r.account_name}</span><small className="d-block text-muted">{r.account_type}</small></td>
      <td>{r.particulars}</td>
      <td><span className="badge bg-primary">{r.reference}</span></td>
      <td className="text-danger fw-bold">{r.debit?money(r.debit):"-"}</td>
      <td className="text-success fw-bold">{r.credit?money(r.credit):"-"}</td>
      <td className="fw-bold">{money(r.running_balance)}</td>
     </tr>):<tr><td colSpan="7" className="text-center text-muted py-4">{loading?"Loading ledger...":"No ledger entries for this filter."}</td></tr>}
    </tbody>
   </table>
  </div>
 </div>
 </>;
}
