"""
Telegram Bot for FB OTP Automation
Receives numbers file and triggers GitHub Actions
"""

import os
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7205135297:AAEKFDTNZBj0c1I23Ri_a_PjCuWn_KUiYyY')
ALLOWED_CHAT_ID = int(os.environ.get('CHAT_ID', '664193835'))

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
# Server Configuration (Supports multiple servers via Env Vars)
# Server Configuration (Supports multiple servers via Env Vars)
SERVERS = {
    "server1": {
        "name": "Server 1 (Main)",
        "repo": os.environ.get('GITHUB_REPO', 'egygo2004/fb-otp'),
        "token": os.environ.get('GITHUB_TOKEN', ''),
        "branch": os.environ.get('GITHUB_BRANCH', 'master')
    }
}

# Check for additional servers in Env Vars (SERVER_2_REPO, SERVER_2_TOKEN, etc.)
for i in range(2, 51): # Support up to 50 servers via Env Vars
    repo_var = f"SERVER_{i}_REPO"
    token_var = f"SERVER_{i}_TOKEN"
    name_var = f"SERVER_{i}_NAME"
    branch_var = f"SERVER_{i}_BRANCH"
    
    if os.environ.get(repo_var) and os.environ.get(token_var):
        SERVERS[f"server{i}"] = {
            "name": os.environ.get(name_var, f"Server {i}"),
            "repo": os.environ.get(repo_var),
            "token": os.environ.get(token_var),
            "branch": os.environ.get(branch_var, 'master')
        }

# Server Status Tracking (persistent via DISABLED_SERVERS env var)
# Format: "server1,server3" = these servers are disabled
DISABLED_SERVERS_STR = os.environ.get('DISABLED_SERVERS', '')
DISABLED_SET = set(DISABLED_SERVERS_STR.split(',')) if DISABLED_SERVERS_STR else set()
SERVER_STATUS = {key: (key not in DISABLED_SET) for key in SERVERS.keys()}

# Heroku API Config (for updating DISABLED_SERVERS)
HEROKU_API_KEY = os.environ.get('HEROKU_API_KEY', '')
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME', 'fb-otp-bot-hema')

def update_disabled_servers_env():
    """Update DISABLED_SERVERS in Heroku config vars"""
    if not HEROKU_API_KEY:
        logger.warning("HEROKU_API_KEY not set, cannot persist server status")
        return False
    
    # Build new value
    disabled = [k for k, v in SERVER_STATUS.items() if not v]
    new_value = ','.join(disabled)
    
    try:
        url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars"
        headers = {
            "Authorization": f"Bearer {HEROKU_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.heroku+json; version=3"
        }
        data = {"DISABLED_SERVERS": new_value}
        
        resp = requests.patch(url, headers=headers, json=data)
        if resp.status_code == 200:
            logger.info(f"Updated DISABLED_SERVERS to: {new_value}")
            return True
        else:
            logger.error(f"Failed to update Heroku config: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error updating Heroku config: {e}")
        return False

def get_active_servers():
    """Return only active servers"""
    return {k: v for k, v in SERVERS.items() if SERVER_STATUS.get(k, True)}

# ... (omitted code) ...



