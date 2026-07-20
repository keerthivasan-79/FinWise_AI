import React,{useEffect,useState}from"react";
import api,{setAuth}from"../services/api";
import Home from"./Home";import Accounts from"./Accounts";import Transactions from"./Transactions";import Ledger from"./Ledger";import Budget from"./Budget";import Goals from"./Goals";import Analytics from"./Analytics";import Reports from"./Reports";import AIInsights from"./AIInsights";import Profile from"./Profile";
import FutureHub from"./FutureHub";
export default function Dashboard({setToken}){
 const[page,setPage]=useState("home");const[transactionType,setTransactionType]=useState("Expense");
 useEffect(()=>{setAuth();api.get("/preferences").then(({data})=>{document.documentElement.dataset.theme=data.theme||"system";document.documentElement.dataset.motion=data.reduced_motion?"reduced":"full"}).catch(()=>{})},[]);
 const logout=async()=>{try{await api.post("/logout")}finally{setToken(false)}};
 const navigate=(target,options={})=>{if(target==="transactions"&&options.type)setTransactionType(options.type);setPage(target)};
 const render=()=>({home:<Home onNavigate={navigate}/>,accounts:<Accounts/>,transactions:<Transactions initialType={transactionType}/>,ledger:<Ledger/>,budget:<Budget/>,goals:<Goals/>,analytics:<Analytics/>,reports:<Reports/>,ai:<AIInsights/>,hub:<FutureHub/>,profile:<Profile/>}[page]);
 const links=[["home","bi-speedometer2","Dashboard"],["accounts","bi-bank","Accounts"],["transactions","bi-arrow-left-right","Transactions"],["ledger","bi-journal-text","Ledger"],["budget","bi-pie-chart","Budget"],["goals","bi-bullseye","Goals"],["analytics","bi-graph-up","Analytics"],["reports","bi-file-earmark-text","Reports"],["ai","bi-chat-dots","Finance Chat"],["hub","bi-grid-1x2","Smart Tools"],["profile","bi-person-circle","Profile"]];
 return <div className="app-layout"><aside className="sidebar"><div className="brand mb-4"><i className="bi bi-stars"/> FinWise <b>AI</b><small>SMART PERSONAL FINANCE</small></div><div className="sidebar-nav">{links.map(x=><button className={page===x[0]?"active":""} key={x[0]} onClick={()=>navigate(x[0])}><i className={`bi ${x[1]}`}/>{x[2]}</button>)}</div><button className="logout" onClick={logout}><i className="bi bi-box-arrow-right"/>Logout</button></aside><main className="main-content">{render()}</main></div>
}
