# 💊 Medicine Reminder for Elderly

A comprehensive web application to help elderly users (or their caregivers) manage medications with automated SMS/WhatsApp reminders.

## 🎯 Features

- ✅ **Medicine Management** - Add, edit, delete medicines with dosage details
- ⏰ **Flexible Reminders** - Set multiple reminder times per medicine
- 📱 **SMS & WhatsApp Notifications** - Automated reminders via Twilio
- 📊 **Adherence Tracking** - Track medicine history and statistics
- 📦 **Stock Management** - Low stock alerts
- 👴 **Elderly-Friendly UI** - Large buttons, clear text, voice support
- 🔐 **Secure Authentication** - JWT-based authentication

## 🏗️ Architecture

```
User (Mobile/Web App)
        ⬇
  React Frontend (Vite + Tailwind CSS)
        ⬇
  Node.js + Express Backend API
        ⬇
     MySQL Database
        ⬇
  Scheduler Service (node-cron)
        ⬇
   Twilio API (SMS / WhatsApp)
```

## 📁 Project Structure

```
medicine-reminder/
├── backend/
│   ├── config/
│   │   ├── database.js      # MySQL connection pool
│   │   └── dbSetup.js       # Database initialization script
│   ├── controllers/
│   │   ├── auth.controller.js
│   │   ├── medicine.controller.js
│   │   ├── reminder.controller.js
│   │   └── history.controller.js
│   ├── middleware/
│   │   └── auth.middleware.js
│   ├── routes/
│   │   ├── auth.routes.js
│   │   ├── medicine.routes.js
│   │   ├── reminder.routes.js
│   │   └── history.routes.js
│   ├── services/
│   │   ├── notification.service.js  # Twilio SMS/WhatsApp
│   │   └── scheduler.service.js     # Cron job for reminders
│   ├── .env.example
│   ├── package.json
│   └── server.js
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── Layout.jsx
    │   ├── context/
    │   │   └── AuthContext.jsx
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Register.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── Medicines.jsx
    │   │   ├── AddMedicine.jsx
    │   │   ├── MedicineDetails.jsx
    │   │   ├── TodayReminders.jsx
    │   │   ├── History.jsx
    │   │   └── Profile.jsx
    │   ├── services/
    │   │   └── api.js
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── postcss.config.js
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- MySQL 8.0+
- Twilio Account (for SMS/WhatsApp)

### Backend Setup

1. Navigate to backend folder:
   ```bash
   cd medicine-reminder/backend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

4. Configure your `.env`:
   ```env
   PORT=5000
   NODE_ENV=development
   
   # Database
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=medicine_reminder
   
   # JWT
   JWT_SECRET=your_super_secret_key
   JWT_EXPIRES_IN=7d
   
   # Twilio (get from twilio.com/console)
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   
   FRONTEND_URL=http://localhost:5173
   ```

5. Setup database:
   ```bash
   npm run db:setup
   ```

6. Start the server:
   ```bash
   npm run dev
   ```

### Frontend Setup

1. Navigate to frontend folder:
   ```bash
   cd medicine-reminder/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:5173 in your browser

## 📱 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | User login |
| GET | `/api/auth/profile` | Get user profile |
| PUT | `/api/auth/profile` | Update profile |
| PUT | `/api/auth/change-password` | Change password |

### Medicines
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/medicines` | Get all medicines |
| GET | `/api/medicines/:id` | Get single medicine |
| POST | `/api/medicines` | Add new medicine |
| PUT | `/api/medicines/:id` | Update medicine |
| DELETE | `/api/medicines/:id` | Delete medicine |
| PUT | `/api/medicines/:id/stock` | Update stock |

### Reminders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reminders` | Get all reminders |
| GET | `/api/reminders/today` | Get today's reminders |
| POST | `/api/reminders` | Add reminder |
| PUT | `/api/reminders/:id` | Update reminder |
| DELETE | `/api/reminders/:id` | Delete reminder |
| POST | `/api/reminders/:id/take` | Mark as taken |
| POST | `/api/reminders/:id/skip` | Skip medicine |

### History
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/history` | Get medicine history |
| GET | `/api/history/stats` | Get adherence stats |
| GET | `/api/history/weekly-report` | Get weekly report |

## 📊 Database Schema

### Users Table
- id, name, email, password, phone, whatsapp_number
- notification_preference, timezone, is_caregiver

### Medicines Table
- id, user_id, name, dosage, dosage_unit, frequency
- instructions, start_date, end_date, is_active
- stock_quantity, low_stock_alert

### Reminders Table
- id, medicine_id, user_id, reminder_time
- days_of_week, is_active, last_sent_at

### Medicine History Table
- id, user_id, medicine_id, reminder_id
- status (taken/missed/skipped), taken_at, scheduled_time

### Notification Logs Table
- id, user_id, reminder_id, notification_type
- status, message, error_message, sent_at

## 🔔 Twilio Setup

1. Create account at [twilio.com](https://twilio.com)
2. Get Account SID and Auth Token from console
3. Buy a phone number for SMS
4. For WhatsApp, join the Twilio Sandbox or apply for WhatsApp Business API

### WhatsApp Sandbox (Testing)
1. Go to Twilio Console > Messaging > Try it Out > WhatsApp
2. Send the join code to the sandbox number
3. Use `whatsapp:+14155238886` as your WhatsApp number

## 🎨 Tech Stack

### Frontend
- React.js 18 with Vite
- Tailwind CSS for styling
- React Router v6 for navigation
- Formik + Yup for forms
- Axios for API calls
- Lucide React for icons
- React Hot Toast for notifications

### Backend
- Node.js with Express.js
- MySQL with mysql2
- JWT for authentication
- bcryptjs for password hashing
- node-cron for scheduling
- Twilio for notifications
- express-validator for validation

## 🔒 Security Features

- Password hashing with bcrypt (10 rounds)
- JWT token authentication
- Protected API routes
- Input validation and sanitization
- CORS configuration

## 👴 Elderly-Friendly Features

- Large, touch-friendly buttons (min 48px)
- High contrast colors
- Clear, readable fonts (18px+)
- Simple navigation
- Voice reminder button (text-to-speech)
- SMS/WhatsApp reminders (no app needed)

## 📝 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Support

For issues or questions, please open a GitHub issue.