def get_server_keyboard():
    """Return keyboard for server selection"""
    keyboard = []
    row = []
    for key, data in SERVERS.items():
        row.append(InlineKeyboardButton(f"🖥️ {data['name']}", callback_data=f"select_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_selection")])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """Return main menu keyboard"""
    keyboard = [
        [KeyboardButton("سيرفر 1"), KeyboardButton("سيرفر 2")],
        [KeyboardButton("سيرفر 3"), KeyboardButton("سيرفر 4")],
        [KeyboardButton("توزيع تلقائي (كل السيرفرات)")],
        [KeyboardButton("فحص السيرفرات 📡")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


import datetime
from dateutil import parser as date_parser

# ... imports ...

async def post_init(application: Application):
    """Set up bot commands menu"""
    await application.bot.set_my_commands([
        BotCommand("start", "القائمة الرئيسية"),
        BotCommand("servers", "إدارة السيرفرات"),

        BotCommand("status", "حالة العمليات"),
        BotCommand("cancel", "إيقاف الكل"),
        BotCommand("help", "المساعدة")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        await update.message.reply_text("❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    reply_keyboard = [
        ["/start", "/servers"],
        ["/check_servers", "/deploy_scripts"],
        ["/delete_server"],
        ["/cancel"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🤖 مرحباً بك في بوت FB OTP\n\n"
        "📱 لإرسال الأرقام:\n"
        "• أرسل ملف .txt يحتوي على الأرقام\n"
        "• أو اكتب الأرقام مباشرة\n\n"
        "⬇️ اختر من القائمة:",
        reply_markup=markup
    )
    # Also show inline keyboard
    await update.message.reply_text("التحكم السريع:", reply_markup=get_main_keyboard())

def get_server_keyboard():
    """Return keyboard for server selection (active servers only)"""
    active_servers = get_active_servers()
    keyboard = []
    
    # Add Auto Distribute Button at the top (only if 2+ active servers)
    if len(active_servers) >= 2:
        keyboard.append([InlineKeyboardButton("🚀 توزيع تلقائي", callback_data="select_auto")])
    
    row = []
    for key, data in active_servers.items():
        row.append(InlineKeyboardButton(f"🖥️ {data['repo']}", callback_data=f"select_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    if not active_servers:
        keyboard.append([InlineKeyboardButton("⚠️ لا سيرفرات نشطة", callback_data="no_servers")])
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_selection")])
    return InlineKeyboardMarkup(keyboard)

def get_server_management_keyboard():
    """Return keyboard for server management (toggle active/inactive)"""
    keyboard = []
    for key, data in SERVERS.items():
        status = "🟢" if SERVER_STATUS.get(key, True) else "🔴"
        btn_text = f"{status} {data['repo']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{key}")])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_delete_server_keyboard():
    """Return keyboard for server deletion"""
    keyboard = []
    
    # Don't allow deleting Server 1 (Main) easily via this if it holds the bot code?
    # Actually, env logic allows it, but let's be safe or just show all.
    for key, data in SERVERS.items():
        if key == 'server1': 
            # Skip server1 if it's the main repo to prevent suicide? 
            # User said "Delete ANY server", so we include it but label it.
            btn_text = f"🗑️ {data['repo']} (MAIN)"
        else:
            btn_text = f"🗑️ {data['repo']}"
            
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"delete_{key}")])
    
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_selection")])
    return InlineKeyboardMarkup(keyboard)

async def delete_server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show panel to delete a server"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    await update.message.reply_text("🗑️ **حذف سيرفر**\nاختر السيرفر لحذفه نهائياً من الإعدادات:", reply_markup=get_delete_server_keyboard(), parse_mode='Markdown')

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle server deletion"""
    query = update.callback_query
    await query.answer()
    
    server_key = query.data.replace("delete_", "")
    
    if server_key not in SERVERS:
        await query.edit_message_text("❌ السيرفر غير موجود.")
        return
        
    server_name = SERVERS[server_key]['repo']
    
    # Determine keys to unset
    keys_to_unset = {}
    if server_key == 'server1':
        # Main server uses GITHUB_REPO etc.
        keys_to_unset = {"GITHUB_REPO": None, "GITHUB_TOKEN": None, "GITHUB_BRANCH": None}
    else:
        # Dynamic servers use SERVER_i_REPO
        index = server_key.replace("server", "")
        keys_to_unset = {
            f"SERVER_{index}_REPO": None, 
            f"SERVER_{index}_TOKEN": None, 
            f"SERVER_{index}_NAME": None, 
            f"SERVER_{index}_BRANCH": None
        }
    
    await query.edit_message_text(f"⏳ جاري حذف {server_name} وإعادة تشغيل البوت...")
    
    # Call Heroku API
    success = update_heroku_config(keys_to_unset)
    
    if success:
        await context.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=f"✅ تم حذف {server_name} بنجاح.\nسيتم إعادة التشغيل خلال لحظات... 🔄")
    else:
        await context.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=f"❌ فشل حذف {server_name}. تأكد من HEROKU_API_KEY.")

def update_heroku_config(config_dict):
    """Update (or unset) Heroku config vars"""
    if not HEROKU_API_KEY:
        return False
        
    try:
        url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars"
        headers = {
            "Authorization": f"Bearer {HEROKU_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.heroku+json; version=3"
        }
        
        resp = requests.patch(url, headers=headers, json=config_dict)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Error updating Heroku: {e}")
        return False

async def show_server_management(query):
    """Show server management panel"""
    active_count = sum(1 for s in SERVER_STATUS.values() if s)
    total_count = len(SERVERS)
    
    msg = f"""⚙️ إدارة السيرفرات

🟢 = نشط (يستخدم في التوزيع)
🔴 = متوقف (لا يُستخدم)

السيرفرات النشطة: {active_count}/{total_count}

اضغط على سيرفر لتغيير حالته:"""
    
    await query.edit_message_text(msg, reply_markup=get_server_management_keyboard())

async def servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /servers command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    active_count = sum(1 for s in SERVER_STATUS.values() if s)
    total_count = len(SERVERS)
    
    msg = f"""⚙️ إدارة السيرفرات

🟢 = نشط (يستخدم في التوزيع)
🔴 = متوقف (لا يُستخدم)

السيرفرات النشطة: {active_count}/{total_count}

اضغط على سيرفر لتغيير حالته:"""
    
    await update.message.reply_text(msg, reply_markup=get_server_management_keyboard())



async def handle_server_selection(query, context, server_key):
    """Execute dispatch using the selected server"""
    if 'pending_numbers' not in context.user_data:
        await query.edit_message_text("❌ حدث خطأ: لا توجد أرقام محفوظة. أرسل الملف مرة أخرى.", reply_markup=get_main_keyboard())
        return
        
    numbers = context.user_data['pending_numbers']
    batch_size = 5
    
    # --- AUTO DISTRIBUTE LOGIC ---
    if server_key == "auto":
        active_servers = get_active_servers()  # FIX: Use active servers only
        total_servers = len(active_servers)
        if total_servers == 0:
             await query.edit_message_text("❌ لا توجد سيرفرات نشطة! اذهب لـ /servers لتفعيل سيرفر.", reply_markup=get_main_keyboard())
             return

        # Clear data
        del context.user_data['pending_numbers']
        
        await query.edit_message_text(
            f"🚀 **توزيع الحمل الذكي (Auto Distribute)**\n"
            f"📊 الأرقام: {len(numbers)}\n"
            f"🖥️ السيرفرات النشطة: {total_servers}\n"
            f"⚙️ جاري التوزيع...",
            parse_mode='Markdown'
        )
        
        server_keys = list(active_servers.keys())  # FIX: Use active server keys
        total_batches = (len(numbers) + batch_size - 1) // batch_size
        success_count = 0
        
        for i in range(0, len(numbers), batch_size):
            batch = numbers[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            # Round Robin Selection
            current_server_key = server_keys[(batch_num - 1) % total_servers]
            current_server = active_servers[current_server_key]  # FIX: Use active_servers
            
            # Trigger
            status_code = trigger_github_workflow(batch, current_server['repo'], current_server['token'], current_server.get('branch', 'master'))
            if status_code == 204:
                success_count += 1
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ {current_server['name']} | دفعة {batch_num}/{total_batches}"
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"❌ {current_server['name']} | فشل دفعة {batch_num} (Status: {status_code})"
                )
        
        return
    # -----------------------------

    server = SERVERS.get(server_key)
    if not server:
        await query.edit_message_text("❌ هذا السيرفر غير موجود", reply_markup=get_main_keyboard())
        return
        
    # Clear data
    del context.user_data['pending_numbers']
    
    await query.edit_message_text(
        f"✅ تم اختيار: {server['name']}\n"
        f"⚙️ جاري معالجة {len(numbers)} رقم...\n"
        f"🚀 الإرسال بنظام الدفعات (5 أرقام)..."
    )
    
    total_batches = (len(numbers) + batch_size - 1) // batch_size
    
    success_count = 0
    for i in range(0, len(numbers), batch_size):
        batch = numbers[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        # Trigger with specific server creds
        status_code = trigger_github_workflow(batch, server['repo'], server['token'], server.get('branch', 'master'))
        if status_code == 204:
            success_count += 1
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ {server['name']} | دفعة {batch_num}/{total_batches} ({len(batch)} أرقام)"
            )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ {server['name']} | فشل دفعة {batch_num} (Status: {status_code})"
            )
            
    return



async def show_progress(query):
    """Show progress of current running workflow"""
    try:
        headers = {
            "Authorization": f"Bearer {SERVERS['server1']['token']}", # Default to main server for checking
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Check for running workflows
        running_found = False
        for status in ["in_progress", "queued", "waiting"]:
            url = f"https://api.github.com/repos/{SERVERS['server1']['repo']}/actions/runs?status={status}&per_page=1"
            response = requests.get(url, headers=headers)
            runs = response.json().get('workflow_runs', [])
            
            if runs:
                run = runs[0]
                running_found = True
                
                # Get workflow start time
                created = run['created_at'][:16].replace('T', ' ')
                run_id = run['id']
                
                # Try to get jobs info for progress
                jobs_url = f"https://api.github.com/repos/{SERVERS['server1']['repo']}/actions/runs/{run_id}/jobs"
                jobs_response = requests.get(jobs_url, headers=headers)
                jobs_data = jobs_response.json().get('jobs', [])
                
                # Build progress message
                if status == "queued":
                    status_text = "📥 في قائمة الانتظار"
                    progress_bar = "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
                elif status == "waiting":
                    status_text = "⏳ منتظر"
                    progress_bar = "🟨⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%"
                else:
                    status_text = "🔄 قيد التنفيذ"
                    # Estimate progress based on steps
                    if jobs_data:
                        job = jobs_data[0]
                        steps = job.get('steps', [])
                        completed = sum(1 for s in steps if s.get('status') == 'completed')
                        total = len(steps) if steps else 1
                        percent = int((completed / total) * 100)
                        filled = percent // 10
                        progress_bar = "🟩" * filled + "⬜" * (10 - filled) + f" {percent}%"
                    else:
                        progress_bar = "🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜ ~30%"
                
                msg = f"""🔄 تقدم العملية الحالية

{status_text}
📅 بدأت: {created}
🆔 ID: {run_id}

{progress_bar}

اضغط 🔄 للتحديث"""
                
                await query.edit_message_text(msg, reply_markup=get_main_keyboard())
                return
        
        if not running_found:
            await query.edit_message_text(
                "📭 لا توجد عمليات جارية حالياً\n\n"
                "أرسل أرقام لبدء عملية جديدة!",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ: {e}", reply_markup=get_main_keyboard())


async def show_status(query):
    """Show GitHub Actions status"""
    try:
        url = f"https://api.github.com/repos/{SERVERS['server1']['repo']}/actions/runs?per_page=5"
        headers = {
            "Authorization": f"Bearer {SERVERS['server1']['token']}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        runs = response.json().get('workflow_runs', [])
        
        if not runs:
            await query.edit_message_text("📭 لا توجد عمليات سابقة", reply_markup=get_main_keyboard())
            return
        
        status_msg = "📊 آخر 5 عمليات:\n\n"
        for run in runs[:5]:
            status_emoji = "✅" if run['conclusion'] == 'success' else "❌" if run['conclusion'] == 'failure' else "⏳"
            status_msg += f"{status_emoji} {run['created_at'][:16].replace('T', ' ')} - {run['status']}\n"
        
        await query.edit_message_text(status_msg, reply_markup=get_main_keyboard())
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ: {e}", reply_markup=get_main_keyboard())


async def cancel_all_workflows(query):
    """Cancel all running and queued workflows"""
    try:
        total_cancelled = 0
        total_checked = 0
        
        # Iterate through all configured servers
        for key, server in SERVERS.items():
            if not server['token']: continue
            
            headers = {
                "Authorization": f"Bearer {server['token']}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get workflows
            server_runs = []
            for status in ["in_progress", "queued", "waiting"]:
                url = f"https://api.github.com/repos/{server['repo']}/actions/runs?status={status}"
                try:
                    response = requests.get(url, headers=headers)
                    runs = response.json().get('workflow_runs', [])
                    server_runs.extend(runs)
                except: pass
            
            total_checked += len(server_runs)
            
            # Cancel each
            for run in server_runs:
                try:
                    cancel_url = f"https://api.github.com/repos/{server['repo']}/actions/runs/{run['id']}/cancel"
                    cancel_response = requests.post(cancel_url, headers=headers)
                    if cancel_response.status_code == 202:
                        total_cancelled += 1
                except: pass
        
        if total_checked == 0:
            await query.edit_message_text("📭 لا توجد عمليات جارية أو منتظرة للإيقاف", reply_markup=get_main_keyboard())
            return
            
        await query.edit_message_text(
            f"🛑 تم إيقاف {total_cancelled} عمليات من أصل {total_checked}",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ: {e}", reply_markup=get_main_keyboard())


async def show_help(query):
    """Show help message"""
    help_text = """❓ المساعدة

📱 لإرسال الأرقام:
• أرسل ملف .txt يحتوي على الأرقام
• أو اكتب الأرقام مباشرة (كل رقم في سطر)

📊 حالة العمليات:
يعرض آخر 5 عمليات

🛑 إيقاف الكل:
يوقف جميع العمليات الجارية

📋 الأوامر:
/start - القائمة الرئيسية
/status - حالة العمليات
/cancel - إيقاف الكل"""
    
    await query.edit_message_text(help_text, reply_markup=get_main_keyboard())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    await show_status(update.message)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    await cancel_all_workflows(update.message)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("select_"):
        await handle_server_selection(query, context, data.split("_")[1])
    elif data.startswith("toggle_"):
        # Toggle server status
        server_key = data.replace("toggle_", "")
        if server_key in SERVER_STATUS:
            SERVER_STATUS[server_key] = not SERVER_STATUS[server_key]
            status_text = "🟢 نشط" if SERVER_STATUS[server_key] else "🔴 متوقف"
            
            # Persist to Heroku env var
            persisted = update_disabled_servers_env()
            persist_icon = "💾" if persisted else "⚠️"
            
            await query.answer(f"{persist_icon} {SERVERS[server_key]['name']}: {status_text}")
        await show_server_management(query)
    elif data == "manage_servers":
        await show_server_management(query)

    elif data == "no_servers":
        await query.answer("اذهب لـ /servers لتفعيل سيرفرات")
    elif data == "back_to_main":
        await query.edit_message_text("التحكم السريع:", reply_markup=get_main_keyboard())
    elif data == "cancel_selection":
        if 'pending_numbers' in context.user_data:
            del context.user_data['pending_numbers']
        await query.edit_message_text("❌ تم إلغاء العملية", reply_markup=get_main_keyboard())
    elif data == "progress":
        await show_progress(query)
    elif data == "status":
        await show_status(query)
    elif data == "cancel":
        await cancel_all_workflows(query)
    elif data == "help":
        await show_help(query)
    elif query.data.startswith("delete_"):
        await handle_delete_callback(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received document - Step 1: Store and Ask for Server"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ يرجى إرسال ملف .txt فقط")
        return
    
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    numbers_text = file_content.decode('utf-8')
    
    numbers = [line.strip() for line in numbers_text.split('\n') if line.strip() and not line.startswith('#')]
    
    if not numbers:
        await update.message.reply_text("❌ الملف فارغ")
        return
    
    # Store numbers in context
    context.user_data['pending_numbers'] = numbers
    
    await update.message.reply_text(
        f"✅ تم استلام {len(numbers)} رقم\n"
        f"📡 الرجاء اختيار السيرفر للتنفيذ:",
        reply_markup=get_server_keyboard()
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text - Step 1: Store and Ask for Server"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    text = update.message.text
    if text.startswith('/'): return
    
    # Check for menu buttons
    if text == "فحص السيرفرات 📡":
        await check_servers_command(update, context)
        return
        
    numbers = [line.strip() for line in text.split('\n') if line.strip()]
    if not numbers: return
    
    # Store numbers in context
    context.user_data['pending_numbers'] = numbers
    
    await update.message.reply_text(
        f"✅ تم استلام {len(numbers)} رقم\n"
        f"📡 الرجاء اختيار السيرفر للتنفيذ:",
        reply_markup=get_server_keyboard()
    )


def trigger_github_workflow(numbers: list, repo: str, token: str, branch: str = 'master', extra_inputs: dict = None) -> int:
    """Trigger GitHub Actions workflow with dynamic credentials
       Returns: 200/204 (Success), or Error Status Code
    """
    try:
        url = f"https://api.github.com/repos/{repo}/actions/workflows/fb_otp.yml/dispatches"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        inputs = {"numbers": "\n".join(numbers)}
        if extra_inputs:
            inputs.update(extra_inputs)
            
        data = {
            "ref": branch,
            "inputs": inputs
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        # GitHub API returns 204 (No Content) on success
        if response.status_code in [200, 204]:
            logger.info(f"Workflow triggered for {repo}: Status={response.status_code}")
            return 204
        else:
            # Log detailed error info
            logger.error(f"GitHub API Error for {repo}: Status={response.status_code}, Body={response.text[:200]}")
            return response.status_code
            
    except Exception as e:
        logger.error(f"Error triggering workflow: {e}")
        return 500

async def check_servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check status of all servers by triggering a ping workflow and verifying execution"""
    logger.info("Starting checks...")
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

async def check_servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check status of all servers by triggering a ping workflow and verifying execution"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    status_msg = await update.message.reply_text("📡 جاري فحص حالة السيرفرات...\n(يقوم بإرسال طلبات وانتظار الاستجابة)")
    
    results = {}
    triggered_servers = []
    
    # 0. Initialize all as Waiting
    for key in SERVERS.keys():
        results[key] = f"⏳ {SERVERS[key]['repo']}: جاري الاتصال..."

    # 1. Trigger Phase
    for key, server in SERVERS.items():
        if not server['token']:
            results[key] = f"⚠️ {server['name']}: لا يوجد توكن"
            continue
            
        branch = server.get('branch', 'master')
        status_code = trigger_github_workflow([], server['repo'], server['token'], branch, extra_inputs={'mode': 'ping'})
        
        if status_code == 204:
            results[key] = f"⏳ {server['repo']}: تم الإرسال (منتظر التحقق...)"
            triggered_servers.append(key)
        elif status_code == 403:
             results[key] = f"❌ {server['repo']}: الحساب محظور (Account Banned - 403)"
        elif status_code == 422:
             results[key] = f"⚠️ {server['repo']}: يحتاج تحديث كود (422) - استخدم /deploy_scripts"
        elif status_code == 401:
             results[key] = f"❌ {server['repo']}: التوكن غير صحيح (401)"
        else:
             results[key] = f"⚠️ {server['repo']}: خطأ غير معروف ({status_code})"
    
    # Update message with initial status
    initial_report = "📊 جاري فحص السيرفرات (انتظار 20 ثانية)...\n\n"
    sorted_keys = sorted(SERVERS.keys(), key=lambda x: int(x.replace('server', '')) if x.replace('server', '').isdigit() else 999)
    
    for key in sorted_keys:
        initial_report += f"{results.get(key, 'Unknown')}\n"
        
    await status_msg.edit_text(initial_report)
    
    # 2. Wait Phase
    await asyncio.sleep(20)
    
    # 3. Verification Phase (Check for recent runs)
    for key in triggered_servers:
        server = SERVERS[key]
        try:
            # Check for runs created in the last minute
            url = f"https://api.github.com/repos/{server['repo']}/actions/runs"
            headers = {
                "Authorization": f"Bearer {server['token']}",
                "Accept": "application/vnd.github.v3+json"
            }
            # Look specifically for 'workflow_dispatch' event in last minute
            params = {
                "event": "workflow_dispatch",
                "per_page": 5
            }
            
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                runs = resp.json().get('workflow_runs', [])
                logger.info(f"Verification for {key}: Found {len(runs)} runs")
                
                # Check if any run is recent (created < 2 min ago) and active/success
                is_online = False
                for run in runs:
                    created_at = datetime.datetime.strptime(run['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                    delta = (datetime.datetime.utcnow() - created_at).total_seconds()
                    
                    if delta < 120:
                        logger.info(f"  > Run {run['id']} recent ({delta}s ago) status: {run['status']}")
                        if run['status'] in ['queued', 'in_progress', 'completed']:
                            is_online = True
                            break
                
                if is_online:
                     results[key] = f"✅ {server['repo']}: متصل ويعمل (تم التحقق)"
                else:
                     logger.warning(f"  > No recent online run found for {key}")
                     results[key] = f"❌ {server['repo']}: رصيد منتهي (Credit Expired) - لم يبدأ العمل"
            else:
                 logger.error(f"Verification failed for {key}: Status {resp.status_code}")
                 results[key] = f"⚠️ {server['repo']}: تعذر التحقق من الحالة ({resp.status_code})"
        except Exception as e:
            logger.error(f"Error verifying {key}: {e}")
            results[key] = f"⚠️ {server['repo']}: خطأ أثناء التحقق ({str(e)})"
            
    logger.info("Checks finished. Generating report.")

    # Final Report - Categorized
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    
    active = []
    expired = []
    banned = []
    issues = []
    waiting = []
    
    for key in sorted_keys:
        msg = results.get(key, 'Unknown')
        if "✅" in msg: active.append(msg)
        elif "رصيد منتهي" in msg: expired.append(msg)
        elif "محظور" in msg: banned.append(msg)
        elif "⏳" in msg: waiting.append(msg)
        else: issues.append(msg)
        
    final_report = f"📊 **تقرير حالة السيرفرات (Server Health)** - {timestamp}\n"
    
    if active:
        final_report += "\n🚀 **سيرفرات تعمل (Active):**\n" + "\n".join(active) + "\n"
        
    if expired:
        final_report += "\n🛑 **رصيد منتهي (Credit Expired):**\n" + "\n".join(expired) + "\n"
        
    if banned:
        final_report += "\n🚫 **حسابات محظورة (Banned):**\n" + "\n".join(banned) + "\n"
        
    if issues or waiting:
        final_report += "\n⚠️ **مشاكل / أخرى:**\n" + "\n".join(issues + waiting) + "\n"

    final_report += "\n💡 تحديث: الدقائق تتجدد يوم 1 في الشهر."
    await status_msg.edit_text(final_report, parse_mode='Markdown')


# --- DEPLOYMENT HELPERS ---
import base64

async def update_github_file(repo: str, token: str, file_path: str, content: str, branch: str = 'master') -> bool:
    """Update a file in a GitHub repository via API (Async wrapper)"""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    loop = asyncio.get_running_loop()

    def _sync_request():
        # 1. Get current file SHA (if exists)
        params = {"ref": branch}
        sha = None
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                sha = resp.json().get('sha')
            elif resp.status_code == 404:
                pass # Create new
            else:
                logger.error(f"Error getting file info for {repo}/{file_path} (ref={branch}): {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Exception getting file info: {e}")
            return False

        # 2. Update/Create file
        try:
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            data = {
                "message": "Auto-deploy: Update script via Bot",
                "content": encoded_content,
                "branch": branch 
            }
            if sha:
                data["sha"] = sha
                
            put_resp = requests.put(url, headers=headers, json=data)
            if put_resp.status_code in [200, 201]:
                return True
            else:
                logger.error(f"Error updating file {repo}/{file_path}: {put_resp.status_code} {put_resp.text}")
                return False
        except Exception as e:
            logger.error(f"Exception updating file: {e}")
            return False

    return await loop.run_in_executor(None, _sync_request)

async def deploy_scripts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deploy local files to all active servers"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    status_msg = await update.message.reply_text("🚀 جاري نشر التحديثات على السيرفرات...")
    
    # Read local files
    files_to_deploy = {
        "fb_otp_browser.py": "fb_otp_browser.py",
        ".github/workflows/fb_otp.yml": ".github/workflows/fb_otp.yml",
        "requirements.txt": "requirements.txt"
    }
    
    file_contents = {}
    try:
        for local_path, remote_path in files_to_deploy.items():
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    file_contents[remote_path] = f.read()
            else:
                 logger.warning(f"Local file not found for deployment: {local_path}")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ في قراءة الملفات المحلية: {e}")
        return

    if not file_contents:
        await status_msg.edit_text("❌ لم يتم العثور على ملفات لنشرها.")
        return

    results = []
    for key, server in SERVERS.items():
        # Skip if token is missing
        if not server['token']:
            results.append(f"⚠️ {server['name']}: لا يوجد توكن")
            continue
            
        # Use configured branch, default to master
        branch = server.get('branch', 'master')
        
        # Deploy all files
        files_success = []
        for remote_path, content in file_contents.items():
            success = await update_github_file(server['repo'], server['token'], remote_path, content, branch)
            files_success.append(success)
        
        # All files must succeed
        all_success = all(files_success)
        icon = "✅" if all_success else "❌"
        results.append(f"{icon} {server['name']} ({sum(files_success)}/{len(files_success)} files)")
        
    report = "📊 **تقرير النشر (Deploy Report)**:\n\n" + "\n".join(results)
    report += "\n\n📦 الملفات المنشورة:\n• fb_otp_browser.py\n• .github/workflows/fb_otp.yml\n• requirements.txt"
    await status_msg.edit_text(report)





def main():
    """Start the bot"""
    logger.info("Starting Telegram Bot...")
    
    # Build application
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("servers", servers_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("check_servers", check_servers_command))
    application.add_handler(CommandHandler("deploy_scripts", deploy_scripts_command))
    application.add_handler(CommandHandler("delete_server", delete_server_command))


    
    # Button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
