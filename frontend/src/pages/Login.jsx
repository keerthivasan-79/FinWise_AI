import React,{useState}from"react";
import api from"../services/api";
import{Notice}from"../components/Notice";

export default function Login({setToken,setPage}){
 const[form,setForm]=useState({email:"",password:""});
 const[reset,setReset]=useState({open:false,email:"",token:"",password:"",confirm:"",ready:false});
 const[message,setMessage]=useState(null);
 const[loading,setLoading]=useState(false);

 const submit=async e=>{
  e.preventDefault();setLoading(true);setMessage(null);
  try{
   await api.post("/login",form);
   setToken(true);
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Login failed"})}
  finally{setLoading(false)}
 };

 const requestReset=async e=>{
  e.preventDefault();setLoading(true);setMessage(null);
  try{
   const{data}=await api.post("/password/forgot",{email:reset.email||form.email});
   setReset(r=>({...r,token:data.resetToken||"",ready:Boolean(data.resetToken)}));
   setMessage({type:data.resetToken?"info":"warning",text:data.resetToken?"Local dev reset token received. Enter a new password below.":data.message||"Reset instructions created."});
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not request reset"})}
  finally{setLoading(false)}
 };

 const finishReset=async e=>{
  e.preventDefault();
  if(reset.password.length<8)return setMessage({type:"warning",text:"Password must contain at least 8 characters"});
  if(reset.password!==reset.confirm)return setMessage({type:"warning",text:"Passwords do not match"});
  setLoading(true);setMessage(null);
  try{
   await api.post("/password/reset",{token:reset.token,password:reset.password});
   setForm({email:reset.email,password:reset.password});
   setReset({open:false,email:"",token:"",password:"",confirm:"",ready:false});
   setMessage({type:"success",text:"Password reset successful. You can log in with the new password."});
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not reset password"})}
  finally{setLoading(false)}
 };

 return <div className="auth-bg"><div className="auth-card shadow"><h2 className="fw-bold text-center">FinWise AI</h2><p className="text-center text-muted">Login to continue</p><Notice message={message} onClose={()=>setMessage(null)}/><form onSubmit={submit}><input className="form-control mb-3" type="email" required placeholder="Email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/><input className="form-control mb-3" type="password" required placeholder="Password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/><button className="btn btn-primary w-100" disabled={loading}>{loading?"Please wait...":"Login"}</button></form><button className="btn btn-link w-100 mt-3" onClick={()=>setPage("register")}>Create new account</button><button className="btn btn-outline-secondary w-100" disabled={loading} onClick={()=>setReset(r=>({...r,open:!r.open,email:r.email||form.email}))}>Forgot Password</button>{reset.open&&<div className="mt-3 border-top pt-3">{!reset.ready?<form onSubmit={requestReset}><label className="form-label">Registered email</label><input className="form-control mb-2" type="email" required value={reset.email} onChange={e=>setReset({...reset,email:e.target.value})}/><button className="btn btn-outline-primary w-100" disabled={loading}>Request Reset Instructions</button><small className="text-muted d-block mt-2">Offline mode does not show reset tokens unless local developer mode enables it.</small></form>:<form onSubmit={finishReset}><label className="form-label">Reset token</label><input className="form-control mb-2" required value={reset.token} onChange={e=>setReset({...reset,token:e.target.value})}/><input className="form-control mb-2" type="password" minLength="8" required placeholder="New password" value={reset.password} onChange={e=>setReset({...reset,password:e.target.value})}/><input className="form-control mb-2" type="password" minLength="8" required placeholder="Confirm password" value={reset.confirm} onChange={e=>setReset({...reset,confirm:e.target.value})}/><button className="btn btn-success w-100" disabled={loading}>Reset Password</button></form>}</div>}</div></div>;
}
