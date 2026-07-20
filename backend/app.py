from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import csv, os, io, hashlib, re, secrets, math
import pdfplumber
from openpyxl import load_workbook
import xlrd
from datetime import date, timedelta, datetime
from db import query, get_conn
from auth import hash_password, verify_password, create_token, create_refresh_token, decode_token, token_required
from config import MAX_UPLOAD_MB, COOKIE_SECURE, ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS
from enhancements import enhancements, create_transaction, process_due_recurring
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))
app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path=''); CORS(app)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024
app.register_blueprint(enhancements)

def set_auth_cookies(response, access_token=None, refresh_token=None):
    cookie_args={'httponly':True,'secure':COOKIE_SECURE,'samesite':'Lax','path':'/'}
    if access_token:
        response.set_cookie('access_token',access_token,max_age=ACCESS_TOKEN_MINUTES*60,**cookie_args)
    if refresh_token:
        response.set_cookie('refresh_token',refresh_token,max_age=REFRESH_TOKEN_DAYS*24*60*60,**cookie_args)
    return response

def clear_auth_cookies(response):
    response.delete_cookie('access_token',path='/')
    response.delete_cookie('refresh_token',path='/')
    return response

def clean_text(value, max_length=255):
    return re.sub(r'[\x00-\x1f]', '', str(value or '')).strip()[:max_length]

def valid_email(value):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value or ""))

@app.get('/')
def home():
    index = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.exists(index): return send_from_directory(FRONTEND_DIST, 'index.html')
    return {'message':'FinWise API running; build the frontend with npm run build'}, 503
@app.post('/api/register')
def register():
    d=request.get_json(silent=True) or {}; name=clean_text(d.get('name'),100); email=clean_text(d.get('email'),120).lower(); pwd=d.get('password','')
    if not name or not valid_email(email) or len(pwd)<8: return jsonify({'error':'Enter a valid name, email and password of at least 8 characters'}),400
    if query('SELECT id FROM users WHERE email=%s',(email,),fetch=True,one=True): return jsonify({'error':'Email already registered'}),400
    query('INSERT INTO users(name,email,password) VALUES(%s,%s,%s)',(name,email,hash_password(pwd)))
    user=query('SELECT id FROM users WHERE email=%s',(email,),fetch=True,one=True)
    token=secrets.token_urlsafe(32); digest=hashlib.sha256(token.encode()).hexdigest()
    query('INSERT INTO email_verification_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,%s)',
          (user['id'],digest,datetime.now()+timedelta(days=1)))
    response={'message':'Registration successful. Verify your email when an email provider is connected.'}
    if app.debug or os.getenv('SHOW_VERIFICATION_TOKEN','false').lower()=='true':
        response['verificationToken']=token
        response['devOnly']=True
    return jsonify(response)
@app.post('/api/login')
def login():
    d=request.get_json(silent=True) or {}; email=clean_text(d.get('email'),120).lower()
    user=query('SELECT id,name,email,password,failed_login_count,locked_until FROM users WHERE email=%s',(email,),fetch=True,one=True)
    if user and user.get('locked_until') and user['locked_until']>datetime.now():
        return jsonify({'error':'Account temporarily locked. Try again later.'}),429
    if not user or not verify_password(user.get('password'),d.get('password','')):
        if user:
            attempts=int(user.get('failed_login_count') or 0)+1
            locked=datetime.now()+timedelta(minutes=15) if attempts>=5 else None
            query('UPDATE users SET failed_login_count=%s,locked_until=%s WHERE id=%s',(attempts,locked,user['id']))
        return jsonify({'error':'Invalid email or password'}),401
    if not user['password'].startswith(('scrypt:','pbkdf2:')):
        query('UPDATE users SET password=%s WHERE id=%s',(hash_password(d.get('password','')),user['id']))
    query('UPDATE users SET failed_login_count=0,locked_until=NULL WHERE id=%s',(user['id'],))
    public={k:user[k] for k in ('id','name','email')}
    response=jsonify({'message':'Login successful','user':public})
    return set_auth_cookies(response,create_token(public),create_refresh_token(public))

@app.post('/api/refresh')
def refresh_access():
    try:
        body=request.get_json(silent=True) or {}
        refresh_token=body.get('refreshToken') or request.cookies.get('refresh_token','')
        data=decode_token(refresh_token,"refresh")
        user=query('SELECT id,name,email FROM users WHERE id=%s',(data['id'],),fetch=True,one=True)
        if not user: raise ValueError()
        response=jsonify({'message':'Token refreshed'})
        return set_auth_cookies(response,create_token(user))
    except Exception:
        return jsonify({'error':'Invalid refresh token'}),401

@app.post('/api/logout')
def logout():
    return clear_auth_cookies(jsonify({'message':'Logged out'}))

@app.post('/api/password/forgot')
def forgot_password():
    email=clean_text((request.get_json(silent=True) or {}).get('email'),120).lower()
    user=query('SELECT id FROM users WHERE email=%s',(email,),fetch=True,one=True)
    if not user: return jsonify({'message':'If the account exists, reset instructions were created'})
    token=secrets.token_urlsafe(32); digest=hashlib.sha256(token.encode()).hexdigest()
    query('INSERT INTO password_reset_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,%s)',
          (user['id'],digest,datetime.now()+timedelta(minutes=30)))
    response={'message':'If email delivery is configured, reset instructions will be sent. Offline demo mode does not expose reset tokens by default.',
              'emailProviderConfigured':False}
    if app.debug or os.getenv('SHOW_RESET_TOKEN','false').lower()=='true':
        response['resetToken']=token
        response['devOnly']=True
    return jsonify(response)

@app.post('/api/email/verify')
def verify_email():
    token=(request.get_json(silent=True) or {}).get('token','')
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=query('SELECT * FROM email_verification_tokens WHERE token_hash=%s AND used=0 AND expires_at>NOW()',(digest,),fetch=True,one=True)
    if not row: return jsonify({'error':'Verification link is invalid or expired'}),400
    query('UPDATE users SET email_verified=1 WHERE id=%s',(row['user_id'],))
    query('UPDATE email_verification_tokens SET used=1 WHERE id=%s',(row['id'],))
    return jsonify({'message':'Email verified'})

@app.post('/api/password/reset')
def reset_password():
    d=request.get_json(silent=True) or {}; pwd=d.get('password','')
    if len(pwd)<8: return jsonify({'error':'Password must contain at least 8 characters'}),400
    digest=hashlib.sha256(d.get('token','').encode()).hexdigest()
    row=query('SELECT * FROM password_reset_tokens WHERE token_hash=%s AND used=0 AND expires_at>NOW()',(digest,),fetch=True,one=True)
    if not row: return jsonify({'error':'Reset link is invalid or expired'}),400
    query('UPDATE users SET password=%s,failed_login_count=0,locked_until=NULL WHERE id=%s',(hash_password(pwd),row['user_id']))
    query('UPDATE password_reset_tokens SET used=1 WHERE id=%s',(row['id'],))
    return jsonify({'message':'Password updated'})

@app.get('/api/profile')
@token_required
def get_profile(user):
    row=query('SELECT id,name,email,email_verified FROM users WHERE id=%s',(user['id'],),fetch=True,one=True)
    if not row: return jsonify({'error':'User not found'}),404
    row['passwordStatus']='Protected'
    return jsonify(row)

@app.put('/api/profile')
@token_required
def update_profile(user):
    d=request.get_json(silent=True) or {}
    name=clean_text(d.get('name'),100); email=clean_text(d.get('email'),120).lower()
    if not name or not valid_email(email): return jsonify({'error':'Enter a valid name and email'}),400
    duplicate=query('SELECT id FROM users WHERE email=%s AND id<>%s',(email,user['id']),fetch=True,one=True)
    if duplicate: return jsonify({'error':'Email already registered'}),409
    current=query('SELECT email,email_verified FROM users WHERE id=%s',(user['id'],),fetch=True,one=True)
    if not current: return jsonify({'error':'User not found'}),404
    email_changed=email!=current['email']
    query('UPDATE users SET name=%s,email=%s,email_verified=%s WHERE id=%s',
          (name,email,0 if email_changed else current.get('email_verified',0),user['id']))
    updated=query('SELECT id,name,email,email_verified FROM users WHERE id=%s',(user['id'],),fetch=True,one=True)
    return jsonify({'message':'Profile updated','user':updated})

@app.put('/api/profile/password')
@token_required
def change_profile_password(user):
    d=request.get_json(silent=True) or {}
    current_password=d.get('current_password',''); new_password=d.get('new_password','')
    if len(new_password)<8: return jsonify({'error':'New password must contain at least 8 characters'}),400
    row=query('SELECT password FROM users WHERE id=%s',(user['id'],),fetch=True,one=True)
    if not row or not verify_password(row.get('password'),current_password):
        return jsonify({'error':'Current password is incorrect'}),400
    query('UPDATE users SET password=%s,failed_login_count=0,locked_until=NULL WHERE id=%s',(hash_password(new_password),user['id']))
    return jsonify({'message':'Password changed'})
