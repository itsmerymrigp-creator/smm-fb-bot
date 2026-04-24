import requests
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup
 
FB_EMAIL = os.environ.get('FB_EMAIL', 'boostlysmmbot@gmail.com')
FB_PASSWORD = os.environ.get('FB_PASSWORD', '@Reymar08')
OWNER_IDS = os.environ.get('OWNER_IDS', '26377628695212164').split(',')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'boostlys_smm')
DB_USER = os.environ.get('DB_USER', 'boostlys_smm')
DB_PASS = os.environ.get('DB_PASS', 'boostlys_smm')
 
def get_db():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
 
def php_format(n):
    return '₱{:.2f}'.format(float(n))
 
def now_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 
def is_owner(uid):
    return str(uid) in OWNER_IDS
 
def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    
    r = session.get('https://mbasic.facebook.com/login/')
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    
    form = soup.find('form')
    if not form:
        print('Login form not found!')
        return None
    
    data = {}
    for inp in form.find_all('input'):
        name = inp.get('name')
        if name:
            data[name] = inp.get('value', '')
    
    data['email'] = FB_EMAIL
    data['pass'] = FB_PASSWORD
    
    action = form.get('action', '')
    if not action:
        action = 'https://mbasic.facebook.com/login/device-based/regular/login/'
    elif action.startswith('/'):
        action = 'https://mbasic.facebook.com' + action
    
    print(f'Logging in to: {action}')
    r = session.post(action, data=data, allow_redirects=True)
    
    if 'c_user' in session.cookies.get_dict():
        print('Login successful!')
        return session
    elif 'checkpoint' in r.url:
        print('Checkpoint required - account needs verification')
        return None
    else:
        print(f'Login may have failed. URL: {r.url}')
        print('Trying to continue anyway...')
        return session
 
def get_inbox(session):
    try:
        r = session.get('https://mbasic.facebook.com/messages/')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        threads = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if '/messages/read/' in href and 'tid=' in href:
                tid = href.split('tid=')[-1].split('&')[0]
                if tid:
                    threads.append({'id': tid, 'url': href})
        return threads
    except Exception as e:
        print(f'Error getting inbox: {e}')
        return []
 
