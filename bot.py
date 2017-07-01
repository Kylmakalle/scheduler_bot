import functools
import queue
import re
import schedule
import telebot
import threading
import time
from telebot import types

from credentials import token, admins, r, p

bot = telebot.TeleBot(token)
timers = ['-10', '+10', '-30', '+30']


def worker_main():
    while True:
        job_func = jobqueue.get()
        job_func()
        jobqueue.task_done()


jobqueue = queue.Queue()
worker_thread = threading.Thread(target=worker_main)
worker_thread.start()


def scheduler_func():
    while True:
        schedule.run_pending()
        time.sleep(1)


sched_thread = threading.Thread(name='scheduler', target=scheduler_func)
sched_thread.start()


def check_legit(message):
    if message.chat.type == 'private' and str(message.from_user.id) in admins:
        return True
    else:
        return False


def check_list(uid):
    if r.get(str(uid)):
        return
    else:
        r.set(str(uid), str(uid))


def announce(text):
    for key in r.scan_iter():
        if not r.get(key).decode('utf-8') in admins:
            try:
                bot.send_message(r.get(key).decode('utf-8'), text, parse_mode='Markdown')
            except Exception as e:
                print((r.get(key).decode('utf-8')))
                print(e)


for scheduled_post in p.scan_iter():
    schedule.every(int(scheduled_post.decode('utf-8').split('post')[0])).minutes.do(jobqueue.put,
                                                                                    functools.partial(announce, p.get(
                                                                                        scheduled_post).decode(
                                                                                        'utf-8')))


def create_task(message, timer, edit=False):
    markup = types.InlineKeyboardMarkup(row_width=4)
    markup.row(
        types.InlineKeyboardButton('-30', callback_data='-30'),
        types.InlineKeyboardButton('-10', callback_data='-10'),
        types.InlineKeyboardButton('+10', callback_data='+10'),
        types.InlineKeyboardButton('+30', callback_data='+30')
    )
    markup.add(types.InlineKeyboardButton('✅ Schedule 🕒', callback_data='schedule'))

    if edit:
        bot.edit_message_text('*Set up time scheduler in minutes:*\nPost every {} min'.format(timer), message.chat.id,
                              message.message_id, parse_mode='Markdown', reply_markup=markup)

    else:
        bot.reply_to(message, '*Set up time scheduler in minutes:*\nPost every {} min'.format(timer),
                     parse_mode='Markdown',
                     reply_markup=markup)


def job_exists(text):
    a = schedule.jobs
    for job in a:
        if job.job_func.args[0].args[0] == text:
            return True
    return False


def delete_job(text):
    a = schedule.jobs
    for job in a:
        if text in job.job_func.args[0].args[0]:
            schedule.cancel_job(job)
            for i in p.scan_iter():
                if p.get(i).decode('utf-8') == text:
                    p.delete(i)
                    return


@bot.callback_query_handler(func=lambda call: True)
def callback_buttons(call):
    if call.message:
        if call.data == 'schedule':
            m = re.search(' [0-9]* ', call.message.text)
            if m:
                p.set(str(int(m.group(0))) + 'post' + str(call.id), call.message.reply_to_message.text)
                schedule.every(int(m.group(0))).minutes.do(jobqueue.put,
                                                           functools.partial(announce,
                                                                             call.message.reply_to_message.text))
                bot.answer_callback_query(call.id, 'Will be posted every {} minutes'.format(m.group(0)))
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('🚫 Cancel 🕒', callback_data='cancel'))
                bot.edit_message_text('*Will be posted every {} minutes*'.format(m.group(0)), call.message.chat.id,
                                      call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        elif call.data in timers:
            m = re.search(' [0-9]* ', call.message.text)
            if m:
                newtimer = eval((m.group(0) + call.data))
                if newtimer < 10:
                    bot.answer_callback_query(call.id, 'Minimal time for post schedule is 10 minutes!', show_alert=True)
                else:
                    create_task(call.message, newtimer, True)
        elif call.data == 'cancel':
            try:
                delete_job(call.message.reply_to_message.text)
            except:
                delete_job(call.message.text.split('Post info\n\n')[1])
            bot.answer_callback_query(call.id, 'Cancelled')
            bot.edit_message_text('*Cancelled*', call.message.chat.id,
                                  call.message.message_id, parse_mode='Markdown')
        elif 'post' in call.data:
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.row(types.InlineKeyboardButton('◀ Back', callback_data='list'),
                       types.InlineKeyboardButton('🚫 Cancel 🕒', callback_data='cancel'))
            bot.edit_message_text('*Post info*\n\n' + p.get(call.data).decode('utf-8'), call.message.chat.id,
                                  call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        elif 'list' in call.data:
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup()
            for i in p.scan_iter():
                markup.add(types.InlineKeyboardButton(p.get(i).decode('utf-8'), callback_data=i.decode('utf-8')))
            bot.edit_message_text('*List of scheduled posts, tap on a post for more info*', call.message.chat.id,
                                  call.message.message_id,
                                  parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['start'])
def start_command(message):
    check_list(message.from_user.id)
    if check_legit(message):
        bot.send_message(message.chat.id, '<b>Hello {}</b>\n'.format(message.from_user.first_name),
                         parse_mode='HTML')


@bot.message_handler(commands=['post'])
def post_command(message):
    if check_legit(message):
        markup = types.ForceReply(selective=False)
        bot.send_message(message.chat.id, 'Reply me with message you want to schedule', reply_markup=markup)


@bot.message_handler(commands=['list'])
def list_command(message):
    if check_legit(message):
        markup = types.InlineKeyboardMarkup()
        for i in p.scan_iter():
            markup.add(types.InlineKeyboardButton(p.get(i).decode('utf-8'), callback_data=i.decode('utf-8')))
        bot.send_message(message.chat.id, '*List of scheduled posts, tap on a post for more info*',
                         parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def text_handling(message):
    if check_legit(message):
        if message.reply_to_message:
            if message.reply_to_message.from_user.id == bot.get_me().id \
                    and message.reply_to_message.text == 'Reply me with message you want to schedule':
                if not job_exists(message.text):
                    create_task(message, 60)
                else:
                    bot.send_message(message.chat.id, '*Post with the same text already exists!*',
                                     parse_mode='Markdown')


@bot.message_handler(content_types=['new_chat_members'])
def new_chat_handler(message):
    for member in message.new_chat_members:
        if member['id'] == bot.get_me().id:
            check_list(message.chat.id)


bot.polling(none_stop=True)
