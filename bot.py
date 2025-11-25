import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from PIL import Image
import io
import schedule
import threading
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ==================== TRANSLATIONS ====================

TRANSLATIONS = {
    'en': {
        'welcome': (
            "🎯 *Welcome to Your Ultimate Productivity Assistant!*\n\n"
            "I'll help you:\n"
            "✅ Manage daily tasks with categories\n"
            "🔁 Set recurring tasks\n"
            "⏰ Send smart reminders\n"
            "🍅 Pomodoro timer for focus\n"
            "📊 Track goals & habits with streaks\n"
            "🏆 Earn points & achievements\n"
            "👥 Team accountability\n"
            "📈 Generate beautiful PDF reports\n\n"
            "🌍 Language set to: English\n"
            "Change anytime with /language\n\n"
            "Let's set up your account!\n\n"
            "Enter your *3 MAJOR GOALS* for this month (one per line):"
        ),
        'goals_set': "✅ *Goals Set!*\n",
        'habits_prompt': "\n\n🎯 Now, what *HABITS* do you want to build?\n(One per line, e.g., 'Drink 8 glasses of water', 'Exercise 30min')",
        'habits_tracking': "🎯 *Perfect! Tracking {count} habits*\n\n",
        'setup_complete': (
            "Setup complete! Here's what you can do:\n\n"
            "*Commands:*\n"
            "✏️ /add - Add tasks manually\n"
            "✅ /habits - Check off habits\n"
            "🍅 /pomodoro - Focus timer\n"
            "📊 /status - Today's progress\n"
            "🎯 /goals - Update goals\n"
            "👥 /team - Team features\n"
            "📈 /report - View reports\n"
            "📄 /export - Export PDF\n"
            "🌍 /language - Change language"
        ),
        'add_tasks': "✏️ *Enter your tasks* (one per line)\n\nExample:\nBuy groceries\nFinish report\nCall dentist",
        'got_tasks': "📋 *Got {count} tasks!*\n\n🏷️ Task 1: {task}\n\nSelect category:",
        'recurring_prompt': "🔁 Is this a *recurring* task?\n\nTask: {task}",
        'time_prompt': "⏰ *Task:* {task}\n\nEnter time:\n• HH:MM format (e.g., 14:30)\n• Or duration in minutes (e.g., 30)",
        'next_task': "🏷️ *Task {num}:* {task}\n\nSelect category:",
        'all_set': "✅ *All set!*\n\n{summary}\n\n🎉 +{points} points earned!\nI'll remind you at scheduled times! 🔔",
        'pomodoro_title': "🍅 *Pomodoro Timer*\n\nCompleted today: {count} pomodoros\n\nWork: {work}min | Break: {break_time}min | Long: {long_break}min",
        'work_started': "🍅 *Work session started!*\n\nFocus for {duration} minutes.\nI'll notify you when it's done!",
        'break_time': "☕ *Break time!*\n\nRelax for {duration} minutes.",
        'long_break': "🌙 *Long break!*\n\nRecharge for {duration} minutes.",
        'work_complete': "🎉 *Work session complete!*\n\nGreat focus! Take a break now. 🍵",
        'break_over': "⏰ *Break's over!*\n\nReady for another work session? 🍅",
        'daily_habits': "📊 *Daily Habits*\n\n",
        'tap_to_check': "Tap to check off:",
        'all_done_habits': "🎉 All habits done today!",
        'habit_checked': "✅ *{habit}* checked!\n\n🔥 Streak: {streak} days\n🎉 +{points} points",
        'milestone': "\n\n🎊 *MILESTONE!* {streak} day streak!",
        'status_title': "📊 *Today's Progress*\n\n",
        'status_tasks': "✅ Tasks: {completed}/{total}\n",
        'status_habits': "🎯 Habits: {done}/{total}\n",
        'status_pomodoros': "🍅 Pomodoros: {count}\n",
        'status_points': "⭐ Total Points: {points}\n\n",
        'great_day': "🎉 Great day!",
        'keep_going': "💪 Keep going!",
        'generating_pdf': "📄 Generating PDF report...",
        'help_title': "📚 *Command Reference*\n\n",
        'help_getting_started': "*Getting Started:*\n/start - Setup goals & habits\n/language - Change language\n\n",
        'help_daily': "*Daily Use:*\n/add - Add new tasks\n/habits - Check off habits\n/pomodoro - Focus timer\n/status - Today's progress\n\n",
        'help_management': "*Management:*\n/goals - Update goals\n/team - Team features\n\n",
        'help_reports': "*Reports:*\n/report - View reports\n/export - Download PDF\n\n",
        'help_tip': "💡 Tip: Use quick reply buttons for faster access!",
        'no_habits': "No habits set. Use /start to set up.",
        'all_done': "✨ All Done!",
        'skip_categories': "⏭️ Skip Categories",
        'daily': "📅 Daily",
        'weekly': "📆 Weekly",
        'one_time': "⏭️ One-time only",
        'work': "Work",
        'personal': "Personal",
        'health': "Health",
        'start_work': "🍅 Start Work (25min)",
        'short_break': "☕ Short Break (5min)",
        'long_break_btn': "🌙 Long Break (15min)",
        'add_tasks_btn': "📋 Add Tasks",
        'check_habits_btn': "✅ Check Habits",
        'pomodoro_btn': "🍅 Pomodoro",
        'status_btn': "📊 Status",
        'help_btn': "❓ Help",
        'select_language': "🌍 *Select Your Language / اختر لغتك*",
        'language_changed': "✅ Language changed to English!",
    },
    'ar': {
        'welcome': (
            "🎯 *مرحباً بك في مساعدك الإنتاجي المتكامل!*\n\n"
            "سأساعدك في:\n"
            "✅ إدارة المهام اليومية مع التصنيفات\n"
            "🔁 تعيين المهام المتكررة\n"
            "⏰ إرسال التذكيرات الذكية\n"
            "🍅 مؤقت بومودورو للتركيز\n"
            "📊 تتبع الأهداف والعادات مع السلاسل\n"
            "🏆 اكسب النقاط والإنجازات\n"
            "👥 المساءلة الجماعية\n"
            "📈 إنشاء تقارير PDF جميلة\n\n"
            "🌍 اللغة المحددة: العربية\n"
            "غير اللغة في أي وقت باستخدام /language\n\n"
            "لنبدأ بإعداد حسابك!\n\n"
            "أدخل *3 أهداف رئيسية* لهذا الشهر (هدف في كل سطر):"
        ),
        'goals_set': "✅ *تم تعيين الأهداف!*\n",
        'habits_prompt': "\n\n🎯 الآن، ما هي *العادات* التي تريد بناءها؟\n(واحدة في كل سطر، مثل: 'شرب 8 أكواب ماء'، 'التمرين 30 دقيقة')",
        'habits_tracking': "🎯 *ممتاز! تتبع {count} عادة*\n\n",
        'setup_complete': (
            "اكتمل الإعداد! إليك ما يمكنك فعله:\n\n"
            "*الأوامر:*\n"
            "✏️ /add - إضافة مهام يدوياً\n"
            "✅ /habits - تحديد العادات\n"
            "🍅 /pomodoro - مؤقت التركيز\n"
            "📊 /status - تقدم اليوم\n"
            "🎯 /goals - تحديث الأهداف\n"
            "👥 /team - ميزات الفريق\n"
            "📈 /report - عرض التقارير\n"
            "📄 /export - تصدير PDF\n"
            "🌍 /language - تغيير اللغة"
        ),
        'add_tasks': "✏️ *أدخل مهامك* (مهمة في كل سطر)\n\nمثال:\nشراء البقالة\nإنهاء التقرير\nالاتصال بالطبيب",
        'got_tasks': "📋 *تم الحصول على {count} مهمة!*\n\n🏷️ المهمة 1: {task}\n\nاختر التصنيف:",
        'recurring_prompt': "🔁 هل هذه مهمة *متكررة*؟\n\nالمهمة: {task}",
        'time_prompt': "⏰ *المهمة:* {task}\n\nأدخل الوقت:\n• صيغة HH:MM (مثل 14:30)\n• أو المدة بالدقائق (مثل 30)",
        'next_task': "🏷️ *المهمة {num}:* {task}\n\nاختر التصنيف:",
        'all_set': "✅ *تم الإعداد!*\n\n{summary}\n\n🎉 +{points} نقطة مكتسبة!\nسأذكرك في الأوقات المحددة! 🔔",
        'pomodoro_title': "🍅 *مؤقت بومودورو*\n\nتم إكماله اليوم: {count} بومودورو\n\nعمل: {work} دقيقة | استراحة: {break_time} دقيقة | استراحة طويلة: {long_break} دقيقة",
        'work_started': "🍅 *بدأت جلسة العمل!*\n\nركز لمدة {duration} دقيقة.\nسأخبرك عند انتهائها!",
        'break_time': "☕ *وقت الاستراحة!*\n\nاسترخ لمدة {duration} دقيقة.",
        'long_break': "🌙 *استراحة طويلة!*\n\nأعد شحن طاقتك لمدة {duration} دقيقة.",
        'work_complete': "🎉 *اكتملت جلسة العمل!*\n\nتركيز رائع! خذ استراحة الآن. 🍵",
        'break_over': "⏰ *انتهت الاستراحة!*\n\nهل أنت مستعد لجلسة عمل أخرى؟ 🍅",
        'daily_habits': "📊 *العادات اليومية*\n\n",
        'tap_to_check': "انقر للتحديد:",
        'all_done_habits': "🎉 تم إنجاز جميع العادات اليوم!",
        'habit_checked': "✅ *{habit}* تم التحديد!\n\n🔥 السلسلة: {streak} يوم\n🎉 +{points} نقطة",
        'milestone': "\n\n🎊 *إنجاز!* سلسلة {streak} يوم!",
        'status_title': "📊 *تقدم اليوم*\n\n",
        'status_tasks': "✅ المهام: {completed}/{total}\n",
        'status_habits': "🎯 العادات: {done}/{total}\n",
        'status_pomodoros': "🍅 بومودورو: {count}\n",
        'status_points': "⭐ إجمالي النقاط: {points}\n\n",
        'great_day': "🎉 يوم رائع!",
        'keep_going': "💪 استمر!",
        'generating_pdf': "📄 جاري إنشاء تقرير PDF...",
        'help_title': "📚 *مرجع الأوامر*\n\n",
        'help_getting_started': "*البداية:*\n/start - إعداد الأهداف والعادات\n/language - تغيير اللغة\n\n",
        'help_daily': "*الاستخدام اليومي:*\n/add - إضافة مهام جديدة\n/habits - تحديد العادات\n/pomodoro - مؤقت التركيز\n/status - تقدم اليوم\n\n",
        'help_management': "*الإدارة:*\n/goals - تحديث الأهداف\n/team - ميزات الفريق\n\n",
        'help_reports': "*التقارير:*\n/report - عرض التقارير\n/export - تنزيل PDF\n\n",
        'help_tip': "💡 نصيحة: استخدم أزرار الرد السريع للوصول الأسرع!",
        'no_habits': "لم يتم تعيين عادات. استخدم /start للإعداد.",
        'all_done': "✨ تم الكل!",
        'skip_categories': "⏭️ تخطي التصنيفات",
        'daily': "📅 يومي",
        'weekly': "📆 أسبوعي",
        'one_time': "⏭️ مرة واحدة فقط",
        'work': "عمل",
        'personal': "شخصي",
        'health': "صحة",
        'start_work': "🍅 بدء العمل (25 دقيقة)",
        'short_break': "☕ استراحة قصيرة (5 دقائق)",
        'long_break_btn': "🌙 استراحة طويلة (15 دقيقة)",
        'add_tasks_btn': "📋 إضافة مهام",
        'check_habits_btn': "✅ تحديد العادات",
        'pomodoro_btn': "🍅 بومودورو",
        'status_btn': "📊 الحالة",
        'help_btn': "❓ مساعدة",
        'select_language': "🌍 *اختر لغتك / Select Your Language*",
        'language_changed': "✅ تم تغيير اللغة إلى العربية!",
    }
}