@app.get('/api/dashboard')
@token_required
def dashboard(user):
    uid=user['id']
    try: process_due_recurring(uid)
    except Exception: pass
    balance=query('SELECT IFNULL(SUM(current_balance),0) total FROM accounts WHERE user_id=%s',(uid,),fetch=True,one=True)['total']
    goal_savings=query("""SELECT IFNULL(SUM(saved_amount),0) total FROM savings_goals
        WHERE user_id=%s OR household_id IN
        (SELECT household_id FROM household_members WHERE user_id=%s AND status='Active')""",(uid,uid),fetch=True,one=True)['total']
    income=query("SELECT IFNULL(SUM(amount),0) total FROM transactions WHERE user_id=%s AND type='Income'",(uid,),fetch=True,one=True)['total']
    expense=query("SELECT IFNULL(SUM(amount),0) total FROM transactions WHERE user_id=%s AND type='Expense'",(uid,),fetch=True,one=True)['total']
    month_totals=query("""SELECT
        IFNULL(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0) income,
        IFNULL(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) expense
        FROM transactions WHERE user_id=%s AND DATE_FORMAT(transaction_date,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m')""",(uid,),fetch=True,one=True)
    top=query("SELECT category,SUM(amount) total FROM transactions WHERE user_id=%s AND type='Expense' GROUP BY category ORDER BY total DESC LIMIT 1",(uid,),fetch=True,one=True)
    recent=query('''SELECT t.*,a.account_name,ta.account_name transfer_to_account_name
        FROM transactions t JOIN accounts a ON a.id=t.account_id
        LEFT JOIN accounts ta ON ta.id=t.transfer_to_account AND ta.user_id=t.user_id
        WHERE t.user_id=%s ORDER BY t.transaction_date DESC,t.id DESC LIMIT 8''',(uid,),fetch=True)
    score=50 if float(balance or 0)>0 else 20
    if float(income or 0)>0: score=int(40+max(0,min(1,(float(income)-float(expense))/float(income)))*50)
    budget_alerts=query("SELECT b.category,b.budget_amount,IFNULL(SUM(t.amount),0) spent FROM budgets b LEFT JOIN transactions t ON t.user_id=b.user_id AND t.type='Expense' AND t.category=b.category AND DATE_FORMAT(t.transaction_date,'%Y-%m')=b.month_year WHERE b.user_id=%s AND b.month_year=DATE_FORMAT(CURDATE(),'%Y-%m') GROUP BY b.id HAVING spent>=b.budget_amount*0.8 ORDER BY spent/b.budget_amount DESC",(uid,),fetch=True)
    return jsonify({'balance':float(balance),'goalSavings':float(goal_savings or 0),
                    'totalTrackedMoney':float(balance or 0)+float(goal_savings or 0),
                    'income':float(income),'expense':float(expense),
                    'monthIncome':float(month_totals['income'] or 0),
                    'monthExpense':float(month_totals['expense'] or 0),
                    'topCategory':top,'healthScore':score,'recent':recent,'budgetAlerts':budget_alerts})
@app.get('/api/accounts')
@token_required
def accounts(user): return jsonify(query('SELECT * FROM accounts WHERE user_id=%s ORDER BY id DESC',(user['id'],),fetch=True))
@app.post('/api/accounts')
@token_required
def add_account(user):
    d=request.get_json(silent=True) or {}; op=float(d.get('opening_balance') or 0); name=clean_text(d.get('account_name'),100)
    if not name: return jsonify({'error':'Account name is required'}),400
    query("""INSERT INTO accounts(user_id,account_name,account_type,account_subtype,bank_name,last4,
        opening_balance,current_balance,credit_limit,interest_rate,institution_value)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (user['id'],name,d.get('account_type'),d.get('account_subtype'),clean_text(d.get('bank_name'),100),
         clean_text(d.get('last4'),4) or None,op,op,float(d.get('credit_limit') or 0),
         float(d.get('interest_rate') or 0),float(d.get('institution_value') or 0)))
    return jsonify({'message':'Account added'})
@app.put('/api/accounts/<int:account_id>')
@token_required
def update_account(user,account_id):
    d=request.json
    existing=query('SELECT id FROM accounts WHERE id=%s AND user_id=%s',(account_id,user['id']),fetch=True,one=True)
    if not existing: return jsonify({'error':'Account not found'}),404
    name=(d.get('account_name') or '').strip()
    if not name: return jsonify({'error':'Account name is required'}),400
    query("""UPDATE accounts SET account_name=%s,account_type=%s,account_subtype=%s,bank_name=%s,last4=%s,
        credit_limit=%s,interest_rate=%s,institution_value=%s WHERE id=%s AND user_id=%s""",
        (name,d.get('account_type'),d.get('account_subtype'),d.get('bank_name'),d.get('last4') or None,
         float(d.get('credit_limit') or 0),float(d.get('interest_rate') or 0),float(d.get('institution_value') or 0),
         account_id,user['id']))
    return jsonify({'message':'Account updated'})

@app.delete('/api/accounts/<int:account_id>')
@token_required
def delete_account(user,account_id):
    existing=query('SELECT id FROM accounts WHERE id=%s AND user_id=%s',(account_id,user['id']),fetch=True,one=True)
    if not existing: return jsonify({'error':'Account not found'}),404
    used=query('SELECT COUNT(*) count FROM transactions WHERE user_id=%s AND (account_id=%s OR transfer_to_account=%s)',(user['id'],account_id,account_id),fetch=True,one=True)['count']
    if used: return jsonify({'error':'This account has transaction history and cannot be deleted. Delete its transactions first.'}),409
    query('DELETE FROM accounts WHERE id=%s AND user_id=%s',(account_id,user['id']))
    return jsonify({'message':'Account deleted'})

@app.get('/api/transactions')
@token_required
def transactions(user):
    s=request.args.get('search',''); where=['t.user_id=%s']; params=[user['id']]
    if s:
        like=f'%{s}%'; where.append('(t.category LIKE %s OR t.description LIKE %s OR t.type LIKE %s OR a.account_name LIKE %s OR ta.account_name LIKE %s OR t.tags LIKE %s)')
        params.extend([like,like,like,like,like,like])
    if request.args.get('type'): where.append('t.type=%s'); params.append(request.args['type'])
    if request.args.get('category'): where.append('t.category=%s'); params.append(request.args['category'])
    if request.args.get('start'): where.append('t.transaction_date>=%s'); params.append(request.args['start'])
    if request.args.get('end'): where.append('t.transaction_date<=%s'); params.append(request.args['end'])
    base=f"""FROM transactions t JOIN accounts a ON a.id=t.account_id
             LEFT JOIN accounts ta ON ta.id=t.transfer_to_account AND ta.user_id=t.user_id
             WHERE {' AND '.join(where)}"""
    if request.args.get('page'):
        page=max(1,int(request.args.get('page',1))); size=min(100,max(10,int(request.args.get('pageSize',25))))
        total=query(f'SELECT COUNT(*) total {base}',tuple(params),fetch=True,one=True)['total']
        rows=query(f'SELECT t.*,a.account_name,ta.account_name transfer_to_account_name {base} ORDER BY t.transaction_date DESC,t.id DESC LIMIT %s OFFSET %s',
                   tuple(params+[size,(page-1)*size]),fetch=True)
        return jsonify({'items':rows,'page':page,'pageSize':size,'total':total,'pages':max(1,(total+size-1)//size)})
    rows=query(f'SELECT t.*,a.account_name,ta.account_name transfer_to_account_name {base} ORDER BY t.transaction_date DESC,t.id DESC',tuple(params),fetch=True)
    return jsonify(rows)

def iso_day(value):
    if hasattr(value,'isoformat'): return value.isoformat()[:10]
    return str(value or '')[:10]

def add_ledger_entry(entries, account, day, source, source_id, title, reference, debit=0, credit=0):
    amount_out=float(debit or 0); amount_in=float(credit or 0)
    entries.append({
        'account_id':account['id'],
        'account_name':account['account_name'],
        'account_type':account.get('account_type'),
        'date':iso_day(day),
        'source':source,
        'source_id':source_id,
        'particulars':title,
        'reference':reference,
        'debit':amount_out,
        'credit':amount_in,
        'effect':amount_in-amount_out
    })

@app.get('/api/ledger')
@token_required
def ledger(user):
    uid=user['id']
    account_filter=request.args.get('account_id') or ''
    start=clean_text(request.args.get('start'),10)
    end=clean_text(request.args.get('end'),10)
    accounts=query('SELECT id,account_name,account_type,opening_balance,current_balance FROM accounts WHERE user_id=%s ORDER BY account_name',(uid,),fetch=True)
    account_map={int(a['id']):a for a in accounts}
    if account_filter:
        try: selected_id=int(account_filter)
        except ValueError: return jsonify({'error':'Choose a valid account'}),400
        if selected_id not in account_map: return jsonify({'error':'Account not found'}),404
        visible_accounts={selected_id}
    else:
        visible_accounts=set(account_map.keys())
    params=[uid]
    date_filter=''
    if end:
        date_filter=' AND t.transaction_date<=%s'
        params.append(end)
    transactions=query(f"""SELECT t.*,a.account_name,ta.account_name transfer_to_account_name
        FROM transactions t JOIN accounts a ON a.id=t.account_id
        LEFT JOIN accounts ta ON ta.id=t.transfer_to_account AND ta.user_id=t.user_id
        WHERE t.user_id=%s{date_filter}
        ORDER BY t.transaction_date,t.id""",tuple(params),fetch=True)
    entries=[]
    for tx in transactions:
        amount=float(tx['amount'] or 0); day=tx['transaction_date']
        source=account_map.get(int(tx['account_id']))
        target=account_map.get(int(tx['transfer_to_account'])) if tx.get('transfer_to_account') else None
        if tx['type']=='Income' and source and source['id'] in visible_accounts:
            add_ledger_entry(entries,source,day,'Transaction',tx['id'],tx.get('description') or tx.get('category') or 'Income','Income',credit=amount)
        elif tx['type']=='Expense' and source and source['id'] in visible_accounts:
            add_ledger_entry(entries,source,day,'Transaction',tx['id'],tx.get('description') or tx.get('category') or 'Expense','Expense',debit=amount)
        elif tx['type']=='Transfer':
            if source and source['id'] in visible_accounts:
                title=tx.get('description') or f"Transfer to {tx.get('transfer_to_account_name') or 'account'}"
                add_ledger_entry(entries,source,day,'Transaction',tx['id'],title,'Transfer out',debit=amount)
            if target and target['id'] in visible_accounts:
                title=tx.get('description') or f"Transfer from {tx.get('account_name') or 'account'}"
                add_ledger_entry(entries,target,day,'Transaction',tx['id'],title,'Transfer in',credit=amount)
    goal_params=[uid]
    goal_filter=''
    if end:
        goal_filter=' AND DATE(c.created_at)<=%s'
        goal_params.append(end)
    goal_moves=query(f"""SELECT c.*,g.goal_name,a.account_name,a.account_type
        FROM goal_contributions c
        JOIN savings_goals g ON g.id=c.goal_id
        JOIN accounts a ON a.id=c.account_id
        WHERE c.user_id=%s{goal_filter}
        ORDER BY c.created_at,c.id""",tuple(goal_params),fetch=True)
    for item in goal_moves:
        account=account_map.get(int(item['account_id']))
        if not account or account['id'] not in visible_accounts: continue
        amount=float(item['amount'] or 0)
        if item['action']=='Deposit':
            add_ledger_entry(entries,account,item['created_at'],'Goal',item['id'],f"Saved to goal: {item['goal_name']}",'Goal deposit',debit=amount)
        else:
            add_ledger_entry(entries,account,item['created_at'],'Goal',item['id'],f"Returned from goal: {item['goal_name']}",'Goal withdrawal',credit=amount)
    entries.sort(key=lambda x:(x['account_name'].lower(),x['date'],x['source'],int(x['source_id'] or 0),x['reference']))
    running={aid:float(account_map[aid]['opening_balance'] or 0) for aid in visible_accounts}
    output=[]; period_opening=None
    for entry in entries:
        aid=int(entry['account_id'])
        if start and entry['date']>=start and period_opening is None:
            period_opening=sum(running.get(aid,float(account_map[aid]['opening_balance'] or 0)) for aid in visible_accounts)
        running[aid]=round(running.get(aid,0)+float(entry['effect']),2)
        row={k:v for k,v in entry.items() if k!='effect'}
        row['running_balance']=running[aid]
        if start and row['date']<start: continue
        output.append(row)
    output.sort(key=lambda x:(x['date'],x['account_name'].lower(),x['source'],int(x['source_id'] or 0),x['reference']),reverse=True)
    summary_rows=output
    opening_total=period_opening if period_opening is not None else sum(float(account_map[aid]['opening_balance'] or 0) for aid in visible_accounts)
    closing_total=sum(running.get(aid,float(account_map[aid]['opening_balance'] or 0)) for aid in visible_accounts)
    return jsonify({
        'rows':output,
        'summary':{
            'openingBalance':opening_total,
            'debitTotal':sum(float(x['debit'] or 0) for x in summary_rows),
            'creditTotal':sum(float(x['credit'] or 0) for x in summary_rows),
            'closingBalance':closing_total,
            'accountCount':len(visible_accounts)
        },
        'algorithm':'Running balance = opening balance + credits - debits. Transfers create one debit row and one credit row.'
    })

def cleanup_empty_statement_import(cur, uid, import_id):
    if not import_id: return
    cur.execute('SELECT COUNT(*) count FROM transactions WHERE statement_import_id=%s AND user_id=%s',(import_id,uid))
    remaining=cur.fetchone()
    if int((remaining or {}).get('count') or 0)==0:
        cur.execute('DELETE FROM statement_imports WHERE id=%s AND user_id=%s',(import_id,uid))

@app.post('/api/transactions')
@token_required
def add_transaction(user):
    d=request.get_json(silent=True) or {}; conn=get_conn(); cur=conn.cursor(dictionary=True)
    try:
        tid=create_transaction(cur,user['id'],d)
        conn.commit()
        if d.get('make_recurring'):
            query("""INSERT INTO recurring_transactions
                (user_id,account_id,type,category,amount,description,payment_method,transfer_to_account,frequency,next_run)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (user['id'],d.get('account_id'),d.get('type'),d.get('category'),d.get('amount'),d.get('description'),
                 d.get('payment_method'),d.get('transfer_to_account') or None,d.get('frequency','Monthly'),
                 d.get('next_run') or date.today()+timedelta(days=30)))
        return jsonify({'message':'Transaction saved','id':tid})
    except ValueError as e:
        conn.rollback(); return jsonify({'error':str(e)}),400
    except Exception:
        conn.rollback(); return jsonify({'error':'Could not save transaction'}),500
    finally:
        cur.close(); conn.close()
