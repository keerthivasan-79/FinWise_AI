import axios from "axios";
const api = axios.create({ baseURL: "/api", withCredentials: true });
export function setAuth(){ delete api.defaults.headers.common.Authorization; }
localStorage.removeItem("token");
localStorage.removeItem("refreshToken");
api.interceptors.response.use(response=>response,async error=>{
 const original=error.config;
 const publicAuthRoute=["/login","/refresh","/password/forgot","/password/reset","/register"].some(path=>String(original?.url||"").includes(path));
 if(error.response?.status===401&&!original?._retried&&!publicAuthRoute){
  original._retried=true;
  try{
   await axios.post("/api/refresh",{}, {withCredentials:true});
   return api(original);
  }catch{
   return Promise.reject(error);
  }
 }
 return Promise.reject(error);
});
export default api;
