import React,{useState}from"react";
import api from"../services/api";
import{Notice}from"../components/Notice";

export default function Reports(){
 const[filters,setFilters]=useState({start:"",end:"",category:""}),[schedule,setSchedule]=useState({email:"",frequency:"Monthly",format:"pdf"});
 const[message,setMessage]=useState(null);
 const download=async format=>{
  const params=new URLSearchParams(Object.entries(filters).filter(([,v])=>v));
  try{
   const response=await api.get(`/reports/export/${format}?${params}`,{responseType:"blob"});
   const url=URL.createObjectURL(response.data),link=document.createElement("a");
   link.href=url;link.download=`finwise-report.${format}`;link.click();URL.revokeObjectURL(url);
   setMessage({type:"success",text:`${format.toUpperCase()} report generated.`});
  }catch{setMessage({type:"danger",text:"Could not generate report"})}
 };
 const saveSchedule=async e=>{e.preventDefault();try{const{data}=await api.post("/scheduled-reports",schedule);setMessage({type:"info",text:data.message})}catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not save schedule"})}};
 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Reports</h2><p className="text-muted mb-0">Custom financial, archive and tax-ready exports.</p></div></div>
 <Notice message={message} onClose={()=>setMessage(null)}/>
 <div className="panel"><h5 className="fw-bold">Custom report</h5><div className="row g-3 mt-1"><div className="col-md-3"><label className="form-label">From</label><input type="date" className="form-control" value={filters.start} onChange={e=>setFilters({...filters,start:e.target.value})}/></div><div className="col-md-3"><label className="form-label">To</label><input type="date" className="form-control" value={filters.end} onChange={e=>setFilters({...filters,end:e.target.value})}/></div><div className="col-md-3"><label className="form-label">Category</label><input className="form-control" placeholder="All categories" value={filters.category} onChange={e=>setFilters({...filters,category:e.target.value})}/></div><div className="col-md-3 d-flex align-items-end gap-2">{["csv","xlsx","pdf"].map(x=><button key={x} className="btn btn-primary text-uppercase" onClick={()=>download(x)}>{x}</button>)}</div></div></div>
 <div className="panel mt-3"><h5 className="fw-bold">Report Reminder</h5><form className="row g-3 mt-1" onSubmit={saveSchedule}><div className="col-md-4"><input type="email" required className="form-control" placeholder="Email address" value={schedule.email} onChange={e=>setSchedule({...schedule,email:e.target.value})}/></div><div className="col-md-3"><select className="form-select" value={schedule.frequency} onChange={e=>setSchedule({...schedule,frequency:e.target.value})}><option>Weekly</option><option>Monthly</option></select></div><div className="col-md-3"><select className="form-select text-uppercase" value={schedule.format} onChange={e=>setSchedule({...schedule,format:e.target.value})}><option value="pdf">PDF</option><option value="xlsx">Excel</option><option value="csv">CSV</option></select></div><div className="col-md-2"><button className="btn btn-outline-primary w-100">Save Reminder</button></div></form><small className="text-muted">Offline mode saves the reminder only. Email sending needs SMTP/provider setup.</small></div></>
}