@app.delete('/api/transactions/<int:tid>')
@token_required
def delete_transaction(user,tid):
    uid=user['id']
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    try:
        cur.execute('SELECT * FROM transactions WHERE id=%s AND user_id=%s FOR UPDATE',(tid,uid)); tx=cur.fetchone()
        if not tx: return jsonify({'error':'Transaction not found'}),404
        amount=float(tx['amount'])
        if tx['type']=='Income': cur.execute('UPDATE accounts SET current_balance=current_balance-%s WHERE id=%s AND user_id=%s',(amount,tx['account_id'],uid))
        elif tx['type']=='Expense': cur.execute('UPDATE accounts SET current_balance=current_balance+%s WHERE id=%s AND user_id=%s',(amount,tx['account_id'],uid))
        elif tx['type']=='Transfer':
            cur.execute('UPDATE accounts SET current_balance=current_balance+%s WHERE id=%s AND user_id=%s',(amount,tx['account_id'],uid))
            cur.execute('UPDATE accounts SET current_balance=current_balance-%s WHERE id=%s AND user_id=%s',(amount,tx['transfer_to_account'],uid))
        import_id=tx.get('statement_import_id')
        cur.execute('DELETE FROM transactions WHERE id=%s AND user_id=%s',(tid,uid))
        cleanup_empty_statement_import(cur,uid,import_id)
        conn.commit()
        return jsonify({'message':'Deleted and account balances restored'})
    except Exception:
        conn.rollback(); return jsonify({'error':'Could not delete transaction'}),500
    finally:
        cur.close(); conn.close()
@app.get('/api/budgets')
@token_required
def budgets(user): return jsonify(query("SELECT b.*,IFNULL((SELECT SUM(amount) FROM transactions t WHERE t.user_id=b.user_id AND t.type='Expense' AND t.category=b.category AND DATE_FORMAT(t.transaction_date,'%Y-%m')=b.month_year),0) spent FROM budgets b WHERE b.user_id=%s ORDER BY b.month_year DESC",(user['id'],),fetch=True))
@app.post('/api/budgets')
@token_required
def add_budget(user):
    d=request.json; category=d.get('category'); month=d.get('month_year'); amount=float(d.get('budget_amount') or 0)
    if amount<=0: return jsonify({'error':'Enter a valid budget amount'}),400
    if query('SELECT id FROM budgets WHERE user_id=%s AND category=%s AND month_year=%s',(user['id'],category,month),fetch=True,one=True): return jsonify({'error':'A budget already exists for this category and month'}),409
    query('INSERT INTO budgets(user_id,category,month_year,budget_amount) VALUES(%s,%s,%s,%s)',(user['id'],category,month,amount)); return jsonify({'message':'Budget added'})

@app.put('/api/budgets/<int:budget_id>')
@token_required
def update_budget(user,budget_id):
    d=request.json; amount=float(d.get('budget_amount') or 0)
    if amount<=0: return jsonify({'error':'Enter a valid budget amount'}),400
    duplicate=query('SELECT id FROM budgets WHERE user_id=%s AND category=%s AND month_year=%s AND id<>%s',(user['id'],d.get('category'),d.get('month_year'),budget_id),fetch=True,one=True)
    if duplicate: return jsonify({'error':'A budget already exists for this category and month'}),409
    query('UPDATE budgets SET category=%s,month_year=%s,budget_amount=%s WHERE id=%s AND user_id=%s',(d.get('category'),d.get('month_year'),amount,budget_id,user['id']))
    return jsonify({'message':'Budget updated'})

@app.delete('/api/budgets/<int:budget_id>')
@token_required
def delete_budget(user,budget_id):
    query('DELETE FROM budgets WHERE id=%s AND user_id=%s',(budget_id,user['id'])); return jsonify({'message':'Budget deleted'})
@app.get('/api/goals')
@token_required
def goals(user): return jsonify(query("""SELECT g.*,CASE WHEN g.household_id IS NULL THEN 0 ELSE 1 END shared
    FROM savings_goals g WHERE g.user_id=%s OR g.household_id IN
    (SELECT household_id FROM household_members WHERE user_id=%s AND status='Active') ORDER BY g.id DESC""",
    (user['id'],user['id']),fetch=True))