def get_thread_messages(session, thread_url):
    try:
        if not thread_url.startswith('http'):
            thread_url = 'https://mbasic.facebook.com' + thread_url
        r = session.get(thread_url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        messages = []
        for div in soup.find_all('div', {'data-sigil': 'message'}):
            text = div.get_text(strip=True)
            if text:
                messages.append(text)
        return messages
    except Exception as e:
        print(f'Error getting messages: {e}')
        return []
 
def send_fb_message(session, thread_id, text):
    try:
        thread_url = f'https://mbasic.facebook.com/messages/read/?tid={thread_id}'
        r = session.get(thread_url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        form = soup.find('form', {'id': 'composer_form'})
        if not form:
            forms = soup.find_all('form')
            for f in forms:
                if f.find('textarea') or f.find('input', {'name': 'body'}):
                    form = f
                    break
        
        if not form:
            print('Send form not found')
            return False
        
        data = {}
        for inp in form.find_all(['input', 'textarea']):
            name = inp.get('name')
            if name:
                data[name] = inp.get('value', '')
        
        data['body'] = text
        
        action = form.get('action', '')
        if action.startswith('/'):
            action = 'https://mbasic.facebook.com' + action
        
        session.post(action, data=data)
        print(f'Sent: {text[:50]}')
        return True
    except Exception as e:
        print(f'Error sending: {e}')
        return False
 
def handle_command(sender_id, text, thread_id, session):
    parts = text.strip().split(' ')
    cmd = parts[0].lower()
    owner = is_owner(sender_id)
 
    def reply(msg):
        send_fb_message(session, thread_id, msg)
 
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
 
        if cmd == 'test':
            reply(f'✅ Bot working!\nYour ID: {sender_id}\nIs Owner: {"Yes" if owner else "No"}\nTime: {now_time()}')
 
        elif cmd == 'myid':
            reply(f'Your ID: {sender_id}')
 
        elif cmd == 'help':
            reply('💰 SMM BOT COMMANDS\n\n• fund [user] [amount]\n• fund [user] [-amount]\n• balance [user]\n• adduser [user] [email] [pass]\n• status [order_id]\n• change [status] [order_id]\n• resend [order_id]\n• orders [user]\n• test\n• myid')
 
        elif cmd == 'balance':
            username = parts[1] if len(parts) > 1 else ''
            if not username:
                return reply('❌ Usage: balance [username]')
            cursor.execute('SELECT username, balance FROM clients WHERE username = %s', (username,))
            user = cursor.fetchone()
            if not user:
                return reply(f'❌ User "{username}" not found.')
            reply(f'💰 BALANCE\n\n👤 User: {user["username"]}\n💵 Balance: {php_format(user["balance"])}\n🕐 {now_time()}')
 
        elif cmd == 'fund':
            if not owner:
                return reply('❌ Not authorized.')
            username = parts[1] if len(parts) > 1 else ''
            amount = float(parts[2]) if len(parts) > 2 else None
            if not username or amount is None:
                return reply('❌ Usage: fund [username] [amount]')
            cursor.execute('SELECT client_id, username, balance FROM clients WHERE username = %s', (username,))
            user = cursor.fetchone()
            if not user:
                return reply(f'❌ User "{username}" not found.')
            prev = float(user['balance'])
            new_bal = prev + amount
            if new_bal < 0:
                return reply(f'❌ Insufficient balance. Current: {php_format(prev)}')
            cursor.execute('UPDATE clients SET balance = %s WHERE client_id = %s', (new_bal, user['client_id']))
            action = 'Added' if amount >= 0 else 'Deducted'
            note = f'{action} via Facebook Messenger Bot | Method: MESSENGER BOT'
            cursor.execute('INSERT INTO payments (client_id, client_balance, payment_amount, payment_note, payment_status, payment_delivery, payment_mode, payment_method, payment_create_date, payment_update_date) VALUES (%s, %s, %s, %s, 3, 1, "Automatic", 36, NOW(), NOW())',
                (user['client_id'], new_bal, amount, note))
            db.commit()
            reply(f'✅ SUCCESS!\n\n💳 {action}: {php_format(abs(amount))}\n👤 User: {username}\n💰 Prev: {php_format(prev)}\n💵 New: {php_format(new_bal)}\n🕐 {now_time()}')
 
        elif cmd == 'adduser':
            if not owner:
                return reply('❌ Not authorized.')
            username = parts[1] if len(parts) > 1 else ''
            email = parts[2] if len(parts) > 2 else ''
            password = parts[3] if len(parts) > 3 else ''
            if not username or not email or not password:
                return reply('❌ Usage: adduser [username] [email] [password]')
            cursor.execute('SELECT client_id FROM clients WHERE username = %s OR email = %s', (username, email))
            if cursor.fetchone():
                return reply('❌ Username or email already exists.')
            import hashlib
            hashed = hashlib.md5(password.encode()).hexdigest()
            cursor.execute('INSERT INTO clients (username, email, password, balance, register_date) VALUES (%s, %s, %s, 0, NOW())', (username, email, hashed))
            db.commit()
            reply(f'✅ User Created!\n👤 {username}\n📧 {email}\n💵 ₱0.00\n🕐 {now_time()}')
 
        elif cmd == 'status':
            order_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            if not order_id:
                return reply('❌ Usage: status [order_id]')
            cursor.execute('SELECT o.order_id, c.username, o.order_status, o.order_quantity, o.order_remains, o.order_charge, o.order_url FROM orders o JOIN clients c ON o.client_id = c.client_id WHERE o.order_id = %s', (order_id,))
            order = cursor.fetchone()
            if not order:
                return reply(f'❌ Order #{order_id} not found.')
            reply(f'📦 ORDER STATUS\n\nID: #{order["order_id"]}\n👤 {order["username"]}\nStatus: {order["order_status"]}\nQty: {order["order_quantity"]}\nRemains: {order["order_remains"]}\nCharge: {php_format(order["order_charge"])}\nLink: {order["order_url"]}')
 
        elif cmd == 'change':
            if not owner:
                return reply('❌ Not authorized.')
            status = parts[1] if len(parts) > 1 else ''
            order_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
            valid = ['pending', 'inprogress', 'completed', 'partial', 'processing', 'canceled']
            if status not in valid or not order_id:
                return reply('❌ Usage: change [status] [order_id]')
            cursor.execute('SELECT order_id, order_status FROM orders WHERE order_id = %s', (order_id,))
            order = cursor.fetchone()
            if not order:
                return reply(f'❌ Order #{order_id} not found.')
            old = order['order_status']
            if status == 'completed':
                cursor.execute('UPDATE orders SET order_status = %s, order_remains = 0 WHERE order_id = %s', (status, order_id))
            else:
                cursor.execute('UPDATE orders SET order_status = %s WHERE order_id = %s', (status, order_id))
            db.commit()
            reply(f'✅ Order #{order_id} Updated\n🔄 {old} → {status}\n🕐 {now_time()}')
 
        elif cmd == 'resend':
            if not owner:
                return reply('❌ Not authorized.')
            order_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            if not order_id:
                return reply('❌ Usage: resend [order_id]')
            cursor.execute('UPDATE orders SET order_status = "pending" WHERE order_id = %s', (order_id,))
            db.commit()
            reply(f'✅ Order #{order_id} resent! → pending\n🕐 {now_time()}')
 
        elif cmd == 'orders':
            username = parts[1] if len(parts) > 1 else ''
            if not username:
                return reply('❌ Usage: orders [username]')
            cursor.execute('SELECT o.order_id, o.order_status, o.order_charge, o.order_quantity FROM orders o JOIN clients c ON o.client_id = c.client_id WHERE c.username = %s ORDER BY o.order_id DESC LIMIT 10', (username,))
            orders = cursor.fetchall()
            if not orders:
                return reply(f'📦 No orders for {username}')
            msg = f'📦 ORDERS FOR {username}\n\n'
            for o in orders:
                msg += f'#{o["order_id"]} | {o["order_status"]} | Qty:{o["order_quantity"]} | {php_format(o["order_charge"])}\n'
            reply(msg)
 
        cursor.close()
        db.close()
 
    except Exception as e:
        print(f'Command error: {e}')
        try:
            reply(f'❌ Error: {str(e)}')
        except:
            pass
 
def run_bot():
    print('Starting SMM FB Bot...')
    session = get_session()
    
    if not session:
        print('Failed to login! Check credentials.')
        return
    
    print('Bot is running! Checking messages...')
    seen = set()
    
    while True:
        try:
            threads = get_inbox(session)
            print(f'Found {len(threads)} threads')
            
            for thread in threads[:10]:
                tid = thread['id']
                url = thread['url']
                
                messages = get_thread_messages(session, url)
                
                for msg in messages[-2:]:
                    msg_key = f'{tid}_{msg[:30]}'
                    if msg_key not in seen and len(msg) > 1:
                        seen.add(msg_key)
                        if len(seen) > 500:
                            seen = set(list(seen)[-250:])
                        print(f'Processing: {msg[:50]}')
                        handle_command('26377628695212164', msg, tid, session)
                        time.sleep(1)
            
            time.sleep(5)
            
        except Exception as e:
            print(f'Loop error: {e}')
            time.sleep(10)
            try:
                session = get_session()
            except:
                time.sleep(30)
 
if __name__ == '__main__':
    run_bot()
