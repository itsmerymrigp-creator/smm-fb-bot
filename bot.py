import requests
import time
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
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
 
STATUS = {'login': 'Starting...', 'threads': 0, 'last': 'Never', 'msgs': [], 'debug': []}
 
 
def get_db():
    import mysql.connector
    return mysql.connector.connect(host=DB_HOST, database=DB_NAME, user=DB_USER_DB, password=DB_PASS)
 
 
def php_format(n):
    return 'P{:.2f}'.format(float(n))
 
 
def now_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 
 
def is_owner(uid):
    return str(uid) in OWNER_IDS
 
 
def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    for name, value in {'c_user': C_USER, 'xs': XS, 'datr': DATR, 'fr': FR}.items():
        session.cookies.set(name, value, domain='.facebook.com')
    return session
 
 
def verify_login(session):
    r = session.get('https://m.facebook.com/')
    if 'login' in r.url.lower():
        return False
    return True
 
 
def get_inbox(session):
    try:
        r = session.get('https://m.facebook.com/messages/', headers={'Accept-Encoding': 'identity'})
        soup = BeautifulSoup(r.text, 'html.parser')
        preview = r.text[:500].replace('\n', ' ').replace('\r', '')
        STATUS['debug'] = ['URL: ' + r.url, 'Preview: ' + preview[:300]]
        print('URL: ' + r.url, flush=True)
        print('Preview: ' + preview[:300], flush=True)
        threads = []
        seen = []
        all_hrefs = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            all_hrefs.append(href[:80])
            if 'messages' in href and ('tid=' in href or 'thread' in href):
                tid = ''
                if 'tid=' in href:
                    tid = href.split('tid=')[-1].split('&')[0]
                elif 'thread_fbid=' in href:
                    tid = href.split('thread_fbid=')[-1].split('&')[0]
                if tid and tid not in seen:
                    seen.append(tid)
                    url = 'https://m.facebook.com' + href if href.startswith('/') else href
                    threads.append({'id': tid, 'url': url})
        msg_hrefs = [h for h in all_hrefs if 'message' in h.lower()]
        STATUS['debug'].append('Msg hrefs: ' + str(msg_hrefs[:5]))
        STATUS['debug'].append('Total hrefs: ' + str(len(all_hrefs)))
        print('Msg hrefs: ' + str(msg_hrefs[:5]), flush=True)
        print('Found ' + str(len(threads)) + ' threads', flush=True)
        return threads
    except Exception as e:
        print('Inbox error: ' + str(e), flush=True)
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
        print('Messages error: ' + str(e), flush=True)
        return []
 
 
def send_message(session, thread_id, text):
    try:
        url = 'https://m.facebook.com/messages/read/?tid=' + thread_id
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        form = None
        for f in soup.find_all('form'):
            if f.find('textarea') or f.find('input', {'name': 'body'}):
                form = f
                break
        if not form:
            print('No form found', flush=True)
            return False
        data = {}
        for inp in form.find_all(['input', 'textarea']):
            n = inp.get('name')
            if n:
                data[n] = inp.get('value', '')
        data['body'] = text
        action = form.get('action', '')
        if action.startswith('/'):
            action = 'https://m.facebook.com' + action
        session.post(action, data=data)
        return True
    except Exception as e:
        print('Send error: ' + str(e), flush=True)
        return False
 
 
