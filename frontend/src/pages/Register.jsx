import React,{useState}from"react";
import api from"../services/api";
import{Notice}from"../components/Notice";

export default function Register({setPage}){
 const[form,setForm]=useState({name:"",email:"",password:""});
 const[message,setMessage]=useState(null);
 const[loading,setLoading]=useState(false);
 const submit=async e=>{
  e.preventDefault();setLoading(true);setMessage(null);
  try{
   await api.post("/register",form);
   setMessage({type:"success",text:"Registration successful. You can log in now."});
   setTimeout(()=>setPage("login"),700);
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Registration failed"})}
  finally{setLoading(false)}
 };
 return <div className="auth-bg"><div className="auth-card shadow"><h2 className="fw-bold text-center">Create Account</h2><Notice message={message} onClose={()=>setMessage(null)}/><form onSubmit={submit}><input className="form-control mb-3" required placeholder="Full Name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><input className="form-control mb-3" type="email" required placeholder="Email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/><input className="form-control mb-3" type="password" required minLength="8" placeholder="Password (8+ characters)" value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/><button className="btn btn-primary w-100" disabled={loading}>{loading?"Creating...":"Register"}</button></form><button className="btn btn-link w-100 mt-3" onClick={()=>setPage("login")}>Back to Login</button></div></div>
}
