import requests
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup

C_USER = os.environ.get('C_USER', '61562982451918')
XS = os.environ.get('XS', '21%3A3NfXjLQ-SfBm5w%3A2%3A1777049360%3A-1%3A-1%3A-1%3AAczACYlwKJWTa1rHb1vvZ_tBYcDh8VLx2x7WcKWXZw')
DATR = os.environ.get('DATR', 'PYG-aZLRoATtxcZgB9co323U')
FR = os.environ.get('FR', '1xuHyyvuRUiYfMEyf.AWfSCwzd7lhBRyc3-zqkpZ_WwMBh6N8td4Vqs6eXlZ0KTfHV5Iw.Bp658U..AAA.0.0.Bp658U.AWf99nurL8eQ_esbxb6JaZOt-2Q')
OWNER_IDS = os.environ.get('OWNER_IDS', '26377628695212164').split(',')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'boostlys_smm')
DB_USER_DB = os.environ.get('DB_USER', 'boostlys_smm')
DB_PASS = os.environ.get('DB_PASS', 'boostlys_smm')

def get_db():
    import mysql.connector
    return mysql.connector.connect(host=DB_HOST, database=DB_NAME, user=DB_USER_DB, password=DB_PASS)

def php_format(n): return '₱{:.2f}'.format(float(n))
def now_time(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def is_owner(uid): return str(uid) in OWNER_IDS

def get_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    for name, value in {'c_user': C_USER, 'xs': XS, 'datr': DATR, 'fr': FR}.items():
        session.cookies.set(name, value, domain='.facebook.com')
    return session

def verify_login(session):
    r = session.get('https://mbasic.facebook.com/')
    if 'login' in r.url.lower():
        print('Cookies expired!')
        return False
    print('Login OK!')
    return True

def get_inbox(session):
    try:
        r = session.get('https://mbasic.facebook.com/messages/')
        soup = BeautifulSoup(r.text, 'html.parser')
        threads = []
        seen = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if '/messages/read/' in href and 'tid=' in href:
                tid = href.split('tid=')[-1].split('&')[0]
                if tid and tid not in seen:
                    seen.append(tid)
                    url = 'https://mbasic.facebook.com' + href if href.startswith('/') else href
                    threads.append({'id': tid, 'url': url})
        return threads
    except Exception as e:
        print(f'Inbox error: {e}')
        return []

def get_messages(session, url):
    try:
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        msgs = []
        for div in soup.find_all('div', {'data-sigil': 'message'}):
            text = div.get_text(strip=True)
            if text:
                msgs.append(text)
        return msgs
    except Exception as e:
        print(f'Messages error: {e}')
        return []

def send_message(session, thread_id, text):
    try:
        url = f'https://mbasic.facebook.com/messages/read/?tid={thread_id}'
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        form = None
        for f in soup.find_all('form'):
            if f.find('textarea') or f.find('input', {'name': 'body'}):
                form = f
                break
        if not form:
            print('No form found')
            return False
        data = {}
        for inp in form.find_all(['input', 'textarea']):
            n = inp.get('name')
            if n:
                data[n] = inp.get('value', '')
        data['body'] = text
        action = form.get('action', '')
        if action.startswith('/'):
            action = 'https://mbasic.facebook.com' + action
        session.post(action, data=data)
        print(f'Sent: {text[:30]}')
        return True
    except Exception as e:
        print(f'Send error: {e}')
        return False

def handle_command(sender_id, text, thread_id, session):
    parts = text.strip().split(' ')
    cmd = parts[0].lower()
    owner = is_owner(sender_id)
    def reply(msg): send_message(session, thread_id, msg)
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        if cmd == 'test':
            reply(f'✅ Bot working!\nID: {sender_id}\nOwner: {"Yes" if owner else "No"}\nTime: {now_time()}')
        elif cmd == 'myid':
            reply(f'Your ID: {sender_id}')
        elif cmd == 'help':
            reply('💰 SMM BOT\n\nfund [user] [amount]\nfund [user] [-amount]\nbalance [user]\nadduser [user] [email] [pass]\nstatus [id]\nchange [status] [id]\nresend [id]\norders [user]\ntest\nmyid')
        elif cmd == 'balance':
            u = parts[1] if len(parts)>1 else ''
            if not u: return reply('❌ Usage: balance [username]')
            cur.execute('SELECT username,balance FROM clients WHERE username=%s',(u,))
            user = cur.fetchone()
            if not user: return reply(f'❌ User "{u}" not found.')
            reply(f'💰 BALANCE\n👤 {user["username"]}\n💵 {php_format(user["balance"])}\n🕐 {now_time()}')
        elif cmd == 'fund':
            if not owner: return reply('❌ Not authorized.')
            u = parts[1] if len(parts)>1 else ''
            amt = float(parts[2]) if len(parts)>2 else None
            if not u or amt is None: return reply('❌ Usage: fund [username] [amount]')
            cur.execute('SELECT client_id,username,balance FROM clients WHERE username=%s',(u,))
            user = cur.fetchone()
            if not user: return reply(f'❌ User "{u}" not found.')
            prev = float(user['balance'])
            new_bal = prev + amt
            if new_bal < 0: return reply(f'❌ Insufficient. Current: {php_format(prev)}')
            cur.execute('UPDATE clients SET balance=%s WHERE client_id=%s',(new_bal,user['client_id']))
            action = 'Added' if amt>=0 else 'Deducted'
            note = f'{action} via Facebook Messenger Bot | Method: MESSENGER BOT'
            cur.execute('INSERT INTO payments (client_id,client_balance,payment_amount,payment_note,payment_status,payment_delivery,payment_mode,payment_method,payment_create_date,payment_update_date) VALUES (%s,%s,%s,%s,3,1,"Automatic",36,NOW(),NOW())',(user['client_id'],new_bal,amt,note))
            db.commit()
            reply(f'✅ SUCCESS!\n💳 {action}: {php_format(abs(amt))}\n👤 {u}\n💰 Prev: {php_format(prev)}\n💵 New: {php_format(new_bal)}\n🕐 {now_time()}')
        elif cmd == 'adduser':
            if not owner: return reply('❌ Not authorized.')
            u = parts[1] if len(parts)>1 else ''
            e = parts[2] if len(parts)>2 else ''
            p = parts[3] if len(parts)>3 else ''
            if not u or not e or not p: return reply('❌ Usage: adduser [username] [email] [password]')
            cur.execute('SELECT client_id FROM clients WHERE username=%s OR email=%s',(u,e))
            if cur.fetchone(): return reply('❌ Already exists.')
            import hashlib
            cur.execute('INSERT INTO clients (username,email,password,balance,register_date) VALUES (%s,%s,%s,0,NOW())',(u,e,hashlib.md5(p.encode()).hexdigest()))
            db.commit()
            reply(f'✅ User Created!\n👤 {u}\n📧 {e}\n💵 ₱0.00')
        elif cmd == 'status':
            oid = int(parts[1]) if len(parts)>1 and parts[1].isdigit() else None
            if not oid: return reply('❌ Usage: status [order_id]')
            cur.execute('SELECT o.order_id,c.username,o.order_status,o.order_quantity,o.order_remains,o.order_charge,o.order_url FROM orders o JOIN clients c ON o.client_id=c.client_id WHERE o.order_id=%s',(oid,))
            order = cur.fetchone()
            if not order: return reply(f'❌ Order #{oid} not found.')
            reply(f'📦 ORDER #{order["order_id"]}\n👤 {order["username"]}\nStatus: {order["order_status"]}\nQty: {order["order_quantity"]}\nRemains: {order["order_remains"]}\nCharge: {php_format(order["order_charge"])}\nLink: {order["order_url"]}')
        elif cmd == 'change':
            if not owner: return reply('❌ Not authorized.')
            status = parts[1] if len(parts)>1 else ''
            oid = int(parts[2]) if len(parts)>2 and parts[2].isdigit() else None
            if status not in ['pending','inprogress','completed','partial','processing','canceled'] or not oid:
                return reply('❌ Usage: change [status] [order_id]')
            cur.execute('SELECT order_id,order_status FROM orders WHERE order_id=%s',(oid,))
            order = cur.fetchone()
            if not order: return reply(f'❌ Order #{oid} not found.')
            old = order['order_status']
            if status=='completed': cur.execute('UPDATE orders SET order_status=%s,order_remains=0 WHERE order_id=%s',(status,oid))
            else: cur.execute('UPDATE orders SET order_status=%s WHERE order_id=%s',(status,oid))
            db.commit()
            reply(f'✅ Order #{oid}\n🔄 {old} → {status}\n🕐 {now_time()}')
        elif cmd == 'resend':
            if not owner: return reply('❌ Not authorized.')
            oid = int(parts[1]) if len(parts)>1 and parts[1].isdigit() else None
            if not oid: return reply('❌ Usage: resend [order_id]')
            cur.execute('UPDATE orders SET order_status="pending" WHERE order_id=%s',(oid,))
            db.commit()
            reply(f'✅ Order #{oid} resent! → pending')
        elif cmd == 'orders':
            u = parts[1] if len(parts)>1 else ''
            if not u: return reply('❌ Usage: orders [username]')
            cur.execute('SELECT o.order_id,o.order_status,o.order_charge,o.order_quantity FROM orders o JOIN clients c ON o.client_id=c.client_id WHERE c.username=%s ORDER BY o.order_id DESC LIMIT 10',(u,))
            orders = cur.fetchall()
            if not orders: return reply(f'📦 No orders for {u}')
            msg = f'📦 ORDERS FOR {u}\n\n'
            for o in orders: msg += f'#{o["order_id"]} | {o["order_status"]} | {php_format(o["order_charge"])}\n'
            reply(msg)
        cur.close()
        db.close()
    except Exception as e:
        print(f'Command error: {e}')
        try: reply(f'❌ Error: {str(e)}')
        except: pass

def run_bot():
    print('Starting SMM FB Cookie Bot...')
    session = get_session()
    if not verify_login(session):
        print('Cookies expired! Update C_USER, XS, DATR, FR in environment variables.')
        return
    print('Bot running! Polling every 5s...')
    seen = set()
    while True:
        try:
            threads = get_inbox(session)
            print(f'Checking {len(threads)} threads...')
            for thread in threads[:10]:
                tid = thread['id']
                msgs = get_messages(session, thread['url'])
                for msg in msgs[-3:]:
                    key = f'{tid}_{msg[:30]}'
                    if key not in seen and len(msg) > 1:
                        seen.add(key)
                        if len(seen) > 1000: seen = set(list(seen)[-500:])
                        print(f'Message: {msg[:50]}')
                        handle_command(C_USER, msg, tid, session)
                        time.sleep(2)
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Loop error: {e}')
            time.sleep(10)

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'SMM Bot Running!')
    def log_message(self, format, *args):
        pass

def start_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    print(f'Web server started!')
    run_bot()