def handle_command(sender_id, text, thread_id, session):
    parts = text.strip().split(' ')
    cmd = parts[0].lower()
    owner = is_owner(sender_id)
 
    def reply(msg):
        send_message(session, thread_id, msg)
 
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
 
        if cmd == 'test':
            reply('Bot working! ID: ' + sender_id + ' Owner: ' + ('Yes' if owner else 'No') + ' Time: ' + now_time())
        elif cmd == 'myid':
            reply('Your ID: ' + sender_id)
        elif cmd == 'help':
            reply('SMM BOT COMMANDS\n\nfund [user] [amount]\nfund [user] [-amount]\nbalance [user]\nadduser [user] [email] [pass]\nstatus [id]\nchange [status] [id]\nresend [id]\norders [user]\ntest\nmyid')
        elif cmd == 'balance':
            u = parts[1] if len(parts) > 1 else ''
            if not u:
                return reply('Usage: balance [username]')
            cur.execute('SELECT username,balance FROM clients WHERE username=%s', (u,))
            user = cur.fetchone()
            if not user:
                return reply('User "' + u + '" not found.')
            reply('BALANCE\nUser: ' + user['username'] + '\nBalance: ' + php_format(user['balance']) + '\nTime: ' + now_time())
        elif cmd == 'fund':
            if not owner:
                return reply('Not authorized.')
            u = parts[1] if len(parts) > 1 else ''
            amt = float(parts[2]) if len(parts) > 2 else None
            if not u or amt is None:
                return reply('Usage: fund [username] [amount]')
            cur.execute('SELECT client_id,username,balance FROM clients WHERE username=%s', (u,))
            user = cur.fetchone()
            if not user:
                return reply('User "' + u + '" not found.')
            prev = float(user['balance'])
            new_bal = prev + amt
            if new_bal < 0:
                return reply('Insufficient balance. Current: ' + php_format(prev))
            cur.execute('UPDATE clients SET balance=%s WHERE client_id=%s', (new_bal, user['client_id']))
            action = 'Added' if amt >= 0 else 'Deducted'
            note = action + ' via Facebook Messenger Bot | Method: MESSENGER BOT'
            cur.execute('INSERT INTO payments (client_id,client_balance,payment_amount,payment_note,payment_status,payment_delivery,payment_mode,payment_method,payment_create_date,payment_update_date) VALUES (%s,%s,%s,%s,3,1,"Automatic",36,NOW(),NOW())', (user['client_id'], new_bal, amt, note))
            db.commit()
            reply('SUCCESS!\n' + action + ': ' + php_format(abs(amt)) + '\nUser: ' + u + '\nPrev: ' + php_format(prev) + '\nNew: ' + php_format(new_bal) + '\nTime: ' + now_time())
        elif cmd == 'adduser':
            if not owner:
                return reply('Not authorized.')
            u = parts[1] if len(parts) > 1 else ''
            e = parts[2] if len(parts) > 2 else ''
            p = parts[3] if len(parts) > 3 else ''
            if not u or not e or not p:
                return reply('Usage: adduser [username] [email] [pass]')
            cur.execute('SELECT client_id FROM clients WHERE username=%s OR email=%s', (u, e))
            if cur.fetchone():
                return reply('Already exists.')
            import hashlib
            cur.execute('INSERT INTO clients (username,email,password,balance,register_date) VALUES (%s,%s,%s,0,NOW())', (u, e, hashlib.md5(p.encode()).hexdigest()))
            db.commit()
            reply('User Created! Username: ' + u + ' Email: ' + e)
        elif cmd == 'status':
            oid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            if not oid:
                return reply('Usage: status [order_id]')
            cur.execute('SELECT o.order_id,c.username,o.order_status,o.order_quantity,o.order_remains,o.order_charge,o.order_url FROM orders o JOIN clients c ON o.client_id=c.client_id WHERE o.order_id=%s', (oid,))
            order = cur.fetchone()
            if not order:
                return reply('Order #' + str(oid) + ' not found.')
            reply('ORDER #' + str(order['order_id']) + '\nUser: ' + order['username'] + '\nStatus: ' + order['order_status'] + '\nQty: ' + str(order['order_quantity']) + '\nRemains: ' + str(order['order_remains']) + '\nCharge: ' + php_format(order['order_charge']) + '\nLink: ' + order['order_url'])
        elif cmd == 'change':
            if not owner:
                return reply('Not authorized.')
            status = parts[1] if len(parts) > 1 else ''
            oid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
            if status not in ['pending', 'inprogress', 'completed', 'partial', 'processing', 'canceled'] or not oid:
                return reply('Usage: change [status] [order_id]')
            cur.execute('SELECT order_id,order_status FROM orders WHERE order_id=%s', (oid,))
            order = cur.fetchone()
            if not order:
                return reply('Order #' + str(oid) + ' not found.')
            old = order['order_status']
            if status == 'completed':
                cur.execute('UPDATE orders SET order_status=%s,order_remains=0 WHERE order_id=%s', (status, oid))
            else:
                cur.execute('UPDATE orders SET order_status=%s WHERE order_id=%s', (status, oid))
            db.commit()
            reply('Order #' + str(oid) + ' Updated ' + old + ' -> ' + status)
        elif cmd == 'resend':
            if not owner:
                return reply('Not authorized.')
            oid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            if not oid:
                return reply('Usage: resend [order_id]')
            cur.execute('UPDATE orders SET order_status="pending" WHERE order_id=%s', (oid,))
            db.commit()
            reply('Order #' + str(oid) + ' resent -> pending')
        elif cmd == 'orders':
            u = parts[1] if len(parts) > 1 else ''
            if not u:
                return reply('Usage: orders [username]')
            cur.execute('SELECT o.order_id,o.order_status,o.order_charge,o.order_quantity FROM orders o JOIN clients c ON o.client_id=c.client_id WHERE c.username=%s ORDER BY o.order_id DESC LIMIT 10', (u,))
            orders = cur.fetchall()
            if not orders:
                return reply('No orders for ' + u)
            msg = 'ORDERS FOR ' + u + '\n\n'
            for o in orders:
                msg += '#' + str(o['order_id']) + ' | ' + o['order_status'] + ' | ' + php_format(o['order_charge']) + '\n'
            reply(msg)
 
        cur.close()
        db.close()
    except Exception as e:
        print('Command error: ' + str(e), flush=True)
        try:
            reply('Error: ' + str(e))
        except:
            pass
 
 
class BotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = '<html><body style="background:#111;color:#0f0;font-family:monospace;padding:20px">'
        html += '<h2>SMM Bot Status</h2>'
        html += '<p>Login: ' + STATUS['login'] + '</p>'
        html += '<p>Threads found: ' + str(STATUS['threads']) + '</p>'
        html += '<p>Last check: ' + STATUS['last'] + '</p>'
        html += '<h3>Recent messages:</h3><pre>'
        for m in STATUS['msgs'][-10:]:
            html += m + '\n'
        html += '</pre><h3>Debug:</h3><pre>'
        for d in STATUS['debug'][-10:]:
            html += d + '\n'
        html += '</pre><p><a href="/" style="color:#0f0">Refresh</a></p>'
        html += '</body></html>'
        self.wfile.write(html.encode())
 
    def log_message(self, format, *args):
        pass
 
 
def start_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), BotHandler)
    print('Web server started on port ' + str(port), flush=True)
    server.serve_forever()
 
 
def run_bot():
    print('Starting SMM FB Cookie Bot...', flush=True)
    session = get_session()
    if not verify_login(session):
        STATUS['login'] = 'FAILED - Cookies expired!'
        print('Cookies expired!', flush=True)
        while True:
            time.sleep(60)
    STATUS['login'] = 'OK - Logged in!'
    print('Login OK!', flush=True)
    seen = set()
    while True:
        try:
            threads = get_inbox(session)
            STATUS['threads'] = len(threads)
            STATUS['last'] = now_time()
            for thread in threads[:10]:
                tid = thread['id']
                msgs = get_messages(session, thread['url'])
                for msg in msgs[-3:]:
                    key = tid + '_' + msg[:30]
                    if key not in seen and len(msg) > 1:
                        seen.add(key)
                        if len(seen) > 1000:
                            seen = set(list(seen)[-500:])
                        print('Message: ' + msg[:50], flush=True)
                        STATUS['msgs'].append(msg[:50])
                        if len(STATUS['msgs']) > 50:
                            STATUS['msgs'] = STATUS['msgs'][-25:]
                        handle_command(C_USER, msg, tid, session)
                        time.sleep(2)
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print('Loop error: ' + str(e), flush=True)
            time.sleep(10)
 
 
if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    run_bot()
