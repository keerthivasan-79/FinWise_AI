import React,{useEffect,useState}from"react";
import api from"../services/api";
import{Notice,ConfirmDialog}from"../components/Notice";

const money=value=>"Rs "+Number(value||0).toLocaleString("en-IN",{maximumFractionDigits:0});
const today=()=>new Date().toISOString().slice(0,10);
const INCOME_CATEGORIES=["Salary","Business","Interest","Gift","Refund","Other"];
const EXPENSE_CATEGORIES=["Food","Groceries","Travel","Shopping","Bills","Rent","College","Education","Medical","Insurance","Entertainment","Fuel","EMI","Utilities","Personal Care","Other"];

export default function FutureHub(){
 const[tab,setTab]=useState("summary"),[overview,setOverview]=useState(null),[accounts,setAccounts]=useState([]);
 const[recurring,setRecurring]=useState([]),[duplicates,setDuplicates]=useState([]);
 const[message,setMessage]=useState(null),[deleteRecurring,setDeleteRecurring]=useState(null);
 const[recForm,setRecForm]=useState({account_id:"",type:"Expense",category:"Bills",amount:"",description:"",frequency:"Monthly",next_run:today()});

 const load=async()=>{
  const[a,o,r,d]=await Promise.all([
   api.get("/accounts"),api.get("/finance/overview"),api.get("/recurring"),
   api.get("/transactions/duplicates")
  ]);
  setAccounts(a.data);setOverview(o.data);setRecurring(r.data);setDuplicates(d.data);
  setRecForm(current=>({...current,account_id:current.account_id||a.data[0]?.id||""}));
 };
 useEffect(()=>{load().catch(err=>setMessage({type:"danger",text:err.response?.data?.error||"Could not load smart tools"}))},[]);

 const addRecurring=async e=>{
  e.preventDefault();
  try{await api.post("/recurring",recForm);setMessage({type:"success",text:"Auto entry added"});setRecForm({...recForm,amount:"",description:""});load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not add auto entry"})}
 };
 const processRecurring=async()=>{
  try{const{data}=await api.post("/recurring/process");setMessage({type:"info",text:`${data.created} recurring transactions created`});load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not run entries"})}
 };
 const removeRecurring=async()=>{
  if(!deleteRecurring)return;
  try{await api.delete(`/recurring/${deleteRecurring.id}`);setMessage({type:"success",text:"Auto entry deleted"});setDeleteRecurring(null);load()}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not delete auto entry"});setDeleteRecurring(null)}
 };
 const changeRecurringType=type=>setRecForm({...recForm,type,category:type==="Income"?"Salary":"Bills"});

 if(!overview)return <div className="panel">Loading smart tools...</div>;
 const metricCards=[
  ["Total Value",overview.netWorth,"bi-safe","Cash, goals and assets after liabilities"],
  ["Assets",overview.assets,"bi-wallet2","Accounts, investments and goal savings"],
  ["Liabilities",overview.liabilities,"bi-credit-card","Loans and credit card balance"],
  ["Next Month Expense",overview.forecast,"bi-calendar2-week","Based on recent monthly spending"]
 ];
 const tabs=[["summary","Summary","bi-grid"],["auto","Auto Entries","bi-repeat"]];

 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Smart Tools</h2><p className="text-muted mb-0">Simple checks for planning and repeat entries.</p></div></div>
 <Notice message={message} onClose={()=>setMessage(null)}/>
 <div className="hub-tabs mb-3">{tabs.map(x=><button key={x[0]} className={tab===x[0]?"active":""} onClick={()=>setTab(x[0])}><i className={`bi ${x[2]} me-1`}/>{x[1]}</button>)}</div>

 {tab==="summary"&&<><div className="row g-3">
  {metricCards.map(card=><div className="col-lg-3 col-md-6" key={card[0]}><div className="panel hub-metric"><i className={`bi ${card[2]}`}/><span>{card[0]}</span><strong>{money(card[1])}</strong><small>{card[3]}</small></div></div>)}
 </div>
 <div className="row g-3 mt-1"><div className="col-lg-7"><div className="panel h-100"><h5 className="fw-bold mb-3">Suggestions</h5>{overview.recommendations.map((x,i)=><div className="ai-tip" key={i}><i className="bi bi-lightbulb"/><span>{x}</span></div>)}</div></div>
 <div className="col-lg-5"><div className="panel h-100"><h5 className="fw-bold mb-3">Checks</h5><div className="summary-row"><span>Possible duplicates</span><strong>{duplicates.length}</strong></div><div className="summary-row"><span>Unusual expenses</span><strong>{overview.unusual.length}</strong></div><div className="summary-row"><span>Possible subscriptions</span><strong>{overview.subscriptions.length}</strong></div></div></div></div>
 {overview.subscriptions.length>0&&<div className="panel mt-3"><h5 className="fw-bold mb-3">Possible Subscriptions</h5>{overview.subscriptions.slice(0,5).map((x,i)=><div className="summary-row" key={i}><span>{x.merchant||x.category}</span><strong>{money(x.average_amount)}</strong></div>)}</div>}</>}

 {tab==="auto"&&<><div className="panel"><div className="d-flex justify-content-between align-items-center mb-3"><h5 className="fw-bold mb-0">Auto Entries</h5><button className="btn btn-outline-primary btn-sm" onClick={processRecurring}><i className="bi bi-play-circle me-1"/>Run Due Entries</button></div>
 <form className="row g-3" onSubmit={addRecurring}><div className="col-md-3"><label className="form-label">Account</label><select className="form-select" value={recForm.account_id} onChange={e=>setRecForm({...recForm,account_id:e.target.value})}>{accounts.length?accounts.map(a=><option value={a.id} key={a.id}>{a.account_name}</option>):<option value="">No account</option>}</select></div><div className="col-md-2"><label className="form-label">Type</label><select className="form-select" value={recForm.type} onChange={e=>changeRecurringType(e.target.value)}><option>Expense</option><option>Income</option></select></div><div className="col-md-2"><label className="form-label">Category</label><select className="form-select" value={recForm.category} onChange={e=>setRecForm({...recForm,category:e.target.value})}>{(recForm.type==="Income"?INCOME_CATEGORIES:EXPENSE_CATEGORIES).map(c=><option key={c}>{c}</option>)}</select></div><div className="col-md-2"><label className="form-label">Amount</label><input className="form-control" type="number" min="0.01" step="0.01" required value={recForm.amount} onChange={e=>setRecForm({...recForm,amount:e.target.value})}/></div><div className="col-md-3"><label className="form-label">Repeats</label><select className="form-select" value={recForm.frequency} onChange={e=>setRecForm({...recForm,frequency:e.target.value})}><option>Weekly</option><option>Monthly</option><option>Quarterly</option><option>Yearly</option></select></div><div className="col-md-3"><label className="form-label">Start Date</label><input className="form-control" type="date" value={recForm.next_run} onChange={e=>setRecForm({...recForm,next_run:e.target.value})}/></div><div className="col-md-6"><label className="form-label">Note</label><input className="form-control" placeholder="Rent, salary, EMI" value={recForm.description} onChange={e=>setRecForm({...recForm,description:e.target.value})}/></div><div className="col-md-3 d-flex align-items-end"><button className="btn btn-primary w-100" disabled={!accounts.length}>Add Auto Entry</button></div></form></div>
 <div className="panel mt-3"><h5 className="fw-bold mb-3">Saved Auto Entries</h5><div className="table-responsive"><table className="table modern-table"><thead><tr><th>Name</th><th>Account</th><th>Type</th><th>Repeats</th><th>Next Date</th><th>Amount</th><th></th></tr></thead><tbody>{recurring.length?recurring.map(x=><tr key={x.id}><td>{x.description||x.category}</td><td>{x.account_name}</td><td>{x.type}</td><td>{x.frequency}</td><td>{x.next_run}</td><td className={x.type==="Income"?"text-success fw-bold":"text-danger fw-bold"}>{money(x.amount)}</td><td><button className="btn btn-sm btn-outline-danger" onClick={()=>setDeleteRecurring(x)}><i className="bi bi-trash"/></button></td></tr>):<tr><td colSpan="7" className="text-center text-muted py-4">No auto entries yet.</td></tr>}</tbody></table></div></div></>}

 <ConfirmDialog state={deleteRecurring&&{title:"Delete auto entry",message:"Delete this auto entry?",confirmText:"Delete"}} onCancel={()=>setDeleteRecurring(null)} onConfirm={removeRecurring}/>
 </>;
}
