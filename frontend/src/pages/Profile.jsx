import React,{useEffect,useState}from"react";
import api from"../services/api";
import{Notice}from"../components/Notice";

export default function Profile(){
 const[profile,setProfile]=useState(null),[form,setForm]=useState({name:"",email:""});
 const[password,setPassword]=useState({current_password:"",new_password:"",confirm_password:""});
 const[preferences,setPreferences]=useState({theme:"system",compact_mode:false,reduced_motion:false,dashboard_widgets:[]});
 const[message,setMessage]=useState(null);
 const[loading,setLoading]=useState(false);

 const load=async()=>{
  const[{data},prefs]=await Promise.all([api.get("/profile"),api.get("/preferences").catch(()=>({data:preferences}))]);
  setProfile(data);
  setForm({name:data.name||"",email:data.email||""});
  setPreferences({...preferences,...prefs.data});
 };
 useEffect(()=>{load().catch(err=>setMessage({type:"danger",text:err.response?.status===404?"Profile is not loaded in the running server. Restart FinWise once.":err.response?.data?.error||"Could not load profile"}))},[]);

 const saveProfile=async e=>{
  e.preventDefault();setLoading(true);setMessage(null);
  try{
   const{data}=await api.put("/profile",form);
   setProfile({...data.user,passwordStatus:"Protected"});
   setMessage({type:"success",text:"Profile updated"});
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not update profile"})}
  finally{setLoading(false)}
 };

 const saveAppearance=async e=>{
  e.preventDefault();setLoading(true);setMessage(null);
  try{
   await api.put("/preferences",preferences);
   document.documentElement.dataset.theme=preferences.theme||"system";
   document.documentElement.dataset.motion=preferences.reduced_motion?"reduced":"full";
   setMessage({type:"success",text:"Appearance updated"});
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not save appearance"})}
  finally{setLoading(false)}
 };

 const changePassword=async e=>{
  e.preventDefault();
  if(password.new_password!==password.confirm_password)return setMessage({type:"warning",text:"New passwords do not match"});
  setLoading(true);setMessage(null);
  try{
   await api.put("/profile/password",{current_password:password.current_password,new_password:password.new_password});
   setPassword({current_password:"",new_password:"",confirm_password:""});
   setMessage({type:"success",text:"Password changed"});
  }catch(err){setMessage({type:"danger",text:err.response?.data?.error||"Could not change password"})}
  finally{setLoading(false)}
 };

 if(!profile)return <><Notice message={message} onClose={()=>setMessage(null)}/><div className="panel">Loading profile...</div></>;
 return <><div className="dashboard-header"><div><h2 className="page-title mb-1">Profile</h2><p className="text-muted mb-0">Manage your account name, email and password.</p></div><span className="ai-badge"><i className="bi bi-person-circle"/> Account</span></div>
 <Notice message={message} onClose={()=>setMessage(null)}/>
 <div className="row g-3">
  <div className="col-lg-4"><div className="panel h-100"><div className="text-center"><div className="profile-avatar"><i className="bi bi-person"/></div><h4 className="fw-bold mt-3 mb-1">{profile.name}</h4><p className="text-muted mb-2">{profile.email}</p><span className={"badge "+(profile.email_verified?"bg-success":"bg-warning text-dark")}>{profile.email_verified?"Email verified":"Email not verified"}</span></div><div className="summary-row mt-4"><span>Password</span><strong>{profile.passwordStatus}</strong></div><small className="text-muted">Saved passwords are encrypted and cannot be shown.</small></div></div>
  <div className="col-lg-8"><div className="panel"><h5 className="fw-bold mb-3">Account Details</h5><form className="row g-3" onSubmit={saveProfile}><div className="col-md-6"><label className="form-label">Name</label><input className="form-control" required value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></div><div className="col-md-6"><label className="form-label">Email ID</label><input className="form-control" type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></div><div className="col-12"><button className="btn btn-primary" disabled={loading}><i className="bi bi-check-circle me-2"/>Save Profile</button></div></form></div>
  <div className="panel mt-3"><h5 className="fw-bold mb-3">Appearance</h5><form className="row g-3" onSubmit={saveAppearance}><div className="col-md-6"><label className="form-label">Mode</label><select className="form-select" value={preferences.theme} onChange={e=>setPreferences({...preferences,theme:e.target.value})}><option value="light">Light</option><option value="system">System</option><option value="dark">Dark</option></select></div><div className="col-md-6 d-flex align-items-end"><button className="btn btn-primary" disabled={loading}><i className="bi bi-palette me-2"/>Save Mode</button></div></form></div>
  <div className="panel mt-3"><h5 className="fw-bold mb-3">Change Password</h5><form className="row g-3" onSubmit={changePassword}><div className="col-md-4"><label className="form-label">Current Password</label><input className="form-control" type="password" required value={password.current_password} onChange={e=>setPassword({...password,current_password:e.target.value})}/></div><div className="col-md-4"><label className="form-label">New Password</label><input className="form-control" type="password" required minLength="8" value={password.new_password} onChange={e=>setPassword({...password,new_password:e.target.value})}/></div><div className="col-md-4"><label className="form-label">Confirm Password</label><input className="form-control" type="password" required minLength="8" value={password.confirm_password} onChange={e=>setPassword({...password,confirm_password:e.target.value})}/></div><div className="col-12"><button className="btn btn-success" disabled={loading}><i className="bi bi-shield-lock me-2"/>Change Password</button><small className="text-muted d-block mt-2">For safety, password reset links are not shown inside the app.</small></div></form></div></div>
 </div></>;
}
