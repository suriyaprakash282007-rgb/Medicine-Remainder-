"""
💊 Medicine Reminder for Elderly - Enhanced Version
===================================================
Architecture: Flask Backend + SQLite + ML Prediction + Twilio SMS
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import json
import random
import threading
import time as time_module

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'medicine_reminder_secret_key_2026_enhanced')

DATABASE = 'medicine_reminder.db'

# ============ TWILIO CONFIGURATION ============
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

try:
    from twilio.rest import Client as TwilioClient  # type: ignore
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("⚠️  Twilio not installed. SMS notifications disabled.")
    print("   Install with: pip install twilio")

# ============ DATABASE FUNCTIONS ============

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            whatsapp_number TEXT,
            age INTEGER,
            notification_preference TEXT DEFAULT 'sms',
            sms_enabled INTEGER DEFAULT 1,
            whatsapp_enabled INTEGER DEFAULT 0,
            email_enabled INTEGER DEFAULT 1,
            timezone TEXT DEFAULT 'Asia/Kolkata',
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caregivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            relationship TEXT,
            is_primary INTEGER DEFAULT 0,
            notify_on_missed INTEGER DEFAULT 1,
            notify_on_emergency INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            dosage_unit TEXT DEFAULT 'tablet',
            frequency TEXT DEFAULT 'once_daily',
            instructions TEXT,
            start_date DATE NOT NULL,
            end_date DATE,
            is_active INTEGER DEFAULT 1,
            stock_quantity INTEGER DEFAULT 0,
            low_stock_alert INTEGER DEFAULT 10,
            color TEXT DEFAULT '#4F46E5',
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reminder_time TEXT NOT NULL,
            days_of_week TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat,Sun',
            is_active INTEGER DEFAULT 1,
            snooze_minutes INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicine_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            medicine_id INTEGER NOT NULL,
            reminder_id INTEGER,
            status TEXT DEFAULT 'pending',
            taken_at TIMESTAMP,
            scheduled_time TIMESTAMP NOT NULL,
            delay_minutes INTEGER DEFAULT 0,
            notes TEXT,
            mood TEXT,
            side_effects TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            medicine_id INTEGER,
            prediction_type TEXT NOT NULL,
            risk_score REAL,
            confidence REAL,
            suggested_time TEXT,
            reason TEXT,
            is_acknowledged INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valid_until TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reminder_id INTEGER,
            notification_type TEXT NOT NULL,
            recipient TEXT NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergency_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT,
            location TEXT,
            status TEXT DEFAULT 'active',
            resolved_at TIMESTAMP,
            resolved_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    salt = "medicine_reminder_salt"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ ML PREDICTION ENGINE ============

class MedicinePredictionEngine:
    
    @staticmethod
    def calculate_adherence_score(user_id, days=30):
        conn = get_db()
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'taken' THEN 1 ELSE 0 END) as taken,
                SUM(CASE WHEN status = 'missed' THEN 1 ELSE 0 END) as missed,
                AVG(delay_minutes) as avg_delay
            FROM medicine_history
            WHERE user_id = ? AND DATE(scheduled_time) >= DATE('now', '-' || ? || ' days')
        ''', (user_id, days)).fetchone()
        conn.close()
        
        if not stats['total'] or stats['total'] == 0:
            return {'score': 100, 'total': 0, 'taken': 0, 'missed': 0, 'avg_delay': 0}
        
        score = round((stats['taken'] / stats['total']) * 100, 1)
        return {
            'score': score,
            'total': stats['total'],
            'taken': stats['taken'] or 0,
            'missed': stats['missed'] or 0,
            'avg_delay': round(stats['avg_delay'] or 0, 1)
        }
    
    @staticmethod
    def predict_miss_risk(user_id, medicine_id=None, time_slot=None):
        conn = get_db()
        
        history = conn.execute('''
            SELECT 
                strftime('%H', scheduled_time) as hour,
                strftime('%w', scheduled_time) as day_of_week,
                status,
                delay_minutes
            FROM medicine_history
            WHERE user_id = ? 
            AND DATE(scheduled_time) >= DATE('now', '-30 days')
            ORDER BY scheduled_time DESC
            LIMIT 100
        ''', (user_id,)).fetchall()
        
        conn.close()
        
        if len(history) < 5:
            return {'risk_score': 0.1, 'confidence': 0.3, 'reason': 'Insufficient data', 'risk_level': 'low'}
        
        missed_count = sum(1 for h in history if h['status'] == 'missed')
        total_count = len(history)
        
        base_risk = missed_count / total_count if total_count > 0 else 0
        risk_score = min(base_risk * 1.5, 1.0)
        confidence = min(0.5 + (total_count / 200), 0.95)
        
        if risk_score > 0.5:
            reason = "High miss rate detected"
            risk_level = "high"
        elif risk_score > 0.3:
            reason = "Moderate adherence issues"
            risk_level = "medium"
        else:
            reason = "Good adherence pattern"
            risk_level = "low"
        
        return {
            'risk_score': round(risk_score, 2),
            'confidence': round(confidence, 2),
            'reason': reason,
            'risk_level': risk_level,
            'historical_rate': round(base_risk, 2)
        }
    
    @staticmethod
    def suggest_optimal_time(user_id, medicine_id):
        conn = get_db()
        
        success_times = conn.execute('''
            SELECT 
                strftime('%H:00', scheduled_time) as time_slot,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'taken' THEN 1 ELSE 0 END) as taken
            FROM medicine_history
            WHERE user_id = ? AND medicine_id = ?
            GROUP BY time_slot
            HAVING total >= 3
            ORDER BY (taken * 1.0 / total) DESC
            LIMIT 3
        ''', (user_id, medicine_id)).fetchall()
        
        conn.close()
        
        if success_times:
            best_time = success_times[0]
            return {
                'suggested_time': best_time['time_slot'],
                'success_rate': round((best_time['taken'] / best_time['total']) * 100, 1),
                'based_on': best_time['total']
            }
        
        return None

# ============ NOTIFICATION SERVICE ============

class NotificationService:
    
    @staticmethod
    def send_sms(to_number, message, user_id=None):
        if not TWILIO_AVAILABLE or not TWILIO_ACCOUNT_SID:
            print(f"📱 [SMS SIMULATION] To: {to_number}")
            print(f"   Message: {message}")
            return {'status': 'simulated', 'message': 'Twilio not configured'}
        
        try:
            client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            sms = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            
            if user_id:
                conn = get_db()
                conn.execute('''
                    INSERT INTO notification_logs (user_id, notification_type, recipient, message, status, sent_at)
                    VALUES (?, 'sms', ?, ?, 'sent', ?)
                ''', (user_id, to_number, message, datetime.now()))
                conn.commit()
                conn.close()
            
            return {'status': 'sent', 'sid': sms.sid}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def send_whatsapp(to_number, message, user_id=None):
        if not TWILIO_AVAILABLE or not TWILIO_ACCOUNT_SID:
            print(f"📱 [WhatsApp SIMULATION] To: {to_number}")
            print(f"   Message: {message}")
            return {'status': 'simulated', 'message': 'Twilio not configured'}
        
        try:
            client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            wa = client.messages.create(
                body=message,
                from_='whatsapp:' + TWILIO_PHONE_NUMBER,
                to='whatsapp:' + to_number
            )
            return {'status': 'sent', 'sid': wa.sid}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def send_reminder(user_id, medicine_name, dosage, reminder_time):
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if not user:
            return
        
        message = f"💊 Medicine Reminder\n\nTime to take {medicine_name} ({dosage})\n\nScheduled: {reminder_time}"
        
        if user['sms_enabled'] and user['phone']:
            NotificationService.send_sms(user['phone'], message, user_id)
        
        if user['whatsapp_enabled'] and user['whatsapp_number']:
            NotificationService.send_whatsapp(user['whatsapp_number'], message, user_id)
    
    @staticmethod
    def notify_caregiver(user_id, alert_type, message):
        conn = get_db()
        caregivers = conn.execute('''
            SELECT * FROM caregivers 
            WHERE user_id = ? AND (notify_on_missed = 1 OR notify_on_emergency = 1)
        ''', (user_id,)).fetchall()
        
        user = conn.execute('SELECT name FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        for caregiver in caregivers:
            full_message = f"⚠️ Alert for {user['name']}\n\n{message}"
            if caregiver['phone']:
                NotificationService.send_sms(caregiver['phone'], full_message)

prediction_engine = MedicinePredictionEngine()
notification_service = NotificationService()

# ============ WEB ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and user['password'] == hash_password(password):
            conn.execute('UPDATE users SET last_active = ? WHERE id = ?', (datetime.now(), user['id']))
            conn.commit()
            conn.close()
            
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash('Welcome back, ' + user['name'] + '!', 'success')
            return redirect(url_for('dashboard'))
        
        conn.close()
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        age = request.form.get('age')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password, phone, age) VALUES (?, ?, ?, ?, ?)',
                (name, email, hash_password(password), phone, age)
            )
            conn.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    
    today = datetime.now().strftime('%a')
    current_time = datetime.now().strftime('%H:%M')
    
    reminders = conn.execute('''
        SELECT r.*, m.name as medicine_name, m.dosage, m.dosage_unit, m.instructions, m.color,
               m.stock_quantity, m.low_stock_alert
        FROM reminders r
        JOIN medicines m ON r.medicine_id = m.id
        WHERE r.user_id = ? AND r.is_active = 1 AND m.is_active = 1
        AND r.days_of_week LIKE ?
        ORDER BY r.reminder_time
    ''', (session['user_id'], f'%{today}%')).fetchall()
    
    medicines = conn.execute(
        'SELECT * FROM medicines WHERE user_id = ? AND is_active = 1',
        (session['user_id'],)
    ).fetchall()
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_history = conn.execute('''
        SELECT reminder_id, status FROM medicine_history
        WHERE user_id = ? AND DATE(scheduled_time) = ?
    ''', (session['user_id'], today_date)).fetchall()
    
    taken_reminders = {h['reminder_id'] for h in today_history if h['status'] == 'taken'}
    
    adherence = prediction_engine.calculate_adherence_score(session['user_id'])
    risk_prediction = prediction_engine.predict_miss_risk(session['user_id'])
    
    caregivers_count = conn.execute(
        'SELECT COUNT(*) as count FROM caregivers WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()['count']
    
    low_stock = [m for m in medicines if m['stock_quantity'] <= m['low_stock_alert']]
    
    upcoming = [r for r in reminders if r['reminder_time'] >= current_time 
                and r['reminder_time'] <= (datetime.now() + timedelta(hours=3)).strftime('%H:%M')
                and r['id'] not in taken_reminders]
    
    conn.close()
    
    return render_template('dashboard.html', 
                         reminders=reminders,
                         taken_reminders=taken_reminders,
                         medicines=medicines,
                         adherence=adherence,
                         risk_prediction=risk_prediction,
                         caregivers_count=caregivers_count,
                         low_stock=low_stock,
                         upcoming=upcoming,
                         current_time=current_time)

@app.route('/medicines')
@login_required
def medicines():
    conn = get_db()
    medicines = conn.execute('''
        SELECT m.*, 
            (SELECT COUNT(*) FROM reminders r WHERE r.medicine_id = m.id AND r.is_active = 1) as reminder_count
        FROM medicines m
        WHERE m.user_id = ?
        ORDER BY m.is_active DESC, m.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('medicines.html', medicines=medicines)

@app.route('/medicines/add', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO medicines (user_id, name, dosage, dosage_unit, frequency, instructions, start_date, end_date, stock_quantity, low_stock_alert, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            request.form.get('name'),
            request.form.get('dosage'),
            request.form.get('dosage_unit', 'tablet'),
            request.form.get('frequency', 'once_daily'),
            request.form.get('instructions'),
            request.form.get('start_date'),
            request.form.get('end_date') or None,
            request.form.get('stock_quantity', 0),
            request.form.get('low_stock_alert', 10),
            request.form.get('color', '#4F46E5')
        ))
        
        medicine_id = cursor.lastrowid
        
        reminder_times = request.form.getlist('reminder_time')
        for time in reminder_times:
            if time:
                cursor.execute('''
                    INSERT INTO reminders (medicine_id, user_id, reminder_time)
                    VALUES (?, ?, ?)
                ''', (medicine_id, session['user_id'], time))
        
        conn.commit()
        conn.close()
        
        flash('Medicine added successfully!', 'success')
        return redirect(url_for('medicines'))
    
    return render_template('add_medicine.html')

@app.route('/medicines/<int:id>')
@login_required
def medicine_details(id):
    conn = get_db()
    medicine = conn.execute(
        'SELECT * FROM medicines WHERE id = ? AND user_id = ?',
        (id, session['user_id'])
    ).fetchone()
    
    if not medicine:
        flash('Medicine not found', 'error')
        return redirect(url_for('medicines'))
    
    reminders = conn.execute(
        'SELECT * FROM reminders WHERE medicine_id = ? ORDER BY reminder_time',
        (id,)
    ).fetchall()
    
    history = conn.execute('''
        SELECT * FROM medicine_history
        WHERE medicine_id = ? AND user_id = ?
        ORDER BY scheduled_time DESC
        LIMIT 10
    ''', (id, session['user_id'])).fetchall()
    
    suggestion = prediction_engine.suggest_optimal_time(session['user_id'], id)
    
    conn.close()
    return render_template('medicine_details.html', 
                         medicine=medicine, 
                         reminders=reminders,
                         history=history,
                         suggestion=suggestion)

@app.route('/medicines/<int:id>/delete', methods=['POST'])
@login_required
def delete_medicine(id):
    conn = get_db()
    conn.execute('DELETE FROM reminders WHERE medicine_id = ?', (id,))
    conn.execute('DELETE FROM medicine_history WHERE medicine_id = ?', (id,))
    conn.execute('DELETE FROM medicines WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Medicine deleted', 'success')
    return redirect(url_for('medicines'))

@app.route('/medicines/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_medicine(id):
    conn = get_db()
    conn.execute(
        'UPDATE medicines SET is_active = NOT is_active WHERE id = ? AND user_id = ?',
        (id, session['user_id'])
    )
    conn.commit()
    conn.close()
    return redirect(url_for('medicine_details', id=id))

@app.route('/reminders/<int:id>/take', methods=['POST'])
@login_required
def take_medicine(id):
    conn = get_db()
    reminder = conn.execute('SELECT * FROM reminders WHERE id = ?', (id,)).fetchone()
    
    if reminder:
        now = datetime.now()
        scheduled = datetime.strptime(reminder['reminder_time'], '%H:%M').replace(
            year=now.year, month=now.month, day=now.day
        )
        delay = max(0, int((now - scheduled).total_seconds() / 60))
        
        conn.execute('''
            INSERT INTO medicine_history (user_id, medicine_id, reminder_id, status, taken_at, scheduled_time, delay_minutes)
            VALUES (?, ?, ?, 'taken', ?, ?, ?)
        ''', (session['user_id'], reminder['medicine_id'], id, now, scheduled, delay))
        
        conn.execute(
            'UPDATE medicines SET stock_quantity = MAX(0, stock_quantity - 1) WHERE id = ?',
            (reminder['medicine_id'],)
        )
        conn.commit()
        flash('Medicine marked as taken! ✓', 'success')
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reminders/<int:id>/skip', methods=['POST'])
@login_required
def skip_medicine(id):
    conn = get_db()
    reminder = conn.execute('SELECT * FROM reminders WHERE id = ?', (id,)).fetchone()
    
    if reminder:
        now = datetime.now()
        conn.execute('''
            INSERT INTO medicine_history (user_id, medicine_id, reminder_id, status, scheduled_time)
            VALUES (?, ?, ?, 'skipped', ?)
        ''', (session['user_id'], reminder['medicine_id'], id, now))
        conn.commit()
        flash('Medicine skipped', 'info')
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reminders/<int:id>/miss', methods=['POST'])
@login_required
def miss_medicine(id):
    conn = get_db()
    reminder = conn.execute('''
        SELECT r.*, m.name as medicine_name, m.dosage
        FROM reminders r
        JOIN medicines m ON r.medicine_id = m.id
        WHERE r.id = ?
    ''', (id,)).fetchone()
    
    if reminder:
        now = datetime.now()
        conn.execute('''
            INSERT INTO medicine_history (user_id, medicine_id, reminder_id, status, scheduled_time)
            VALUES (?, ?, ?, 'missed', ?)
        ''', (session['user_id'], reminder['medicine_id'], id, now))
        conn.commit()
        
        notification_service.notify_caregiver(
            session['user_id'],
            'missed_dose',
            f"Missed dose: {reminder['medicine_name']} ({reminder['dosage']}) at {reminder['reminder_time']}"
        )
        
        flash('Dose marked as missed. Caregivers notified.', 'warning')
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def history():
    conn = get_db()
    
    filter_days = request.args.get('days', '30')
    
    history = conn.execute('''
        SELECT mh.*, m.name as medicine_name, m.dosage, m.dosage_unit, m.color
        FROM medicine_history mh
        JOIN medicines m ON mh.medicine_id = m.id
        WHERE mh.user_id = ? AND DATE(mh.scheduled_time) >= DATE('now', '-' || ? || ' days')
        ORDER BY mh.scheduled_time DESC
    ''', (session['user_id'], filter_days)).fetchall()
    
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'taken' THEN 1 ELSE 0 END) as taken,
            SUM(CASE WHEN status = 'missed' THEN 1 ELSE 0 END) as missed,
            SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
            AVG(delay_minutes) as avg_delay
        FROM medicine_history
        WHERE user_id = ? AND DATE(scheduled_time) >= DATE('now', '-' || ? || ' days')
    ''', (session['user_id'], filter_days)).fetchone()
    
    adherence = round((stats['taken'] / stats['total'] * 100)) if stats['total'] and stats['total'] > 0 else 0
    
    conn.close()
    return render_template('history.html', 
                         history=history, 
                         stats=stats, 
                         adherence=adherence, 
                         filter_days=filter_days)

@app.route('/caregivers')
@login_required
def caregivers():
    conn = get_db()
    caregivers = conn.execute(
        'SELECT * FROM caregivers WHERE user_id = ? ORDER BY is_primary DESC, name',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('caregivers.html', caregivers=caregivers)

@app.route('/caregivers/add', methods=['POST'])
@login_required
def add_caregiver():
    conn = get_db()
    conn.execute('''
        INSERT INTO caregivers (user_id, name, phone, email, relationship, is_primary)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        session['user_id'],
        request.form.get('name'),
        request.form.get('phone'),
        request.form.get('email'),
        request.form.get('relationship'),
        1 if request.form.get('is_primary') else 0
    ))
    conn.commit()
    conn.close()
    flash('Caregiver added successfully!', 'success')
    return redirect(url_for('caregivers'))

@app.route('/caregivers/<int:id>/delete', methods=['POST'])
@login_required
def delete_caregiver(id):
    conn = get_db()
    conn.execute('DELETE FROM caregivers WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Caregiver removed', 'success')
    return redirect(url_for('caregivers'))

@app.route('/emergency', methods=['POST'])
@login_required
def emergency_alert():
    conn = get_db()
    
    conn.execute('''
        INSERT INTO emergency_alerts (user_id, alert_type, message)
        VALUES (?, 'manual', ?)
    ''', (session['user_id'], request.form.get('message', 'Emergency button pressed')))
    conn.commit()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    caregivers = conn.execute(
        'SELECT * FROM caregivers WHERE user_id = ? AND notify_on_emergency = 1',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    emergency_message = f"🚨 EMERGENCY ALERT 🚨\n\n{user['name']} has pressed the emergency button!\n\nPlease check on them immediately.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    for caregiver in caregivers:
        if caregiver['phone']:
            notification_service.send_sms(caregiver['phone'], emergency_message)
    
    flash('Emergency alert sent to all caregivers!', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action', 'update_profile')
        
        if action == 'update_profile':
            conn.execute('''
                UPDATE users SET name = ?, phone = ?, whatsapp_number = ?, age = ?
                WHERE id = ?
            ''', (
                request.form.get('name'),
                request.form.get('phone'),
                request.form.get('whatsapp_number'),
                request.form.get('age'),
                session['user_id']
            ))
            session['user_name'] = request.form.get('name')
            flash('Profile updated!', 'success')
        
        elif action == 'update_notifications':
            conn.execute('''
                UPDATE users SET 
                    sms_enabled = ?,
                    whatsapp_enabled = ?,
                    email_enabled = ?,
                    notification_preference = ?
                WHERE id = ?
            ''', (
                1 if request.form.get('sms_enabled') else 0,
                1 if request.form.get('whatsapp_enabled') else 0,
                1 if request.form.get('email_enabled') else 0,
                request.form.get('notification_preference', 'sms'),
                session['user_id']
            ))
            flash('Notification settings updated!', 'success')
        
        conn.commit()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    adherence = prediction_engine.calculate_adherence_score(session['user_id'])
    
    conn.close()
    return render_template('profile.html', user=user, adherence=adherence)

# ============ API ENDPOINTS ============

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user and user['password'] == hash_password(password):
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email']
            }
        })
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/medicines')
@login_required
def api_medicines():
    conn = get_db()
    medicines = conn.execute('''
        SELECT * FROM medicines WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return jsonify({
        'medicines': [dict(m) for m in medicines]
    })

@app.route('/api/reminders/today')
@login_required
def api_today_reminders():
    conn = get_db()
    today = datetime.now().strftime('%a')
    
    reminders = conn.execute('''
        SELECT r.*, m.name as medicine_name, m.dosage, m.dosage_unit
        FROM reminders r
        JOIN medicines m ON r.medicine_id = m.id
        WHERE r.user_id = ? AND r.is_active = 1 AND m.is_active = 1
        AND r.days_of_week LIKE ?
        ORDER BY r.reminder_time
    ''', (session['user_id'], f'%{today}%')).fetchall()
    conn.close()
    
    return jsonify({
        'reminders': [dict(r) for r in reminders]
    })

@app.route('/api/prediction/risk')
@login_required
def api_risk_prediction():
    prediction = prediction_engine.predict_miss_risk(session['user_id'])
    return jsonify(prediction)

@app.route('/api/adherence')
@login_required
def api_adherence():
    days = request.args.get('days', 30, type=int)
    adherence = prediction_engine.calculate_adherence_score(session['user_id'], days)
    return jsonify(adherence)

# ============ STARTUP ============

if __name__ == '__main__':
    init_db()
    
    print("\n" + "="*60)
    print("💊 Medicine Reminder for Elderly - Enhanced Version")
    print("="*60)
    print("\n🏗️  Architecture:")
    print("   • Backend: Flask (Python)")
    print("   • Database: SQLite")
    print("   • ML Engine: Built-in prediction")
    print("   • Notifications: Twilio SMS/WhatsApp" + (" ✓" if TWILIO_AVAILABLE else " (Not configured)"))
    print("\n🌐 Open this link in your browser:")
    print("\n   ➜ http://127.0.0.1:5000")
    print("\n📱 API Endpoints:")
    print("   • GET  /api/health")
    print("   • POST /api/login")
    print("   • GET  /api/medicines")
    print("   • GET  /api/reminders/today")
    print("   • GET  /api/prediction/risk")
    print("   • GET  /api/adherence")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
