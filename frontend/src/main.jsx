import React,{useEffect,useState}from"react";
import{createRoot}from"react-dom/client";
import"bootstrap/dist/css/bootstrap.min.css";
import"bootstrap-icons/font/bootstrap-icons.css";
import"./styles/app.css";
import api from"./services/api";
import Login from"./pages/Login";
import Register from"./pages/Register";
import Dashboard from"./pages/Dashboard";

function App(){
 const[authenticated,setAuthenticated]=useState(null);
 const[page,setPage]=useState("login");
 useEffect(()=>{api.get("/profile").then(()=>setAuthenticated(true)).catch(()=>setAuthenticated(false))},[]);
 if(authenticated===null)return <div className="auth-bg"><div className="auth-card shadow text-center"><h4>Loading FinWise...</h4></div></div>;
 if(!authenticated&&page==="register")return <Register setPage={setPage}/>;
 if(!authenticated)return <Login setToken={()=>setAuthenticated(true)} setPage={setPage}/>;
 return <Dashboard setToken={setAuthenticated}/>;
}

createRoot(document.getElementById("root")).render(<App/>);
