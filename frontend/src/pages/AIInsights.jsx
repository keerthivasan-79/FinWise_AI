import React,{useEffect,useState}from"react";
import api from"../services/api";

const formatMoney=value=>"Rs "+Number(value||0).toLocaleString("en-IN",{maximumFractionDigits:0});
const starterPrompts=[
 "Is this fully offline?",
 "What algorithm is used?",
 "How do I transfer between banks?",
 "Explain my total money"
];

export default function AIInsights(){
 const[data,setData]=useState(null),[error,setError]=useState("");
 const[messages,setMessages]=useState([{role:"assistant",text:"Hi, I am your offline FinWise assistant. Ask me about your money, budgets, goals, ledger, bank statement imports, transfers, profile, automation, reports, or the project algorithm."}]);
 const[input,setInput]=useState(""),[chips,setChips]=useState(starterPrompts),[sending,setSending]=useState(false);
 useEffect(()=>{api.get("/ai/insights").then(r=>setData(r.data)).catch(()=>setError("Could not load insights."))},[]);
 const ask=async text=>{
  const question=(text||input).trim();if(!question||sending)return;
  setInput("");setSending(true);setMessages(current=>[...current,{role:"user",text:question}]);
  try{
   const{data:reply}=await api.post("/ai/chat",{message:question});
   setMessages(current=>[...current,{role:"assistant",text:reply.reply,summary:reply.summary}]);
   setChips(reply.chips||starterPrompts);
  }catch(err){
   setMessages(current=>[...current,{role:"assistant",text:err.response?.data?.error||"I could not answer that right now."}]);
  }finally{setSending(false)}
 };
 if(error)return <div className="alert alert-danger">{error}</div>;
 if(!data)return <div className="panel">Analysing your finances...</div>;
 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Offline FinWise Assistant</h2><p className="text-muted mb-0">Ask finance and project questions using local rules and your saved FinWise data.</p></div><span className="ai-badge"><i className="bi bi-chat-dots"/> Offline AI</span></div>
 <div className="row g-3"><div className="col-lg-4"><div className="health-orb"><small>FINANCIAL HEALTH</small><strong>{data.score}<sup>/100</sup></strong><h4>{data.rating}</h4></div></div><div className="col-lg-8"><div className="panel h-100"><h5 className="fw-bold mb-3">Personal recommendations</h5>{data.suggestions.map((x,i)=><div className="ai-tip" key={i}><i className="bi bi-lightbulb"/><span>{x}</span></div>)}</div></div></div>
 <div className="row g-3 mt-1"><div className="col-md-4"><div className="mini-stat income-stat"><span>Income this month</span><h4>{formatMoney(data.income)}</h4></div></div><div className="col-md-4"><div className="mini-stat expense-stat"><span>Expense this month</span><h4>{formatMoney(data.expense)}</h4></div></div><div className="col-md-4"><div className="mini-stat balance-stat"><span>Available savings</span><h4>{formatMoney(data.savings)}</h4></div></div></div>
 <div className="chat-layout mt-4"><div className="panel chat-panel"><div className="chat-header"><div><h5 className="fw-bold mb-1">Ask FinWise</h5><p className="text-muted mb-0">No cloud LLM or internet required. Answers come from local finance rules, Naive Bayes category prediction and built-in FinWise help.</p></div><i className="bi bi-robot"/></div><div className="chat-messages">{messages.map((m,i)=><div className={"chat-message "+m.role} key={i}><div>{m.text.split("\n").map((line,idx)=><p key={idx}>{line}</p>)}</div>{m.summary&&<div className="chat-summary"><span>Cash {formatMoney(m.summary.balance)}</span><span>Goals {formatMoney(m.summary.goalSavings)}</span><span>Tracked {formatMoney(m.summary.totalTrackedMoney||m.summary.balance)}</span></div>}</div>)}{sending&&<div className="chat-message assistant"><div><p>Checking local FinWise data...</p></div></div>}</div><div className="chat-chips">{chips.map(chip=><button key={chip} onClick={()=>ask(chip)}>{chip}</button>)}</div><form className="chat-form" onSubmit={e=>{e.preventDefault();ask()}}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask about finance, ledger, transfers, imports, profile, or algorithms"/><button disabled={sending}><i className="bi bi-send"/></button></form></div>
 <div><div className="panel"><h5 className="fw-bold"><i className="bi bi-shield-exclamation me-2"/>Unusual spending check</h5>{data.unusual.length?data.unusual.map(x=><div className="unusual" key={x.id}><span>{x.description||x.category} - {x.account_name}</span><strong>{formatMoney(x.amount)}</strong></div>):<p className="text-muted mb-0">No unusually large expenses detected.</p>}</div><div className="panel mt-3"><h5 className="fw-bold"><i className="bi bi-cpu me-2"/>Offline AI Engine</h5><p className="text-muted mb-1">Category prediction uses Multinomial Naive Bayes with finance keywords and saved transactions.</p><small className="text-muted">Chat answers use local intent rules, live database summaries and a built-in FinWise project guide.</small></div></div></div></>
}