@app.post('/api/goals')
@token_required
def add_goal(user):
    d=request.get_json(silent=True) or {}; household_id=None
    name=clean_text(d.get('goal_name'),100)
    try: target=float(d.get('target_amount') or 0)
    except (TypeError,ValueError): target=0
    if not name or target<=0: return jsonify({'error':'Goal name and a valid target are required'}),400
    if d.get('shared'):
        membership=query("SELECT household_id FROM household_members WHERE user_id=%s AND status='Active' LIMIT 1",(user['id'],),fetch=True,one=True)
        if not membership: return jsonify({'error':'Create or join a household before sharing a goal'}),400
        household_id=membership['household_id']
    query('INSERT INTO savings_goals(user_id,goal_name,target_amount,saved_amount,deadline,household_id) VALUES(%s,%s,%s,%s,%s,%s)',
          (user['id'],name,target,0,d.get('deadline') or None,household_id))
    return jsonify({'message':'Goal added'})
@app.put('/api/goals/<int:goal_id>')
@token_required
def update_goal(user,goal_id):
    d=request.json; name=(d.get('goal_name') or '').strip(); target=float(d.get('target_amount') or 0)
    goal=query('SELECT * FROM savings_goals WHERE id=%s AND user_id=%s',(goal_id,user['id']),fetch=True,one=True)
    if not goal: return jsonify({'error':'Goal not found'}),404
    if not name or target<=0: return jsonify({'error':'Goal name and a valid target are required'}),400
    if target<float(goal['saved_amount']): return jsonify({'error':'Target cannot be lower than the amount already saved'}),400
    query('UPDATE savings_goals SET goal_name=%s,target_amount=%s,deadline=%s WHERE id=%s AND user_id=%s',(name,target,d.get('deadline') or None,goal_id,user['id']))
    return jsonify({'message':'Goal updated'})

@app.delete('/api/goals/<int:goal_id>')
@token_required
def delete_goal(user,goal_id):
    goal=query('SELECT * FROM savings_goals WHERE id=%s AND user_id=%s',(goal_id,user['id']),fetch=True,one=True)
    if not goal: return jsonify({'error':'Goal not found'}),404
    if float(goal['saved_amount'])>0: return jsonify({'error':'Withdraw the saved amount before deleting this goal'}),409
    query('DELETE FROM savings_goals WHERE id=%s AND user_id=%s',(goal_id,user['id']))
    return jsonify({'message':'Goal deleted'})

@app.post('/api/goals/<int:goal_id>/contributions')
@token_required
def goal_contribution(user,goal_id):
    d=request.json; action=d.get('action'); amount=float(d.get('amount') or 0); account_id=d.get('account_id')
    if action not in ('Deposit','Withdraw') or amount<=0 or not account_id: return jsonify({'error':'Account, action and valid amount are required'}),400
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    try:
        cur.execute("""SELECT g.* FROM savings_goals g WHERE g.id=%s AND
            (g.user_id=%s OR g.household_id IN (SELECT household_id FROM household_members
            WHERE user_id=%s AND status='Active')) FOR UPDATE""",(goal_id,user['id'],user['id'])); goal=cur.fetchone()
        cur.execute('SELECT * FROM accounts WHERE id=%s AND user_id=%s FOR UPDATE',(account_id,user['id'])); account=cur.fetchone()
        if not goal or not account: raise ValueError('Goal or account not found')
        saved=float(goal['saved_amount']); balance=float(account['current_balance'])
        if action=='Deposit':
            if amount>balance: raise ValueError('Insufficient account balance')
            if saved+amount>float(goal['target_amount']): raise ValueError('Deposit exceeds the remaining goal amount')
            new_saved=saved+amount; new_balance=balance-amount
        else:
            if amount>saved: raise ValueError('Withdrawal exceeds the saved amount')
            new_saved=saved-amount; new_balance=balance+amount
        cur.execute('UPDATE savings_goals SET saved_amount=%s WHERE id=%s',(new_saved,goal_id))
        cur.execute('UPDATE accounts SET current_balance=%s WHERE id=%s',(new_balance,account_id))
        cur.execute('INSERT INTO goal_contributions(user_id,goal_id,account_id,action,amount) VALUES(%s,%s,%s,%s,%s)',(user['id'],goal_id,account_id,action,amount))
        conn.commit(); return jsonify({'message':f'{action} successful','saved_amount':new_saved})
    except ValueError as e:
        conn.rollback(); return jsonify({'error':str(e)}),400
    except Exception:
        conn.rollback(); return jsonify({'error':'Could not update goal'}),500
    finally:
        cur.close(); conn.close()

@app.get('/api/goals/<int:goal_id>/contributions')
@token_required
def goal_contributions(user,goal_id):
    return jsonify(query('SELECT c.*,a.account_name FROM goal_contributions c JOIN accounts a ON a.id=c.account_id WHERE c.goal_id=%s AND c.user_id=%s ORDER BY c.created_at DESC,c.id DESC',(goal_id,user['id']),fetch=True))

@app.get('/api/savings/activity')
@token_required
def savings_activity(user):
    where=['c.user_id=%s']; params=[user['id']]
    if request.args.get('start'): where.append('DATE(c.created_at)>=%s'); params.append(request.args['start'])
    if request.args.get('end'): where.append('DATE(c.created_at)<=%s'); params.append(request.args['end'])
    return jsonify(query(f"""SELECT c.*,g.goal_name,a.account_name
        FROM goal_contributions c
        JOIN savings_goals g ON g.id=c.goal_id
        JOIN accounts a ON a.id=c.account_id
        WHERE {' AND '.join(where)}
        ORDER BY c.created_at DESC,c.id DESC""",tuple(params),fetch=True))

