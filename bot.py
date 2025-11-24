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

# Database class
class ProductivityDB:
    def __init__(self):
        self.users = {}
        self.teams = {}
    
    def get_user(self, user_id):
        if user_id not in self.users:
            self.users[user_id] = {
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
(GOALS_INPUT, HABITS_INPUT, TASK_INPUT, TASK_CONFIRM, 
 CATEGORY_SELECT, RECURRING_SELECT, TIME_ALLOCATION) = range(7)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== SETUP & ONBOARDING ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    welcome_text = (
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
        "Let's set up your account!\n\n"
        "Enter your *3 MAJOR GOALS* for this month (one per line):"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
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
    
    await update.message.reply_text(
        f"✅ *Goals Set!*\n" + 
        "\n".join([f"{i+1}. {g}" for i, g in enumerate(goals[:3])]) +
        "\n\n🎯 Now, what *HABITS* do you want to build?\n"
        "(One per line, e.g., 'Drink 8 glasses of water', 'Exercise 30min')",
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
    
    keyboard = [
        ['📋 Add Tasks', '✅ Check Habits'],
        ['🍅 Pomodoro', '📊 Status'],
        ['❓ Help']
    ]
    
    await update.message.reply_text(
        f"🎯 *Perfect! Tracking {len(habits)} habits*\n\n"
        f"Setup complete! Here's what you can do:\n\n"
        f"*Commands:*\n"
        f"✏️ /add - Add tasks manually\n"
        f"✅ /habits - Check off habits\n"
        f"🍅 /pomodoro - Focus timer\n"
        f"📊 /status - Today's progress\n"
        f"🎯 /goals - Update goals\n"
        f"👥 /team - Team features\n"
        f"📈 /report - View reports\n"
        f"📄 /export - Export PDF",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

# ==================== TASK MANAGEMENT ====================

async def add_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ *Enter your tasks* (one per line)\n\n"
        "Example:\n"
        "Buy groceries\n"
        "Finish report\n"
        "Call dentist",
        parse_mode='Markdown'
    )
    return TASK_INPUT

async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks_text = update.message.text
    tasks = [t.strip() for t in tasks_text.split('\n') if t.strip()]
    
    context.user_data['pending_tasks'] = tasks
    context.user_data['current_task_index'] = 0
    context.user_data['task_data'] = []
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    categories = user_data.get('categories', ['Work', 'Personal', 'Health'])
    
    keyboard = [[cat] for cat in categories] + [['⏭️ Skip Categories']]
    
    await update.message.reply_text(
        f"📋 *Got {len(tasks)} tasks!*\n\n"
        f"🏷️ Task 1: {tasks[0]}\n\nSelect category:",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CATEGORY_SELECT

async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    tasks = context.user_data.get('pending_tasks', [])
    index = context.user_data.get('current_task_index', 0)
    
    if 'task_data' not in context.user_data:
        context.user_data['task_data'] = []
    
    context.user_data['task_data'].append({
        'task': tasks[index],
        'category': category if '⏭️' not in category else 'General'
    })
    
    keyboard = [
        ['📅 Daily', '📆 Weekly'],
        ['⏭️ One-time only']
    ]
    
    await update.message.reply_text(
        f"🔁 Is this a *recurring* task?\n\nTask: {tasks[index]}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return RECURRING_SELECT

async def select_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recurring = update.message.text
    tasks = context.user_data.get('pending_tasks', [])
    index = context.user_data.get('current_task_index', 0)
    
    task_data = context.user_data['task_data'][-1]
    
    if '📅' in recurring:
        task_data['recurring'] = 'daily'
    elif '📆' in recurring:
        task_data['recurring'] = 'weekly'
    else:
        task_data['recurring'] = None
    
    await update.message.reply_text(
        f"⏰ *Task:* {tasks[index]}\n\n"
        f"Enter time:\n"
        f"• HH:MM format (e.g., 14:30)\n"
        f"• Or duration in minutes (e.g., 30)",
        parse_mode='Markdown'
    )
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
        keyboard = [[cat] for cat in categories] + [['⏭️ Skip Categories']]
        
        await update.message.reply_text(
            f"🏷️ *Task {index + 1}:* {tasks[index]}\n\nSelect category:",
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
                user_data['tasks'].append(task)
        
        points = len(tasks) * 5
        user_data['points'] += points
        
        db.save_user(user_id, user_data)
        
        summary = "\n".join([
            f"{i+1}. [{t['category']}] {t['task']} - {t['time']}" +
            (f" ({t['recurring']})" if t.get('recurring') else "")
            for i, t in enumerate(context.user_data['task_data'])
        ])
        
        await update.message.reply_text(
            f"✅ *All set!*\n\n{summary}\n\n"
            f"🎉 +{points} points earned!\n"
            f"I'll remind you at scheduled times! 🔔",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

# ==================== POMODORO TIMER ====================

async def pomodoro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    settings = user_data.get('pomodoro_settings', {'work': 25, 'break': 5, 'long_break': 15})
    
    keyboard = [
        [InlineKeyboardButton("🍅 Start Work (25min)", callback_data="pomo_work")],
        [InlineKeyboardButton("☕ Short Break (5min)", callback_data="pomo_break")],
        [InlineKeyboardButton("🌙 Long Break (15min)", callback_data="pomo_long")]
    ]
    
    count = user_data.get('pomodoro_count', 0)
    
    await update.message.reply_text(
        f"🍅 *Pomodoro Timer*\n\n"
        f"Completed today: {count} pomodoros\n\n"
        f"Work: {settings['work']}min | Break: {settings['break']}min | Long: {settings['long_break']}min",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def pomodoro_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    settings = user_data['pomodoro_settings']
    
    if query.data == "pomo_work":
        duration = settings['work']
        msg = f"🍅 *Work session started!*\n\nFocus for {duration} minutes.\nI'll notify you when it's done!"
        
        context.job_queue.run_once(
            pomodoro_complete,
            duration * 60,
            data={'user_id': user_id, 'type': 'work'},
            name=f'pomo_{user_id}'
        )
        
        user_data['pomodoro_count'] += 1
        user_data['points'] += 10
        db.save_user(user_id, user_data)
        
    elif query.data == "pomo_break":
        duration = settings['break']
        msg = f"☕ *Break time!*\n\nRelax for {duration} minutes."
        
        context.job_queue.run_once(
            pomodoro_complete,
            duration * 60,
            data={'user_id': user_id, 'type': 'break'},
            name=f'pomo_{user_id}'
        )
    
    elif query.data == "pomo_long":
        duration = settings['long_break']
        msg = f"🌙 *Long break!*\n\nRecharge for {duration} minutes."
        
        context.job_queue.run_once(
            pomodoro_complete,
            duration * 60,
            data={'user_id': user_id, 'type': 'long_break'},
            name=f'pomo_{user_id}'
        )
    
    await query.edit_message_text(msg, parse_mode='Markdown')

async def pomodoro_complete(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data['user_id']
    session_type = job.data['type']
    
    if session_type == 'work':
        msg = "🎉 *Work session complete!*\n\nGreat focus! Take a break now. 🍵"
    else:
        msg = "⏰ *Break's over!*\n\nReady for another work session? 🍅"
    
    await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')

# ==================== HABITS & STREAKS ====================

async def habits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    habits = user_data.get('habits', [])
    
    if not habits:
        await update.message.reply_text("No habits set. Use /start to set up.")
        return
    
    today = datetime.now().date().isoformat()
    
    habit_list = []
    for i, habit in enumerate(habits):
        streak = habit.get('streak', 0)
        best = habit.get('best_streak', 0)
        done_today = today in habit.get('tracking', [])
        
        status = "✅" if done_today else "⬜"
        habit_list.append(f"{status} {habit['habit']} - 🔥{streak} (best: {best})")
    
    keyboard = [[h['habit']] for h in habits if today not in h.get('tracking', [])]
    if keyboard:
        keyboard.append(['✨ All Done!'])
    
    await update.message.reply_text(
        f"📊 *Daily Habits*\n\n" + "\n".join(habit_list) + "\n\n" +
        ("Tap to check off:" if keyboard else "🎉 All habits done today!"),
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True) if keyboard else None
    )

async def habit_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habit_name = update.message.text
    
    if habit_name == '✨ All Done!':
        await update.message.reply_text("🎉 Amazing! All habits completed!")
        return
    
    user_data = db.get_user(user_id)
    today = datetime.now().date().isoformat()
    
    for habit in user_data['habits']:
        if habit['habit'] == habit_name:
            if today not in habit['tracking']:
                habit['tracking'].append(today)
                habit['streak'] = habit.get('streak', 0) + 1
                
                if habit['streak'] > habit.get('best_streak', 0):
                    habit['best_streak'] = habit['streak']
                
                points = 5 + (habit['streak'] // 7) * 5
                user_data['points'] += points
                
                if habit['streak'] == 7:
                    user_data['achievements'].append(f"🏆 Week Warrior - {habit_name}")
                elif habit['streak'] == 30:
                    user_data['achievements'].append(f"👑 Month Master - {habit_name}")
                
                db.save_user(user_id, user_data)
                
                msg = f"✅ *{habit_name}* checked!\n\n🔥 Streak: {habit['streak']} days\n🎉 +{points} points"
                
                if habit['streak'] % 7 == 0:
                    msg += f"\n\n🎊 *MILESTONE!* {habit['streak']} day streak!"
                
                await update.message.reply_text(msg, parse_mode='Markdown')
                break

# ==================== STATUS & REPORTS ====================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    tasks = user_data.get('tasks', [])
    completed = [t for t in tasks if t.get('completed')]
    habits = user_data.get('habits', [])
    today = datetime.now().date().isoformat()
    habits_done = sum(1 for h in habits if today in h.get('tracking', []))
    
    status_text = (
        f"📊 *Today's Progress*\n\n"
        f"✅ Tasks: {len(completed)}/{len(tasks)}\n"
        f"🎯 Habits: {habits_done}/{len(habits)}\n"
        f"🍅 Pomodoros: {user_data.get('pomodoro_count', 0)}\n"
        f"⭐ Total Points: {user_data.get('points', 0)}\n\n"
        f"{'🎉 Great day!' if len(completed) == len(tasks) and habits_done == len(habits) else '💪 Keep going!'}"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def export_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    await update.message.reply_text("📄 Generating PDF report...")
    
    pdf_path = f"report_{user_id}.pdf"
    create_pdf_report(user_data, pdf_path)
    
    with open(pdf_path, 'rb') as pdf:
        await update.message.reply_document(
            document=pdf,
            filename=f"ProductivityReport_{datetime.now().strftime('%Y%m%d')}.pdf",
            caption="📊 Your productivity report"
        )
    
    os.remove(pdf_path)

def create_pdf_report(user_data, filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title = Paragraph(f"<b>Productivity Report - {datetime.now().strftime('%B %Y')}</b>", styles['Title'])
    story.append(title)
    
    goals = user_data.get('monthly_goals', [])
    if goals:
        story.append(Paragraph("<br/><b>Monthly Goals</b>", styles['Heading2']))
        goal_data = [['Goal', 'Progress']]
        for g in goals:
            goal_data.append([g['goal'], f"{g['progress']}%"])
        
        goal_table = Table(goal_data)
        goal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(goal_table)
    
    habits = user_data.get('habits', [])
    if habits:
        story.append(Paragraph("<br/><b>Habit Streaks</b>", styles['Heading2']))
        habit_data = [['Habit', 'Current Streak', 'Best Streak']]
        for h in habits:
            habit_data.append([h['habit'], str(h.get('streak', 0)), str(h.get('best_streak', 0))])
        
        habit_table = Table(habit_data)
        habit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(habit_table)
    
    story.append(Paragraph(f"<br/><b>Statistics</b>", styles['Heading2']))
    story.append(Paragraph(f"Total Points: {user_data.get('points', 0)}", styles['Normal']))
    story.append(Paragraph(f"Pomodoros: {user_data.get('pomodoro_count', 0)}", styles['Normal']))
    story.append(Paragraph(f"Achievements: {len(user_data.get('achievements', []))}", styles['Normal']))
    
    doc.build(story)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 *Command Reference*\n\n"
        "*Getting Started:*\n"
        "/start - Setup goals & habits\n\n"
        "*Daily Use:*\n"
        "/add - Add new tasks\n"
        "/habits - Check off habits\n"
        "/pomodoro - Focus timer\n"
        "/status - Today's progress\n\n"
        "*Management:*\n"
        "/goals - Update goals\n"
        "/team - Team features\n\n"
        "*Reports:*\n"
        "/report - View reports\n"
        "/export - Download PDF\n\n"
        "💡 Tip: Use quick reply buttons for faster access!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== MAIN ====================

def main():
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    logger.info("🚀 Starting bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GOALS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_goals)],
            HABITS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_habits)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    task_conv = ConversationHandler(
        entry_points=[CommandHandler('add', add_tasks)],
        states={
            TASK_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tasks)],
            CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
            RECURRING_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_recurring)],
            TIME_ALLOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, allocate_time)],
        },
        fallbacks=[CommandHandler('add', add_tasks)]
    )
    
    application.add_handler(setup_conv)
    application.add_handler(task_conv)
    application.add_handler(CommandHandler('pomodoro', pomodoro_command))
    application.add_handler(CommandHandler('habits', habits_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('export', export_pdf))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(pomodoro_callback, pattern='^pomo_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, habit_check))
    
    logger.info("✅ Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
