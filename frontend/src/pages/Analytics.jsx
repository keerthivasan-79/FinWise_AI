import React,{useEffect,useMemo,useState}from"react";
import api from"../services/api";
import{Pie,Bar}from"react-chartjs-2";
import{Chart as ChartJS,ArcElement,BarElement,CategoryScale,LinearScale,Tooltip,Legend}from"chart.js";

ChartJS.register(ArcElement,BarElement,CategoryScale,LinearScale,Tooltip,Legend);

const COLORS=[
 "#2563eb","#059669","#dc2626","#7c3aed","#f97316","#0891b2",
 "#ca8a04","#be185d","#4338ca","#16a34a","#ea580c","#475569"
];
const colorFor=index=>COLORS[index%COLORS.length];
const money=value=>"Rs "+Number(value||0).toLocaleString("en-IN",{maximumFractionDigits:0});
const toMonthValue=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}`;
const currentMonth=()=>toMonthValue(new Date());
const monthName=value=>new Date(value+"-01T00:00:00").toLocaleDateString("en-IN",{month:"long",year:"numeric"});
const shiftMonth=(value,delta)=>{
 const[y,m]=value.split("-").map(Number);
 const d=new Date(y,m-1+delta,1);
 return toMonthValue(d);
};
const monthRange=value=>{
 const[y,m]=value.split("-").map(Number);
 const end=new Date(y,m,0).getDate();
 return{start:`${value}-01`,end:`${value}-${String(end).padStart(2,"0")}`};
};
const isDarkTheme=()=>{
 if(typeof document==="undefined")return false;
 const theme=document.documentElement.dataset.theme||"system";
 return theme==="dark"||(theme==="system"&&typeof window!=="undefined"&&window.matchMedia?.("(prefers-color-scheme: dark)").matches);
};

export default function Analytics(){
 const[cat,setCat]=useState([]),[monthly,setMonthly]=useState([]),[selectedMonth,setSelectedMonth]=useState(currentMonth());
 const[monthRows,setMonthRows]=useState([]),[goalMoves,setGoalMoves]=useState([]),[loadingMonth,setLoadingMonth]=useState(false);
 const[darkChart,setDarkChart]=useState(isDarkTheme);
 useEffect(()=>{(async()=>{setCat((await api.get("/analytics/category")).data);setMonthly((await api.get("/analytics/monthly")).data)})()},[]);
 useEffect(()=>{const load=async()=>{const{start,end}=monthRange(selectedMonth);setLoadingMonth(true);try{const[tx,goals]=await Promise.all([api.get(`/transactions?start=${start}&end=${end}`),api.get(`/savings/activity?start=${start}&end=${end}`)]);setMonthRows(tx.data);setGoalMoves(goals.data)}finally{setLoadingMonth(false)}};load()},[selectedMonth]);
 useEffect(()=>{const update=()=>setDarkChart(isDarkTheme());const observer=typeof MutationObserver!=="undefined"?new MutationObserver(update):null;observer?.observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});const media=window.matchMedia?.("(prefers-color-scheme: dark)");media?.addEventListener?.("change",update);return()=>{observer?.disconnect();media?.removeEventListener?.("change",update)}},[]);
 const predicted=monthly.length?Math.round(monthly.slice(-3).reduce((s,x)=>s+Number(x.total),0)/Math.min(3,monthly.length)):0;
 const selectedSummary=useMemo(()=>{
  const income=monthRows.filter(x=>x.type==="Income").reduce((s,x)=>s+Number(x.amount||0),0);
  const expense=monthRows.filter(x=>x.type==="Expense").reduce((s,x)=>s+Number(x.amount||0),0);
  const byCategory={};
  monthRows.filter(x=>x.type==="Expense").forEach(x=>{byCategory[x.category||"Other"]=(byCategory[x.category||"Other"]||0)+Number(x.amount||0)});
  const top=Object.entries(byCategory).sort((a,b)=>b[1]-a[1])[0];
  const goalDeposits=goalMoves.filter(x=>x.action==="Deposit").reduce((s,x)=>s+Number(x.amount||0),0);
  const goalWithdrawals=goalMoves.filter(x=>x.action==="Withdraw").reduce((s,x)=>s+Number(x.amount||0),0);
  return{income,expense,net:income-expense,goalDeposits,goalWithdrawals,top:top?{category:top[0],total:top[1]}:null};
 },[monthRows,goalMoves]);
 const chartText=darkChart?"#e5e7eb":"#334155";
 const chartGrid=darkChart?"#334155":"#e2e8f0";
 const pieOptions=useMemo(()=>({responsive:true,plugins:{legend:{position:"bottom",labels:{color:chartText}}}}),[chartText]);
 const pieData=useMemo(()=>({
  labels:cat.map(x=>x.category),
  datasets:[{data:cat.map(x=>Number(x.total||0)),backgroundColor:cat.map((_,i)=>colorFor(i)),borderColor:darkChart?"#111827":"#ffffff",borderWidth:2}]
 }),[cat,darkChart]);
 const barData=useMemo(()=>({
  labels:monthly.map(x=>x.month),
  datasets:[{label:"Expense",data:monthly.map(x=>Number(x.total||0)),backgroundColor:monthly.map((_,i)=>colorFor(i+3)),borderColor:monthly.map((_,i)=>colorFor(i+3)),borderWidth:1,borderRadius:8}]
 }),[monthly]);
 const monthCategoryData=useMemo(()=>{
  const categories={};
  monthRows.filter(x=>x.type==="Expense").forEach(x=>{categories[x.category||"Other"]=(categories[x.category||"Other"]||0)+Number(x.amount||0)});
  const entries=Object.entries(categories).sort((a,b)=>b[1]-a[1]);
  return{labels:entries.map(x=>x[0]),datasets:[{data:entries.map(x=>x[1]),backgroundColor:entries.map((_,i)=>colorFor(i+5)),borderColor:darkChart?"#111827":"#ffffff",borderWidth:2}]};
 },[monthRows,darkChart]);
 const options=useMemo(()=>({responsive:true,plugins:{legend:{position:"bottom",labels:{color:chartText}}},scales:{x:{ticks:{color:chartText},grid:{color:chartGrid}},y:{beginAtZero:true,ticks:{color:chartText,callback:value=>money(value)},grid:{color:chartGrid}}}}),[chartText,chartGrid]);
 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Analytics</h2><p className="text-muted mb-0">Compare any month and review spending patterns.</p></div></div>
 <div className="alert alert-info">AI Expense Prediction: Next month expected expense around {money(predicted)}</div>
 <div className="panel month-picker-panel"><div><h5 className="fw-bold mb-1">Check different month</h5><p className="text-muted mb-0">{monthName(selectedMonth)} summary</p></div><div className="month-controls"><button className="btn btn-outline-primary" onClick={()=>setSelectedMonth(shiftMonth(selectedMonth,-1))}><i className="bi bi-chevron-left me-1"/>Previous</button><input className="form-control" type="month" value={selectedMonth} onChange={e=>setSelectedMonth(e.target.value||currentMonth())}/><button className="btn btn-outline-primary" onClick={()=>setSelectedMonth(shiftMonth(selectedMonth,1))}>Next<i className="bi bi-chevron-right ms-1"/></button><button className="btn btn-primary" onClick={()=>setSelectedMonth(currentMonth())}>This Month</button></div></div>
 <div className="row g-3 mb-3"><div className="col-lg col-md-4"><div className="mini-stat income-stat"><span>Income</span><h4>{money(selectedSummary.income)}</h4></div></div><div className="col-lg col-md-4"><div className="mini-stat expense-stat"><span>Expense</span><h4>{money(selectedSummary.expense)}</h4></div></div><div className="col-lg col-md-4"><div className="mini-stat balance-stat"><span>Net Flow</span><h4>{money(selectedSummary.net)}</h4></div></div><div className="col-lg col-md-4"><div className="mini-stat"><span>Saved to Goals</span><h4>{money(selectedSummary.goalDeposits)}</h4><small>{selectedSummary.goalWithdrawals?money(selectedSummary.goalWithdrawals)+" returned":"Not counted as expense"}</small></div></div><div className="col-lg col-md-4"><div className="mini-stat"><span>Top Category</span><h4>{selectedSummary.top?selectedSummary.top.category:"None"}</h4><small>{selectedSummary.top?money(selectedSummary.top.total):loadingMonth?"Loading...":"No expense"}</small></div></div></div>
 <div className="panel mb-3"><h5 className="fw-bold mb-3">Savings Goal Movement</h5><div className="table-responsive month-table"><table className="table table-hover modern-table"><thead><tr><th>Date</th><th>Goal</th><th>Account</th><th>Action</th><th>Amount</th></tr></thead><tbody>{goalMoves.length?goalMoves.slice(0,8).map(x=><tr key={x.id}><td>{new Date(x.created_at).toLocaleDateString()}</td><td>{x.goal_name}</td><td>{x.account_name}</td><td><span className={"badge "+(x.action==="Deposit"?"bg-success":"bg-warning text-dark")}>{x.action==="Deposit"?"Saved":"Returned"}</span></td><td className={x.action==="Deposit"?"text-success fw-bold":"text-warning fw-bold"}>{money(x.amount)}</td></tr>):<tr><td colSpan="5" className="text-center text-muted py-4">{loadingMonth?"Loading...":"No goal savings movement for this month."}</td></tr>}</tbody></table></div></div>
 <div className="row g-3 mb-3"><div className="col-lg-6"><div className="panel h-100"><h5>{monthName(selectedMonth)} Category Breakdown</h5>{monthCategoryData.labels.length?<Pie data={monthCategoryData} options={pieOptions}/>:<p className="text-muted mb-0">No expenses for this month.</p>}</div></div><div className="col-lg-6"><div className="panel h-100"><h5>{monthName(selectedMonth)} Transactions</h5><div className="table-responsive month-table"><table className="table table-hover modern-table"><thead><tr><th>Date</th><th>Type</th><th>Category</th><th>Amount</th></tr></thead><tbody>{monthRows.length?monthRows.slice(0,8).map(x=><tr key={x.id}><td>{x.transaction_date}</td><td>{x.type}</td><td>{x.category}</td><td className={x.type==="Income"?"text-success fw-bold":x.type==="Expense"?"text-danger fw-bold":"fw-bold"}>{money(x.amount)}</td></tr>):<tr><td colSpan="4" className="text-center text-muted py-4">{loadingMonth?"Loading...":"No transactions for this month."}</td></tr>}</tbody></table></div></div></div></div>
 <div className="row"><div className="col-md-6"><div className="panel"><h5>All-Time Category Pie Chart</h5>{cat.length?<Pie data={pieData} options={pieOptions}/>:<p className="text-muted mb-0">No category data yet.</p>}</div></div><div className="col-md-6"><div className="panel"><h5>Monthly Bar Chart</h5>{monthly.length?<Bar data={barData} options={options}/>:<p className="text-muted mb-0">No monthly data yet.</p>}</div></div></div></>
}