@app.get('/api/analytics/category')
@token_required
def category(user): return jsonify(query("SELECT category,SUM(amount) total FROM transactions WHERE user_id=%s AND type='Expense' GROUP BY category ORDER BY total DESC",(user['id'],),fetch=True))
@app.get('/api/analytics/monthly')
@token_required
def monthly(user): return jsonify(query("SELECT DATE_FORMAT(transaction_date,'%Y-%m') month,SUM(amount) total FROM transactions WHERE user_id=%s AND type='Expense' GROUP BY month ORDER BY month",(user['id'],),fetch=True))
@app.get('/api/reports/csv')
@token_required
def report(user):
    rows=query('SELECT t.id,a.account_name,t.type,t.category,t.amount,t.description,t.transaction_date,t.payment_method FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.user_id=%s ORDER BY t.transaction_date DESC',(user['id'],),fetch=True)
    os.makedirs('reports',exist_ok=True); path=f"reports/report_{user['id']}.csv"
    with open(path,'w',newline='',encoding='utf-8') as f:
        if rows:
            wr=csv.DictWriter(f,fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
        else: f.write('No data')
    return send_file(path,as_attachment=True)

SMART_CATEGORIES={
 'Food':['swiggy','zomato','restaurant','cafe','food'],
 'Travel':['uber','ola','metro','bus','train','flight'],
 'Shopping':['amazon','flipkart','myntra','shopping'],
 'Medical':['apollo','pharmacy','hospital','medicine'],
 'Entertainment':['netflix','spotify','cinema','movie'],
 'Bills':['electricity','broadband','recharge','bill','airtel','jio','vodafone','sms chgs'],
 'Groceries':['grocery','groceries','supermarket','dmart','bigbasket'],
 'Education':['college','school','course','udemy'],
 'Insurance':['insurance','premium'],
 'Fuel':['petrol','diesel','fuel'],
 'Salary':['salary','payroll']
}

def ai_tokens(text):
    return re.findall(r'[a-z0-9]+', (text or '').lower())

def naive_bayes_category(uid, description):
    tokens=ai_tokens(description)
    if not tokens: return {'category':'Other','confidence':40,'matched':False,'algorithm':'Multinomial Naive Bayes','reason':'No clear words found'}
    training=[]
    for category,words in SMART_CATEGORIES.items():
        for word in words:
            training.append((category,word))
    history=query("""SELECT category,description,merchant FROM transactions
        WHERE user_id=%s AND type IN ('Income','Expense') AND category IS NOT NULL
        AND category<>'' AND category<>'Transfer'
        ORDER BY transaction_date DESC,id DESC LIMIT 500""",(uid,),fetch=True)
    for row in history:
        text=' '.join([str(row.get('description') or ''),str(row.get('merchant') or '')]).strip()
        if text: training.append((row['category'],text))
    if not training: return {'category':'Other','confidence':40,'matched':False,'algorithm':'Multinomial Naive Bayes','reason':'No training examples available'}

    categories=sorted(set(category for category,_ in training))
    doc_counts={category:0 for category in categories}
    word_counts={category:{} for category in categories}
    total_words={category:0 for category in categories}
    vocab=set()
    for category,text in training:
        doc_counts[category]+=1
        for token in ai_tokens(text):
            vocab.add(token)
            word_counts[category][token]=word_counts[category].get(token,0)+1
            total_words[category]+=1
    vocab_size=max(1,len(vocab)); total_docs=sum(doc_counts.values())
    scores={}
    for category in categories:
        score=math.log((doc_counts[category]+1)/(total_docs+len(categories)))
        denom=total_words[category]+vocab_size
        for token in tokens:
            score+=math.log((word_counts[category].get(token,0)+1)/denom)
        scores[category]=score
    best=max(scores,key=scores.get)
    max_score=scores[best]
    probabilities={category:math.exp(score-max_score) for category,score in scores.items()}
    total_probability=sum(probabilities.values()) or 1
    confidence=round(probabilities[best]/total_probability*100)
    matched_words=[token for token in tokens if token in vocab][:4]
    if not matched_words or confidence<45:
        return {'category':'Other','confidence':max(35,confidence),'matched':False,'algorithm':'Multinomial Naive Bayes','reason':'No strong category pattern found'}
    return {'category':best,'confidence':confidence,'matched':True,'algorithm':'Multinomial Naive Bayes','reason':'Matched words: '+', '.join(matched_words)}

@app.post('/api/ai/categorize')
@token_required
def categorize(user):
    text=(request.json or {}).get('description','')
    return jsonify(naive_bayes_category(user['id'],text))

@app.get('/api/ai/insights')
@token_required
def ai_insights(user):
    uid=user['id']
    totals=query("SELECT IFNULL(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0) income,IFNULL(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) expense FROM transactions WHERE user_id=%s AND DATE_FORMAT(transaction_date,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m')",(uid,),fetch=True,one=True)
    categories=query("SELECT category,SUM(amount) total FROM transactions WHERE user_id=%s AND type='Expense' AND DATE_FORMAT(transaction_date,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m') GROUP BY category ORDER BY total DESC",(uid,),fetch=True)
    unusual=query("SELECT t.*,a.account_name FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.user_id=%s AND t.type='Expense' AND t.amount>(SELECT IFNULL(AVG(amount)*2.5,999999999) FROM transactions WHERE user_id=%s AND type='Expense') ORDER BY t.amount DESC LIMIT 5",(uid,uid),fetch=True)
    income=float(totals['income']); expense=float(totals['expense']); savings=income-expense; rate=(savings/income*100) if income else 0
    score=max(0,min(100,round(50+rate*.45-(15 if expense>income else 0))))
    suggestions=[]
    if not income and not expense: suggestions.append('Add transactions to generate personalised financial guidance.')
    if income: suggestions.append(f'You saved {rate:.0f}% of your income this month.')
    if categories: suggestions.append(f"{categories[0]['category']} is your highest category at ₹{float(categories[0]['total']):,.0f}.")
    if expense>income: suggestions.append('Your spending exceeds income. Pause non-essential purchases this week.')
    elif savings>0: suggestions.append(f'You can direct up to ₹{savings*.5:,.0f} toward a savings goal while keeping a buffer.')
    return jsonify({'score':score,'rating':'Excellent' if score>=80 else 'Good' if score>=60 else 'Needs Attention','income':income,'expense':expense,'savings':savings,'categories':categories,'unusual':unusual,'suggestions':suggestions})

def money_text(value):
    return f"Rs {float(value or 0):,.0f}"

def percent_text(value):
    return f"{float(value or 0):.0f}%"

FINWISE_HELP_TOPICS=[
    {
        'keys':['offline','online','internet','without internet','cloud','api key','paid api','chatgpt'],
        'lines':[
            'FinWise is designed to run offline on your computer after setup. The finance assistant does not need internet, a paid API, or a cloud LLM.',
            'It answers using local rules, your saved accounts, budgets, goals and transactions, plus a built-in FinWise help guide. Internet is only needed for installing packages or adding a real email/bank provider later.'
        ],
        'chips':['What algorithm is used?','What can you answer?','How do I run FinWise?']
    },
    {
        'keys':['all questions','what can you answer','chat used for','assistant used for','finance assistant','ai chat','chatbot'],
        'lines':[
            'I can answer FinWise and personal finance questions offline: total money, income, expenses, savings, budgets, goals, ledger, bank statement import, transfers, analytics, profile, automation, reports and project explanation.',
            'For unknown live-world facts, I will not guess because offline mode has no internet. For your project, that is a good point: the AI is explainable and local.'
        ],
        'chips':['Is this offline?','Explain total money','What algorithm is used?']
    },
    {
        'keys':['algorithm','algorithms','naive bayes','ai algorithm','machine learning','ml','rule based','rules'],
        'lines':[
            'The project uses Multinomial Naive Bayes for transaction category prediction. It learns from finance keywords and your saved transaction descriptions.',
            'The chat uses rule-based intent matching plus live finance summaries from your database. The health score uses simple scoring rules based on income, expenses, savings, budgets and cash balance.'
        ],
        'chips':['Is this offline?','How categories work?','Explain health score']
    },
    {
        'keys':['transfer','transfer money','transfer between','one bank','another bank','own account','bank to bank'],
        'lines':[
            'For moving money between your own accounts, go to Transactions, choose Transfer Money, select the source account, select the destination account, enter the amount, and save.',
            'A transfer is not income or expense. It reduces one account and increases the other account, so your total money stays the same.'
        ],
        'chips':['Show my accounts','Explain total money','Recent transactions']
    },
    {
        'keys':['goal money','goal savings','savings goal','saved amount','add money in goal','goal expense','goal income'],
        'lines':[
            'Money added to a goal is treated as savings, not normal expense or income. It moves money from an account into saved goal money.',
            'This avoids confusion in tracking: expenses mean money spent, income means money received, and savings goals mean money kept aside for a target.'
        ],
        'chips':['How much can I save?','Explain total money','Which goal should I fund?']
    },
    {
        'keys':['total money','income expense saving','income expense savings','dashboard numbers','net worth','recorded networth','recorded net worth'],
        'lines':[
            'Total Money means cash/bank balance plus saved goal money. Income is money received this month. Expense is money spent this month. Savings is money kept aside in goals.',
            'I avoid the confusing recorded net worth wording here. For this project, the simple summary is Total Money, Income, Expense and Savings.'
        ],
        'chips':['Show my accounts','How is my cash flow?','How much can I save?']
    },
    {
        'keys':['import','bank statement','csv','excel','xlsx','pdf','duplicate','already imported','upi wallet'],
        'lines':[
            'To import a statement, go to Transactions, choose an account, pick CSV, Excel, or a text-based PDF, preview the rows, correct categories if needed, then import.',
            'FinWise now checks duplicate rows using account, date, amount, type and description, so the same bank statement should not keep importing again.'
        ],
        'chips':['How categories work?','Recent transactions','Check duplicates']
    },
    {
        'keys':['analytics month','last month','this month','previous month','next month','month button','monthly'],
        'lines':[
            'In Analytics, use the month picker plus Previous and Next buttons to compare this month and last month.',
            'The monthly view loads transactions and goal activity for the selected month, so you can check income, expenses and savings period by period.'
        ],
        'chips':['Where am I spending most?','Check my budgets','How is my cash flow?']
    },
    {
        'keys':['ledger','debit','credit','running balance','account statement','book keeping','bookkeeping'],
        'lines':[
            'The Ledger page shows every account movement in debit and credit format with a running balance.',
            'The algorithm is: running balance = opening balance + credits - debits. Transfers create two ledger rows, one debit from the source account and one credit to the destination account.'
        ],
        'chips':['Explain total money','How do I transfer between banks?','What algorithm is used?']
    },
    {
        'keys':['profile','email id','emailid','change password','current password','show password','forgot password','login password'],
        'lines':[
            'Profile shows your name, email and password status. You can change name, email and password there.',
            'FinWise cannot show the current password because saved passwords are encrypted. If you forget it, use Forgot Password in local developer mode or reset it directly in the database for demo setup.'
        ],
        'chips':['Is this offline?','How do I run FinWise?','What can you answer?']
    },
    {
        'keys':['dark mode','light mode','system mode','theme','letters not visible','text not visible'],
        'lines':[
            'Theme is in Profile. You can choose Light, Dark or System.',
            'Dark mode uses separate colors for panels, inputs, tables and muted text so letters stay readable.'
        ],
        'chips':['Open profile help','What can you answer?','How do I run FinWise?']
    },
    {
        'keys':['automation','auto entry','recurring','salary every month','rent every month'],
        'lines':[
            'Automation is for recurring entries like monthly salary, rent, EMI, subscriptions or bills. You create the rule once, then run due entries when needed.',
            'It is local automation inside FinWise, not an online bank connection.'
        ],
        'chips':['Check my budgets','Recent transactions','What should I do next?']
    },
    {
        'keys':['finance hub','future hub','financial hub','hub confusing','what is hub'],
        'lines':[
            'Smart Tools groups simple planning features: summary checks, duplicate checks, possible subscriptions and recurring auto entries.',
            'For daily use, focus on Dashboard, Transactions, Accounts, Analytics and Profile first. Use Smart Tools when you need recurring entries or planning checks.'
        ],
        'chips':['What is automation?','Check my budgets','What should I do next?']
    },
    {
        'keys':['run','start app','vs code','page failed','failed to load','not loading','port','localhost','127.0.0.1'],
        'lines':[
            'To run FinWise in VS Code, open the folder C:\\FinWise_AI, open the terminal, run .\\run.cmd, and keep that terminal open.',
            'Then open http://127.0.0.1:5000. If the page fails to load, the backend is not running yet or Python dependencies need repair.'
        ],
        'chips':['Is this offline?','What can you answer?','How do I start?']
    },
    {
        'keys':['report','reports','scheduled report','email report','export'],
        'lines':[
            'Reports can export your finance data as local files. Scheduled reports are saved as local reminders in offline mode.',
            'Automatic email sending needs SMTP or another email provider, so offline FinWise does not send emails by itself.'
        ],
        'chips':['Is this offline?','What is automation?','Export help']
    }
]

def topic_score(question, keywords):
    q=question.lower()
    tokens=set(re.findall(r'[a-z0-9]+',q))
    score=0
    for keyword in keywords:
        key=keyword.lower()
        if ' ' in key:
            if key in q: score+=4+len(key.split())
        elif key in tokens:
            score+=2
    return score

def project_help_answer(question):
    best=None; best_score=0
    for topic in FINWISE_HELP_TOPICS:
        score=topic_score(question,topic['keys'])
        if score>best_score:
            best=topic; best_score=score
    if best and best_score>=2:
        return best['lines'], best.get('chips') or ['What can you answer?','Is this offline?','What should I do next?']
    return None, None

def finance_snapshot(uid):
    current_month = date.today().strftime('%Y-%m')
    totals=query("""SELECT
        IFNULL(SUM(CASE WHEN type='Income' THEN amount ELSE 0 END),0) income,
        IFNULL(SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END),0) expense
        FROM transactions WHERE user_id=%s AND DATE_FORMAT(transaction_date,'%Y-%m')=%s""",
        (uid,current_month),fetch=True,one=True)
    balance=query('SELECT IFNULL(SUM(current_balance),0) total FROM accounts WHERE user_id=%s',(uid,),fetch=True,one=True)['total']
    goal_savings=query("""SELECT IFNULL(SUM(saved_amount),0) total FROM savings_goals
        WHERE user_id=%s OR household_id IN
        (SELECT household_id FROM household_members WHERE user_id=%s AND status='Active')""",(uid,uid),fetch=True,one=True)['total']
    accounts=query("""SELECT account_name,account_type,account_subtype,current_balance,institution_value
        FROM accounts WHERE user_id=%s ORDER BY current_balance DESC LIMIT 8""",(uid,),fetch=True)
    categories=query("""SELECT category,SUM(amount) total FROM transactions
        WHERE user_id=%s AND type='Expense' AND DATE_FORMAT(transaction_date,'%Y-%m')=%s
        GROUP BY category ORDER BY total DESC LIMIT 5""",(uid,current_month),fetch=True)
    budgets=query("""SELECT b.category,b.budget_amount,IFNULL(SUM(t.amount),0) spent
        FROM budgets b LEFT JOIN transactions t ON t.user_id=b.user_id AND t.type='Expense'
        AND t.category=b.category AND DATE_FORMAT(t.transaction_date,'%Y-%m')=b.month_year
        WHERE b.user_id=%s AND b.month_year=%s GROUP BY b.id ORDER BY spent/b.budget_amount DESC""",
        (uid,current_month),fetch=True)
    goals=query("""SELECT goal_name,target_amount,saved_amount,deadline FROM savings_goals
        WHERE user_id=%s ORDER BY
        CASE WHEN target_amount>0 THEN saved_amount/target_amount ELSE 0 END DESC LIMIT 5""",
        (uid,),fetch=True)
    recent=query("""SELECT t.type,t.category,t.amount,t.description,t.transaction_date,a.account_name
        FROM transactions t JOIN accounts a ON a.id=t.account_id
        WHERE t.user_id=%s ORDER BY t.transaction_date DESC,t.id DESC LIMIT 5""",(uid,),fetch=True)
    unusual=query("""SELECT t.category,t.amount,t.description,t.transaction_date,a.account_name
        FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.user_id=%s AND t.type='Expense'
        AND t.amount>(SELECT IFNULL(AVG(amount)*2.5,999999999) FROM transactions WHERE user_id=%s AND type='Expense')
        ORDER BY t.amount DESC LIMIT 3""",(uid,uid),fetch=True)
    income=float(totals['income'] or 0); expense=float(totals['expense'] or 0); savings=income-expense
    rate=(savings/income*100) if income else 0
    return {'month':current_month,'balance':float(balance or 0),'goal_savings':float(goal_savings or 0),
            'total_tracked_money':float(balance or 0)+float(goal_savings or 0),'income':income,'expense':expense,
            'savings':savings,'savings_rate':rate,'accounts':accounts,'categories':categories,
            'budgets':budgets,'goals':goals,'recent':recent,'unusual':unusual}

def assistant_lines(snapshot, question):
    q=question.lower()
    lines=[]
    chips=['How can I save more this month?','Where am I spending most?','Check my budgets','What should I do next?']
    help_lines, help_chips=project_help_answer(question)
    if help_lines:
        return help_lines, help_chips
    has_data=snapshot['income'] or snapshot['expense'] or snapshot['accounts']
    if not has_data:
        return [
            'Start by adding at least one account, then record income and expenses. After that I can explain spending patterns, budget risk, savings rate and goal progress.',
            'Good first steps: add a bank or cash account, add salary/income, then add your top 5 regular expenses.'
        ], ['How do I start?','What account should I add first?']

    if any(x in q for x in ['budget','limit','overspend','over spend']):
        if not snapshot['budgets']:
            lines.append('No budget is set for this month yet. Create budgets for your top expense categories first.')
            if snapshot['categories']:
                top=snapshot['categories'][0]
                lines.append(f"Start with {top['category']} because it is currently your largest category at {money_text(top['total'])}.")
        else:
            risky=[]
            for b in snapshot['budgets']:
                spent=float(b['spent'] or 0); limit=float(b['budget_amount'] or 0)
                ratio=(spent/limit*100) if limit else 0
                if ratio>=80: risky.append(f"{b['category']} is at {percent_text(ratio)} ({money_text(spent)} of {money_text(limit)}).")
            lines.append('Budget check: ' + (' '.join(risky) if risky else 'all tracked budgets are below 80% usage.'))
            lines.append('Best move: reduce flexible categories first before changing fixed expenses.')
        chips=['Which budget is risky?','Where am I spending most?','How much can I save?']
    elif any(x in q for x in ['save','saving','savings','goal','invest']):
        lines.append(f"This month you have income of {money_text(snapshot['income'])}, expenses of {money_text(snapshot['expense'])}, and available savings of {money_text(snapshot['savings'])}.")
        if snapshot['income']:
            lines.append(f"Your savings rate is {percent_text(snapshot['savings_rate'])}.")
        if snapshot['savings']>0:
            lines.append(f"A cautious target is to move up to {money_text(snapshot['savings']*.5)} into a goal while keeping cash available.")
        elif snapshot['income']:
            lines.append('You are not saving this month yet. Cut one non-essential category before adding new goals.')
        if snapshot['goals']:
            g=snapshot['goals'][0]; target=float(g['target_amount'] or 0); saved=float(g['saved_amount'] or 0)
            progress=(saved/target*100) if target else 0
            lines.append(f"Closest goal: {g['goal_name']} is {percent_text(progress)} funded.")
        chips=['Which goal should I fund?','Where can I cut expenses?','Check my budgets']
    elif any(x in q for x in ['spend','expense','category','where','cut','reduce']):
        if snapshot['categories']:
            top=', '.join([f"{c['category']} {money_text(c['total'])}" for c in snapshot['categories'][:3]])
            lines.append(f"Your top spending categories this month are: {top}.")
            lines.append(f"Start with {snapshot['categories'][0]['category']} because it has the biggest impact.")
        else:
            lines.append('I do not see expense transactions for this month yet.')
        if snapshot['unusual']:
            u=snapshot['unusual'][0]
            lines.append(f"One large item to review: {u['description'] or u['category']} for {money_text(u['amount'])} from {u['account_name']}.")
        chips=['What can I reduce?','Check unusual spending','Make a budget plan']
    elif any(x in q for x in ['balance','account','cash','bank','wallet']):
        lines.append(f"Your cash balance is {money_text(snapshot['balance'])}. Goal savings are {money_text(snapshot['goal_savings'])}. Total tracked money is {money_text(snapshot['total_tracked_money'])}.")
        if snapshot['accounts']:
            account_text=', '.join([f"{a['account_name']} {money_text(a['current_balance'])}" for a in snapshot['accounts'][:4]])
            lines.append(f"Top accounts: {account_text}.")
        chips=['Can I afford this expense?','How much can I save?','Show recent transactions']
    elif any(x in q for x in ['income','salary','earn']):
        lines.append(f"Income recorded this month is {money_text(snapshot['income'])}.")
        lines.append(f"After expenses of {money_text(snapshot['expense'])}, your net monthly flow is {money_text(snapshot['savings'])}.")
        chips=['How much should I save?','Where is income going?','Check budgets']
    elif any(x in q for x in ['transaction','recent','latest']):
        if snapshot['recent']:
            recent='; '.join([f"{r['transaction_date']} {r['type']} {money_text(r['amount'])} in {r['category']}" for r in snapshot['recent'][:4]])
            lines.append(f"Recent transactions: {recent}.")
        else:
            lines.append('No recent transactions are available yet.')
        chips=['Where am I spending most?','Check unusual spending','How is my cash flow?']
    elif any(x in q for x in ['afford','emergency','buffer','safe to spend']):
        buffer=max(snapshot['expense'],snapshot['income']*.2)
        spendable=max(0,snapshot['balance']-buffer)
        lines.append(f"Cash available is {money_text(snapshot['balance'])}. I would keep about {money_text(buffer)} as a buffer before optional spending.")
        lines.append(f"Estimated optional spendable amount: {money_text(spendable)}. This is a simple local estimate, not financial advice.")
        chips=['How much can I save?','Where can I cut expenses?','Check my budgets']
    else:
        lines.append(f"Here is the quick picture: cash {money_text(snapshot['balance'])}, goal savings {money_text(snapshot['goal_savings'])}, total tracked money {money_text(snapshot['total_tracked_money'])}.")
        lines.append(f"This month: income {money_text(snapshot['income'])}, expenses {money_text(snapshot['expense'])}, net flow {money_text(snapshot['savings'])}.")
        if snapshot['categories']:
            lines.append(f"Biggest spending area this month: {snapshot['categories'][0]['category']} at {money_text(snapshot['categories'][0]['total'])}.")
        if snapshot['savings']>0:
            lines.append('Next step: move part of the surplus to a savings goal and keep the rest as a buffer.')
        else:
            lines.append('Next step: set a small budget cut in your largest flexible category.')
        lines.append('You can also ask project questions like: is this offline, how to transfer between accounts, what algorithm is used, how import works, or how auto entries work.')
    return lines, chips

@app.post('/api/ai/chat')
@token_required
def ai_chat(user):
    d=request.get_json(silent=True) or {}
    question=clean_text(d.get('message'),500)
    if len(question)<2: return jsonify({'error':'Ask a finance question first'}),400
    snapshot=finance_snapshot(user['id'])
    lines,chips=assistant_lines(snapshot,question)
    return jsonify({'reply':'\n'.join(lines),'chips':chips,'month':snapshot['month'],
                    'summary':{'balance':snapshot['balance'],'goalSavings':snapshot['goal_savings'],
                               'totalTrackedMoney':snapshot['total_tracked_money'],'income':snapshot['income'],
                               'expense':snapshot['expense'],'savings':snapshot['savings'],
                               'savingsRate':snapshot['savings_rate']}})


def parse_statement_file(uploaded):
    ext=os.path.splitext(uploaded.filename or '')[1].lower()
    if ext not in ('.csv','.xlsx','.xls','.pdf'): raise ValueError('Supported formats: CSV, XLSX, XLS and text-based PDF')
    content=uploaded.read(); digest=hashlib.sha256(content).hexdigest()
    try:
        if ext=='.csv': raw=pd.read_csv(io.BytesIO(content),header=None)
        elif ext in ('.xlsx','.xls'): raw=pd.read_excel(io.BytesIO(content),header=None)
        else:
            table_rows=[]
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    for table in page.extract_tables() or []:
                        if table: table_rows.extend(table)
            if not table_rows: raise ValueError('No table found. Scanned-image PDFs need OCR; use Excel/CSV for this statement.')
            raw=pd.DataFrame(table_rows)
        header_index=None
        for idx,row in raw.head(40).iterrows():
            cells=' | '.join(str(v).strip().lower() for v in row.tolist() if not pd.isna(v))
            if ('date' in cells) and any(x in cells for x in ('debit','withdrawal','credit','deposit','amount')): header_index=idx; break
        if header_index is None: raise ValueError('Transaction header row was not found')
        headers=[('' if pd.isna(v) else str(v).strip()) or 'column '+str(i+1) for i,v in enumerate(raw.loc[header_index].tolist())]
        frame=raw.loc[header_index+1:].copy(); frame.columns=headers; frame=frame.dropna(how='all')
    except ValueError: raise
    except Exception: raise ValueError('Could not read this statement. For PDF, use a text-based statement rather than a scanned image.')
    frame.columns=[str(c).strip().lower().replace('_',' ').replace('\n',' ') for c in frame.columns]
    def column(*names):
        for name in names:
            for actual in frame.columns:
                if name==actual or name in actual: return actual
        return None
    date_col=column('transaction date','txn date','value date','date'); desc_col=column('narration','description','remarks','particulars','details')
    debit_col=column('withdrawal amount','debit amount','withdrawal','debit'); credit_col=column('deposit amount','credit amount','deposit','credit')
    amount_col=column('transaction amount','amount'); type_col=column('transaction type','dr/cr','cr/dr','type')
    if not date_col or (not debit_col and not credit_col and not amount_col): raise ValueError('Required Date and Debit/Credit or Amount columns were not found')
    def number(value):
        if pd.isna(value): return 0.0
        try: return abs(float(str(value).replace(',','').replace('₹','').strip()))
        except: return 0.0
    parsed=[]
    for _,row in frame.iterrows():
        try:
            value=row[date_col]
            tx_date=(pd.to_datetime(value,unit='D',origin='1899-12-30') if isinstance(value,(int,float)) and not pd.isna(value) else pd.to_datetime(value,dayfirst=True)).date()
        except: continue
        description='' if not desc_col or pd.isna(row[desc_col]) else str(row[desc_col]).strip()
        debit=number(row[debit_col]) if debit_col else 0; credit=number(row[credit_col]) if credit_col else 0
        if not debit and not credit and amount_col:
            amount=number(row[amount_col]); marker=str(row[type_col]).lower() if type_col and not pd.isna(row[type_col]) else ''; raw_amount=str(row[amount_col]).strip()
            if any(x in marker for x in ('cr','credit','deposit')): credit=amount
            elif any(x in marker for x in ('dr','debit','withdraw')): debit=amount
            elif raw_amount.startswith('-'): debit=amount
            else: credit=amount
        amount=credit or debit
        if amount<=0: continue
        typ='Income' if credit else 'Expense'; category='Other'; text=description.lower()
        for cat,words in SMART_CATEGORIES.items():
            if any(word in text for word in words): category=cat; break
        parsed.append({'selected':True,'transaction_date':tx_date.isoformat(),'description':description,'type':typ,'category':category,'amount':amount})
    if not parsed: raise ValueError('No valid transaction rows were found')
    return digest,uploaded.filename,parsed

def blank_cell(value):
    return value is None or str(value).strip()==''

def normalize_column(value, fallback):
    text=str(value or '').strip().lower().replace('_',' ').replace('\n',' ')
    return re.sub(r'\s+',' ',text) or fallback

def read_statement_rows(ext, content):
    if ext=='.csv':
        for encoding in ('utf-8-sig','utf-8','cp1252'):
            try:
                text=content.decode(encoding)
                return [row for row in csv.reader(io.StringIO(text))]
            except UnicodeDecodeError:
                continue
        raise ValueError('Could not read this CSV encoding.')
    if ext=='.xlsx':
        workbook=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        sheet=workbook.active
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    if ext=='.xls':
        workbook=xlrd.open_workbook(file_contents=content)
        sheet=workbook.sheet_by_index(0)
        rows=[]
        for r in range(sheet.nrows):
            row=[]
            for c in range(sheet.ncols):
                cell=sheet.cell(r,c)
                if cell.ctype==xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate.xldate_as_datetime(cell.value,workbook.datemode).date())
                else:
                    row.append(cell.value)
            rows.append(row)
        return rows
    table_rows=[]
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if table: table_rows.extend(table)
    if not table_rows: raise ValueError('No table found. Scanned-image PDFs need OCR; use Excel/CSV for this statement.')
    return table_rows