# Database class
class ProductivityDB:
    def __init__(self):
        self.users = {}
        self.teams = {}
    
    def get_user(self, user_id):
        if user_id not in self.users:
            self.users[user_id] = {
                'language': 'en',  # Default language
                'monthly_goals': [],
                'habits': [],
                'habit_streaks': {},
                'tasks': [],
                'recurring_tasks': [],
                'completed_tasks': [],
                'categories': ['Work', 'Personal', 'Health'],
                'pomodoro_settings': {'work': 25, 'break': 5, 'long_break': 15},
                'pomodoro_count': 0,
                'weekly_reports': [],
                'monthly_reports': [],
                'annual_reports': [],
                'team_id': None,
                'points': 0,
                'achievements': []
            }
        return self.users[user_id]
    
    def save_user(self, user_id, data):
        self.users[user_id] = data
    
    def get_team(self, team_id):
        return self.teams.get(team_id, {'members': [], 'shared_goals': []})
    
    def save_team(self, team_id, data):
        self.teams[team_id] = data

db = ProductivityDB()

# Conversation states
(LANGUAGE_SELECT, GOALS_INPUT, HABITS_INPUT, TASK_INPUT, TASK_CONFIRM, 
 CATEGORY_SELECT, RECURRING_SELECT, TIME_ALLOCATION) = range(8)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== HELPER FUNCTIONS ====================

