import React from "react";

export function Notice({message,onClose}){
 if(!message)return null;
 const type=message.type||"info";
 return <div className={`alert alert-${type} d-flex justify-content-between align-items-start gap-3`} role="status">
  <span>{message.text}</span>
  {onClose&&<button type="button" className="btn-close" aria-label="Close" onClick={onClose}/>}
 </div>;
}

export function ConfirmDialog({state,onCancel,onConfirm}){
 if(!state)return null;
 return <div className="modal-backdrop-custom">
  <div className="goal-dialog">
   <h4>{state.title||"Confirm action"}</h4>
   <p className="text-muted">{state.message}</p>
   <div className="d-flex justify-content-end gap-2 mt-4">
    <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
    <button type="button" className={`btn ${state.confirmClass||"btn-danger"}`} onClick={onConfirm}>{state.confirmText||"Confirm"}</button>
   </div>
  </div>
 </div>;
}