def parse_statement_date(value):
    if isinstance(value,datetime): return value.date()
    if isinstance(value,date): return value
    if isinstance(value,(int,float)) and value>1000:
        return (datetime(1899,12,30)+timedelta(days=float(value))).date()
    text=str(value or '').strip()
    if not text: raise ValueError('Missing date')
    text=re.sub(r'\s+',' ',text)
    for candidate in (text,text.split(' ')[0]):
        for fmt in ('%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%d.%m.%Y','%d %b %Y','%d-%b-%Y','%d/%b/%Y','%m/%d/%Y'):
            try: return datetime.strptime(candidate,fmt).date()
            except ValueError: pass
    raise ValueError('Invalid date')

def statement_number(value):
    if blank_cell(value): return 0.0
    text=str(value).strip()
    cleaned=re.sub(r'[^\d.\-()]','',text.replace(',',''))
    if not cleaned: return 0.0
    cleaned=cleaned.strip('()')
    try: return abs(float(cleaned.replace('-','')))
    except ValueError: return 0.0

def parse_statement_file(uploaded):
    ext=os.path.splitext(uploaded.filename or '')[1].lower()
    if ext not in ('.csv','.xlsx','.xls','.pdf'): raise ValueError('Supported formats: CSV, XLSX, XLS and text-based PDF')
    content=uploaded.read(); digest=hashlib.sha256(content).hexdigest()
    try:
        rows=read_statement_rows(ext,content)
        rows=[list(row or []) for row in rows if row and not all(blank_cell(v) for v in row)]
        header_index=None
        for idx,row in enumerate(rows[:40]):
            cells=' | '.join(str(v).strip().lower() for v in row if not blank_cell(v))
            if ('date' in cells) and any(x in cells for x in ('debit','withdrawal','credit','deposit','amount')): header_index=idx; break
        if header_index is None: raise ValueError('Transaction header row was not found')
        headers=[normalize_column(v,'column '+str(i+1)) for i,v in enumerate(rows[header_index])]
        data_rows=[]
        for source in rows[header_index+1:]:
            item={}
            for i,header in enumerate(headers):
                item[header]=source[i] if i<len(source) else None
            if not all(blank_cell(v) for v in item.values()): data_rows.append(item)
    except ValueError: raise
    except Exception: raise ValueError('Could not read this statement. For PDF, use a text-based statement rather than a scanned image.')
    def column(*names):
        for name in names:
            for actual in headers:
                if name==actual or name in actual: return actual
        return None
    date_col=column('transaction date','txn date','value date','date'); desc_col=column('narration','description','remarks','particulars','details')
    debit_col=column('withdrawal amount','debit amount','withdrawal','debit'); credit_col=column('deposit amount','credit amount','deposit','credit')
    amount_col=column('transaction amount','amount'); type_col=column('transaction type','dr/cr','cr/dr','type')
    if not date_col or (not debit_col and not credit_col and not amount_col): raise ValueError('Required Date and Debit/Credit or Amount columns were not found')
    parsed=[]
    for row in data_rows:
        try: tx_date=parse_statement_date(row.get(date_col))
        except ValueError: continue
        description='' if not desc_col or blank_cell(row.get(desc_col)) else str(row.get(desc_col)).strip()
        debit=statement_number(row.get(debit_col)) if debit_col else 0; credit=statement_number(row.get(credit_col)) if credit_col else 0
        if not debit and not credit and amount_col:
            amount=statement_number(row.get(amount_col)); marker=str(row.get(type_col) or '').lower() if type_col else ''; raw_amount=str(row.get(amount_col) or '').strip()
            if any(x in marker for x in ('cr','credit','deposit')): credit=amount
            elif any(x in marker for x in ('dr','debit','withdraw')): debit=amount
            elif raw_amount.startswith('-') or (raw_amount.startswith('(') and raw_amount.endswith(')')): debit=amount
            else: credit=amount
        amount=credit or debit
        if amount<=0: continue
        typ='Income' if credit else 'Expense'; category='Other'; text=description.lower()
        for cat,words in SMART_CATEGORIES.items():
            if any(word in text for word in words): category=cat; break
        parsed.append({'selected':True,'transaction_date':tx_date.isoformat(),'description':description,'type':typ,'category':category,'amount':amount})
    if not parsed: raise ValueError('No valid transaction rows were found')
    return digest,uploaded.filename,parsed