def get_text(user_id, key, **kwargs):
    """Get translated text for user's language"""
    user_data = db.get_user(user_id)
    lang = user_data.get('language', 'en')
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS['en'][key])
    if kwargs:
        text = text.format(**kwargs)
    return text

def get_category_name(user_id, category):
    """Get translated category name"""
    lang = db.get_user(user_id).get('language', 'en')
    categories = {
        'Work': TRANSLATIONS[lang]['work'],
        'Personal': TRANSLATIONS[lang]['personal'],
        'Health': TRANSLATIONS[lang]['health']
    }
    return categories.get(category, category)

# ==================== LANGUAGE SELECTION ====================

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ]
    
    await update.message.reply_text(
        "🌍 *Select Your Language / اختر لغتك*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if query.data == "lang_en":
        user_data['language'] = 'en'
        user_data['categories'] = ['Work', 'Personal', 'Health']
        msg = "✅ Language changed to English!"
    else:
        user_data['language'] = 'ar'
        user_data['categories'] = ['عمل', 'شخصي', 'صحة']
        msg = "✅ تم تغيير اللغة إلى العربية!"
    
    db.save_user(user_id, user_data)
    await query.edit_message_text(msg)

# ==================== SETUP & ONBOARDING ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # First time users - select language
    user_data = db.get_user(user_id)
    if not user_data.get('language'):
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en_start")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar_start")]
        ]
        
        await update.message.reply_text(
            "🌍 *Select Your Language / اختر لغتك*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return LANGUAGE_SELECT
    
    welcome_text = get_text(user_id, 'welcome')
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    return GOALS_INPUT

async def language_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if 'en' in query.data:
        user_data['language'] = 'en'
        user_data['categories'] = ['Work', 'Personal', 'Health']
    else:
        user_data['language'] = 'ar'
        user_data['categories'] = ['عمل', 'شخصي', 'صحة']
    
    db.save_user(user_id, user_data)
    
    welcome_text = get_text(user_id, 'welcome')
    await query.edit_message_text(welcome_text, parse_mode='Markdown')
    return GOALS_INPUT

async def receive_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    goals_text = update.message.text
    goals = [g.strip() for g in goals_text.split('\n') if g.strip()]
    
    user_data = db.get_user(user_id)
    user_data['monthly_goals'] = [
        {
            'goal': g, 
            'created': datetime.now().isoformat(), 
            'progress': 0,
            'milestones': []
        }
        for g in goals[:3]
    ]
    db.save_user(user_id, user_data)
    
    goals_text = get_text(user_id, 'goals_set') + "\n".join([f"{i+1}. {g}" for i, g in enumerate(goals[:3])])
    habits_prompt = get_text(user_id, 'habits_prompt')
    
    await update.message.reply_text(
        goals_text + habits_prompt,
        parse_mode='Markdown'
    )
    return HABITS_INPUT

async def receive_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits_text = update.message.text
    habits = [h.strip() for h in habits_text.split('\n') if h.strip()]
    
    user_data = db.get_user(user_id)
    user_data['habits'] = [
        {
            'habit': h, 
            'tracking': [],
            'streak': 0,
            'best_streak': 0
        } 
        for h in habits
    ]
    db.save_user(user_id, user_data)
    
    lang = user_data.get('language', 'en')
    keyboard = [
        [get_text(user_id, 'add_tasks_btn'), get_text(user_id, 'check_habits_btn')],
        [get_text(user_id, 'pomodoro_btn'), get_text(user_id, 'status_btn')],
        [get_text(user_id, 'help_btn')]
    ]
    
    tracking_msg = get_text(user_id, 'habits_tracking', count=len(habits))
    setup_msg = get_text(user_id, 'setup_complete')
    
    await update.message.reply_text(
        tracking_msg + setup_msg,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

# ==================== TASK MANAGEMENT ====================

async def add_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = get_text(user_id, 'add_tasks')
    await update.message.reply_text(msg, parse_mode='Markdown')
    return TASK_INPUT

async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks_text = update.message.text
    tasks = [t.strip() for t in tasks_text.split('\n') if t.strip()]
    
    context.user_data['pending_tasks'] = tasks
    context.user_data['current_task_index'] = 0
    context.user_data['task_data'] = []
    
    user_data = db.get_user(user_id)
    categories = user_data.get('categories', ['Work', 'Personal', 'Health'])
    
    keyboard = [[cat] for cat in categories] + [[get_text(user_id, 'skip_categories')]]
    
    msg = get_text(user_id, 'got_tasks', count=len(tasks), task=tasks[0])
    
    await update.message.reply_text(
        msg,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CATEGORY_SELECT

async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    category = update.message.text
    tasks = context.user_data.get('pending_tasks', [])
    index = context.user_data.get('current_task_index', 0)
    
    if 'task_data' not in context.user_data:
        context.user_data['task_data'] = []
    
    skip_text = get_text(user_id, 'skip_categories')
    context.user_data['task_data'].append({
        'task': tasks[index],
        'category': category if skip_text not in category else 'General'
    })
    
    keyboard = [
        [get_text(user_id, 'daily'), get_text(user_id, 'weekly')],
        [get_text(user_id, 'one_time')]
    ]
    
    msg = get_text(user_id, 'recurring_prompt', task=tasks[index])
    
    await update.message.reply_text(
        msg,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return RECURRING_SELECT

async def select_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    recurring = update.message.text
    tasks = context.user_data.get('pending_tasks', [])
    index = context.user_data.get('current_task_index', 0)
    
    task_data = context.user_data['task_data'][-1]
    
    daily_text = get_text(user_id, 'daily')
    weekly_text = get_text(user_id, 'weekly')
    
    if daily_text in recurring:
        task_data['recurring'] = 'daily'
    elif weekly_text in recurring:
        task_data['recurring'] = 'weekly'
    else:
        task_data['recurring'] = None
    
    msg = get_text(user_id, 'time_prompt', task=tasks[index])
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    return TIME_ALLOCATION

async def allocate_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    time_input = update.message.text
    tasks = context.user_data.get('pending_tasks', [])
    index = context.user_data.get('current_task_index', 0)
    
    task_data = context.user_data['task_data'][-1]
    task_data['time'] = time_input
    task_data['completed'] = False
    task_data['created'] = datetime.now().isoformat()
    
    index += 1
    context.user_data['current_task_index'] = index
    
    if index < len(tasks):
        user_data = db.get_user(user_id)
        categories = user_data.get('categories', ['Work', 'Personal', 'Health'])
        keyboard = [[cat] for cat in categories] + [[get_text(user_id, 'skip_categories')]]
        
        msg = get_text(user_id, 'next_task', num=index+1, task=tasks[index])
        
        await update.message.reply_text(
            msg,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return CATEGORY_SELECT
    else:
        user_data = db.get_user(user_id)
        for task in context.user_data['task_data']:
            if task.get('recurring'):
                user_data['recurring_tasks'].append(task)
            else:
                user_data['
