# Tax Summit Analytics Dashboard

## 🚀 Deployment on Railway.app

### Prerequisites
- GitHub account
- Railway.app account
- Excel file with your Tax Summit data

### Step 1: Fork/Clone this Repository
```bash
git clone <your-repo-url>
cd TAX_SUMMIT
```

### Step 2: Set Up Local Database (First Time)
1. Install MySQL locally
2. Create `.env` file (copy from `.env.example`)
3. Update `.env` with your local MySQL credentials
4. Run setup scripts:
```bash
pip install -r requirements.txt
python excel_to_sql.py
python setup_database_architecture.py
python analysis_table_with_auto_triggers.py
```

### Step 3: Deploy to Railway

#### A. Create Railway Project
1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose this repository

#### B. Add MySQL Database
1. In Railway dashboard, click "New"
2. Select "Database" → "MySQL"
3. Wait for provisioning

#### C. Set Environment Variables
1. Click on your web service
2. Go to "Variables" tab
3. Add these variables (copy from MySQL service in Railway):
```
   DB_HOST=<from-railway-mysql>
   DB_USER=root
   DB_PASS=<from-railway-mysql>
   DB_NAME=Tax_summit
   DB_TABLE=Tax_summit_master_data
   PORT=8050
```

#### D. Import Data to Railway MySQL
Option 1 - Use Railway CLI:
```bash
npm i -g @railway/cli
railway login
railway link
```

Then update your `.env` with Railway credentials and run:
```bash
python excel_to_sql.py
python setup_database_architecture.py
python analysis_table_with_auto_triggers.py
```

Option 2 - Use MySQL Workbench:
- Connect to Railway MySQL using credentials
- Import your local database

### Step 4: Access Your Dashboard
- Railway will provide a URL: `https://your-app.up.railway.app`
- Dashboard will auto-refresh every 30 seconds

## 📁 File Structure

### Dashboard & Deployment
- `analysis_dashboard.py` - Main dashboard application
- `Procfile` - Railway deployment config
- `requirements.txt` - Python dependencies

### Database Setup
- `excel_to_sql.py` - Import Excel to MySQL
- `setup_database_architecture.py` - Create child tables
- `analysis_table_with_auto_triggers.py` - Create analysis tables

### vCard Generators
- `tax_vcard_generator.py` - Generate Tax contacts
- `cfo_vcard_generator.py` - Generate CFO contacts  
- `Other_Persons_vCard_Generator.py` - Generate Other contacts

## 🔒 Security Notes
- Never commit `.env` file
- Always use environment variables in Railway
- Keep your MySQL password secure

## 🛠️ Local Development
```bash
python analysis_dashboard.py
```
Visit: http://localhost:8050