def statement_description_key(value):
    return re.sub(r'\s+',' ',str(value or '').strip().lower())[:255]

def statement_row_key(account_id, item):
    return (str(account_id), item.get('transaction_date'), item.get('type'),
            round(float(item.get('amount') or 0),2), statement_description_key(item.get('description')))

def statement_duplicate_exists(cur, uid, account_id, item):
    cur.execute("""SELECT id FROM transactions
        WHERE user_id=%s AND account_id=%s AND transaction_date=%s AND type=%s
        AND amount=%s AND LOWER(TRIM(REGEXP_REPLACE(COALESCE(description,''),'[[:space:]]+',' ')))=%s
        LIMIT 1""",
        (uid,account_id,item.get('transaction_date'),item.get('type'),float(item.get('amount') or 0),
         statement_description_key(item.get('description'))))
    return cur.fetchone() is not None

def clear_stale_statement_import(uid, file_hash):
    existing=query("""SELECT s.id,COUNT(t.id) linked_rows FROM statement_imports s
        LEFT JOIN transactions t ON t.statement_import_id=s.id
        WHERE s.user_id=%s AND s.file_hash=%s GROUP BY s.id""",(uid,file_hash),fetch=True,one=True)
    if not existing: return False
    if int(existing.get('linked_rows') or 0)>0: return True
    query('DELETE FROM statement_imports WHERE id=%s AND user_id=%s',(existing['id'],uid))
    return False

@app.post('/api/statements/preview')
@token_required
def preview_statement(user):
    uploaded=request.files.get('file')
    if not uploaded: return jsonify({'error':'Choose a statement file'}),400
    try:
        digest,name,items=parse_statement_file(uploaded)
        if clear_stale_statement_import(user['id'],digest): return jsonify({'error':'This statement was already imported'}),409
        account_id=request.form.get('account_id')
        if account_id:
            conn=get_conn(); cur=conn.cursor(dictionary=True)
            try:
                cur.execute('SELECT id FROM accounts WHERE id=%s AND user_id=%s',(account_id,user['id']))
                if not cur.fetchone(): return jsonify({'error':'Account not found'}),404
                seen=set()
                for item in items:
                    key=statement_row_key(account_id,item)
                    duplicate=key in seen or statement_duplicate_exists(cur,user['id'],account_id,item)
                    seen.add(key)
                    item['duplicate']=duplicate
                    if duplicate: item['selected']=False
            finally:
                cur.close(); conn.close()
        return jsonify({'file_hash':digest,'file_name':name,'rows':items})
    except ValueError as e: return jsonify({'error':str(e)}),400

@app.post('/api/statements/confirm')
@token_required
def confirm_statement(user):
    d=request.json or {}; account_id=d.get('account_id'); items=[x for x in d.get('rows',[]) if x.get('selected',True)]
    if not account_id or not items: return jsonify({'error':'Select an account and at least one transaction'}),400
    if clear_stale_statement_import(user['id'],d.get('file_hash')): return jsonify({'error':'This statement was already imported'}),409
    conn=get_conn(); cur=conn.cursor(dictionary=True); income=expense=imported=skipped_duplicates=0
    try:
        cur.execute('SELECT id FROM accounts WHERE id=%s AND user_id=%s FOR UPDATE',(account_id,user['id']))
        if not cur.fetchone(): raise ValueError('Account not found')
        valid_items=[]
        seen=set()
        for item in items:
            typ=item.get('type'); amount=float(item.get('amount') or 0)
            if typ not in ('Income','Expense') or amount<=0: continue
            key=statement_row_key(account_id,item)
            if key in seen or statement_duplicate_exists(cur,user['id'],account_id,item):
                skipped_duplicates+=1
                continue
            seen.add(key)
            valid_items.append((item,typ,amount))
        if not valid_items:
            raise ValueError('All selected rows already exist for this account')
        cur.execute('INSERT INTO statement_imports(user_id,account_id,file_name,file_hash,imported_rows) VALUES(%s,%s,%s,%s,%s)',(user['id'],account_id,d.get('file_name','Statement'),d.get('file_hash'),len(valid_items))); import_id=cur.lastrowid
        for item,typ,amount in valid_items:
            cur.execute('INSERT INTO transactions(user_id,account_id,type,category,amount,description,transaction_date,payment_method,statement_import_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(user['id'],account_id,typ,item.get('category','Other'),amount,item.get('description',''),item.get('transaction_date'),'Bank Statement',import_id))
            imported+=1
            if typ=='Income': income+=amount
            else: expense+=amount
        if not imported: raise ValueError('No valid transactions selected')
        cur.execute('UPDATE accounts SET current_balance=current_balance+%s-%s WHERE id=%s',(income,expense,account_id)); conn.commit()
        return jsonify({'message':'Statement imported','imported':imported,'income':income,'expense':expense,'skippedDuplicates':skipped_duplicates})
    except ValueError as e: conn.rollback(); return jsonify({'error':str(e)}),400
    except Exception: conn.rollback(); return jsonify({'error':'Import failed. Run the v8 database migration first.'}),500
    finally: cur.close(); conn.close()

@app.get('/api/statements/history')
@token_required
def statement_history(user):
    query("""DELETE s FROM statement_imports s
        LEFT JOIN transactions t ON t.statement_import_id=s.id
        WHERE s.user_id=%s AND t.id IS NULL""",(user['id'],))
    return jsonify(query("SELECT s.*,a.account_name,IFNULL(SUM(CASE WHEN t.type='Income' THEN t.amount ELSE 0 END),0) income,IFNULL(SUM(CASE WHEN t.type='Expense' THEN t.amount ELSE 0 END),0) expense,COUNT(t.id) linked_rows FROM statement_imports s JOIN accounts a ON a.id=s.account_id LEFT JOIN transactions t ON t.statement_import_id=s.id WHERE s.user_id=%s GROUP BY s.id ORDER BY s.created_at DESC",(user['id'],),fetch=True))

@app.delete('/api/statements/<int:import_id>')
@token_required
def undo_statement(user,import_id):
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    try:
        cur.execute('SELECT * FROM statement_imports WHERE id=%s AND user_id=%s FOR UPDATE',(import_id,user['id'])); record=cur.fetchone()
        if not record: raise ValueError('Import not found')
        cur.execute('SELECT id,type,amount FROM transactions WHERE statement_import_id=%s AND user_id=%s FOR UPDATE',(import_id,user['id'])); items=cur.fetchall()
        if not items:
            cur.execute('DELETE FROM statement_imports WHERE id=%s AND user_id=%s',(import_id,user['id']))
            conn.commit()
            return jsonify({'message':'Import history cleaned','removed':0})
        income=sum(float(x['amount']) for x in items if x['type']=='Income'); expense=sum(float(x['amount']) for x in items if x['type']=='Expense')
        cur.execute('UPDATE accounts SET current_balance=current_balance-%s+%s WHERE id=%s AND user_id=%s',(income,expense,record['account_id'],user['id']))
        cur.executemany('DELETE FROM transactions WHERE id=%s AND user_id=%s',[(x['id'],user['id']) for x in items])
        cur.execute('DELETE FROM statement_imports WHERE id=%s AND user_id=%s',(import_id,user['id'])); conn.commit()
        return jsonify({'message':'Import undone','removed':len(items)})
    except ValueError as e: conn.rollback(); return jsonify({'error':str(e)}),400
    except Exception: conn.rollback(); return jsonify({'error':'Could not undo import'}),500
    finally: cur.close(); conn.close()

@app.get('/<path:path>')
def frontend(path):
    requested = os.path.join(FRONTEND_DIST, path)
    if os.path.isfile(requested): return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, 'index.html')

if __name__=='__main__':
    from migrations import ensure_schema
    ensure_schema()
    app.run(debug=False)
