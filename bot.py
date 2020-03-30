import time,  json, re
from webwhatsapi import WhatsAPIDriver
from webwhatsapi.objects.message import Message
import random
from pymongo import MongoClient
from datetime import datetime, date, timedelta
import apiai
import requests
import base64
from telethon import TelegramClient, events, sync
import socks
from obscene_words_filter.default import get_default_filter

badwords_filter = get_default_filter()


def detect_intent_audio(project_id, session_id, audio_file_path,
                        language_code):
    """Returns the result of detect intent with an audio file as input.

    Using the same `session_id` between requests allows continuation
    of the conversation."""
    import dialogflow_v2 as dialogflow

    session_client = dialogflow.SessionsClient()

    # Note: hard coding audio_encoding and sample_rate_hertz for simplicity.
    audio_encoding = dialogflow.enums.AudioEncoding.AUDIO_ENCODING_OGG_OPUS 
    sample_rate_hertz = 16000

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    with open(audio_file_path, 'rb') as audio_file:
        input_audio = audio_file.read()

    audio_config = dialogflow.types.InputAudioConfig(
        audio_encoding=audio_encoding, language_code=language_code,
        sample_rate_hertz=sample_rate_hertz)
    query_input = dialogflow.types.QueryInput(audio_config=audio_config)

    response = session_client.detect_intent(
        session=session, query_input=query_input,
        input_audio=input_audio)

    #print('=' * 20)
    #print('Query text: {}'.format(response.query_result.query_text))
    #print('Detected intent: {} (confidence: {})\n'.format(
    #    response.query_result.intent.display_name,
    #    response.query_result.intent_detection_confidence))
    #print('Fulfillment text: {}\n'.format(
    #    response.query_result.fulfillment_text))
    return  response.query_result.query_text
        
def rand_delay(min_sec=3, max_sec=10):
    time.sleep( random.randint(min_sec,max_sec) )

def start_of_month():
    return datetime.today().replace(day=1, hour=0, minute=0,second=0, microsecond=0)
    #todayDate = date.today()
    #if todayDate.day > 25:
    #    todayDate += timedelta(7)
    #return todayDate.replace(day=1)

def validate_date(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return 1
    except ValueError:
        return 0

def reply_with_mentione(driver, chat_id, orig_message_id, users, reply):
    #rand_delay(1,2)
    print("DEBUG: __reply_with_mentione__")
    userscode = "var users = []; var id = null;"
    for u in users:
	    userscode += """
			id = new window.Store.UserConstructor("%s@c.us", {intentionallyUsePrivateConstructor:true});
			users.push(id);
		""" % u
    script =   """var chat = Store.Chat.get('%s');
		%s			
		var msgs = chat.msgs.models;
		var msg = null;
		for (var i=0; i<chat.msgs.length; i++) {
			if (msgs[i].id._serialized == '%s') {
				msg = msgs[i];
			}				
		}
		if (msg != null) {
			chat.sendMessage('%s', 
				{
				linkPreview : null, 
				mentionedJidList : users, 
				quotedMsg : msg, 
				quotedMsgAdminGroupJid : null
				}  );
		} else {
			console.log('cant find q id');
		}
		""" % (chat_id, userscode, orig_message_id, reply.replace("\n", "\\n") )
    #print("DEBUG: %s" % script)
    driver.driver.execute_script(script)

def message_with_mentione(driver, chat_id, users, message):
    #rand_delay(1,2)
    print("DEBUG: __reply_with_mentione__")
    userscode = "var users = []; var id = null;"
    for u in users:
	    userscode += """
			id = new window.Store.UserConstructor("%s@c.us", {intentionallyUsePrivateConstructor:true});
			users.push(id);
		""" % u
    script =   """var chat = Store.Chat.get('%s');
		%s			
			chat.sendMessage('%s', 
				{
				linkPreview : null, 
				mentionedJidList : users, 
				quotedMsg : null, 
				quotedMsgAdminGroupJid : null
				}  );
		""" % (chat_id, userscode, message.replace("\n", "\\n") )
    #print("DEBUG: %s" % script)
    driver.driver.execute_script(script)





def normalize_num(num_in):
    num_out = []
    norm = {
       'A': 'A', 'a':'A', 'А':'A', 'а':'A',
       'B': 'B', 'b':'B', 'В':'B', 'в':'B',
       'C': 'C', 'c':'C', 'С':'C', 'с':'C',
       'E': 'E', 'e':'E', 'Е':'E', 'е':'E',
       'H': 'H', 'h':'H', 'Н':'H', 'н':'H',
       'K': 'K', 'k':'K', 'К':'K', 'к':'K',
       'M': 'M', 'm':'M', 'М':'M', 'м':'M',
       'O': 'O', 'o':'O', 'О':'O', 'о':'O',
       'P': 'P', 'p':'P', 'Р':'P', 'р':'P',
       'T': 'T', 't':'T', 'Т':'T', 'т':'T',
       'Y': 'Y', 'y':'Y', 'У':'Y', 'у':'Y',
       'X': 'X', 'x':'X', 'Х':'X', 'х':'X',
    }
    for i in range(0, len(num_in)):
        if num_in[i] in norm:
            num_out.append( norm[ num_in[i] ] )
        else:
            num_out.append( num_in[i] )
    return "".join(num_out)



def find_num2(num_norm, chat_id, from_pic=False, part_search=False):
    print("DEBUG: find_num2, num: %s" % num_norm)
    users = []
    reply = "Что-то пошло не так О_о"
    botdb = MongoClient('localhost', 27017).bot
    s = "{0}.".format(num_norm) if len(num_norm)==3 else num_norm
    print("DEBUG: num_len:", len(num_norm))
    res = botdb.numbers.find({'number':{'$regex':s}, 'chat_id': chat_id})
    if res.count()==1:
        num = res.next()
        if part_search:
            reply = "Возможно, что это @%s, полный номер %s\n" % ( num['phone'], num['number'])
        else:
            reply = "Нашел совпадение: @%s, полный номер %s\n" % ( num['phone'], num['number'])

        users.append(num['phone'])
        
    elif res.count()>1:
        reply = "Нашел несколько записей:  \n"
        for num in res:
            reply += " - @%s, полный номер %s \n" % ( num['phone'], num['number'])
            users.append(num['phone'])
    else:
        if not from_pic:
            reply = "Нет такого номера :(\n"
        else:
            reply = "Полного совпадения нет :(\nПоиск только по цифрам:\n" 
            p = re.compile("(\d{3})")
            res = p.findall(num_norm)
            if len(res) and len(res[0]) == 3:
                r, users = find_num2(res[0], chat_id, False, True)
                reply += r

    return reply, users


def process_poll(msg, phone):
    reply = ""
    botdb = MongoClient('localhost', 27017).bot
    #('Голос', 'голос', 'чип', 'Чип', 'Голосование', 'голосование')
    if msg[0] in ('чип', 'Чип', 'Голосование', 'голосование', 'ЧИП'):
        reply = """
*Голосуем за чип*\nПришлите боту в ответом сообщение:\n *голос за Revo* (или другой чип).
Варианты ответа:
- Сток
- Revo
- APR
- Etuners
- AGP
- Другое
  """
        res = botdb.poll1.aggregate([
             {"$group": { "_id" :  "$result" , "cnt": { "$sum": 1 }} },
             {"$sort":{"cnt":-1}}
        ])
        reply += "\n*Результаты*\n"
        results = []
        total = 0
        for r in res:
            print ("DEBUG:",r)
            total += r['cnt']
            #reply += "{0} - {1}\n".format(r['_id'], r['cnt'])
            results.append(r)
        
        for r in results:
            reply += "{0} - {1} ({2}%)\n".format(r['_id'], r['cnt'], round(float(r['cnt'])/float(total)*100,1) )

    elif msg[0] in ('Голос', 'голос'):
        if len(msg)>1:
            if msg[1] == 'за':
                if len(msg) == 2 or msg[2] == "":
                    reply = "За кого голосуем то?"
                    return reply
                msg[1] = msg[2]
            vote = msg[1]
            print('DEBUG: ', vote)
           
            res = botdb.poll1.find({'phone':phone, 'chat_id': chat_id})
            if res.count()>0:
                reply = "Вы уже голосовали, 2 раза низя :)"
            else:
                vote_norm = "'Другой чип'"
                
                if vote in ('Сток', 'сток'):
                    vote_norm = 'Сток'
                
                if vote in ('Revo', 'revo', 'Рево', 'рево', 'REVO'):
                    vote_norm = 'Revo'

                if vote in ('APR','Apr','apr','АПР', 'Апр', 'апр'):
                    vote_norm = 'APR'

                if vote in ('Etun','Etuners','etun','etuners', 'Етюн','етюн'):
                    vote_norm = 'Etuners'

                if vote in ('AGP','Agp', 'agp', 'АГП','Агп', 'агп'):
                    vote_norm = 'AGP'
                  
                botdb.poll1.insert({'phone': phone, 'result': vote_norm, 'chat_id': chat_id})
                reply = "Спасибо, записал голос за {0}".format(vote_norm)

    else:
        reply = "Читайте описание!"

    return reply

def process_in(in_str, message_obj, chat_id):
    m = 0
    users = []
    botdb = MongoClient('localhost', 27017).bot
    #reply = 'Не понял :(\nНайти номер - "@bot номер ххххх"\nДобавить номер в базу - "@bot добавь номер ххххх"\nПоиск телефона по базе антипаркон - "@bot пробей х456хх77"\nОстальные комманды - "@bot старт (или помощь)"'
    reply = 'Не понял :( Если нужно найти номер - "@bot номер ххххх", остальные комманды - "@bot помощь"'
    hello_replies = ['Салют!', 'Привет!','Халлоу!','Прувэт!', 'Алоха', 'Шалом :)']
    in_str = in_str[1:len(in_str)].strip() if in_str.startswith(',') else in_str.strip()
    #remove multiple spaces 
    in_str = " ".join(in_str.split())
    
    msg = in_str.split(' ')
    if len(msg):
        if msg[0] in ('Номер', 'номер'):
            if len(msg)>=2 and msg[1] and len(msg[1])>=3:
                num_in = msg[1]
                print ('DEBUG: num in = ', num_in)
                num_norm = normalize_num(num_in)
                print ('DEBUG: num norm = ', num_norm)
                #reply = find_num(num_norm, False)
                reply, users = find_num2(num_norm, chat_id, False)
                
                #fixme
                m = 1
                #m = 0
            else:
                reply = "Не совсем понял запрос. Надо, к примеру, так: @bot номер 640 или @bot номер в861рт (минимум 3 символа)"

        elif msg[0] in ('Добавь', 'добавь', 'Добавить', 'добавить'):
            #print("DEBUG,", msg)
            if len(msg)>=3 and msg[1] and msg[2] and msg[1] in ('номер', 'Номер'):
                num_norm = normalize_num(msg[2])
                print ('DEBUG: num norm = ', num_norm)
                if len(num_norm)<=10 and len(num_norm)>=3:
                    res = botdb.numbers.find({'number':num_norm, 'chat_id': chat_id})
                    if res.count():
                        reply = "Такой номер уже есть в базе, но спасибо ;)"
                    else:
                        botdb.numbers.insert( { 'number':num_norm, 
                                        'name': message_obj['sender']['pushname'], 
                                        'phone':message_obj['sender']['id']['user'], 'chat_id': chat_id } )
                        reply = 'Ок, я запомнил номер тачки %s - это %s ' % (num_norm, message_obj['sender']['pushname'])
                else:
                    reply = "Слишком длинный или слишком короткий номер (минимально 3 символа, максимально 10), не могу добавить."
            elif len(msg)>=3 and msg[1] and msg[2] and msg[1] in ('др', 'Др', 'ДР', 'днюху'):
                print("DEBUG: dr_add mode")
                dr = msg[2]
                if dr and len(dr) and validate_date(dr):
                    dr_dt = datetime.strptime(dr, '%Y-%m-%d')
                    botdb.drs.insert( { 'name': message_obj['sender']['pushname'],
                                        'phone':message_obj['sender']['id']['user'],
                                        'day': dr_dt.day,
                                        'month': dr_dt.month,
                                        'year': dr_dt.year,
                                        'chat_id': chat_id} )
                    reply = "Ок, спасибо, я записал твой день рождения! ;)"
                else:
                    reply = "Не понял формат даты. Нужно использовать ГГГГ-ММ-ДД. Например *@bot добавь др 1983-08-17* "
            else:
                reply = """Не совсем понял запрос. \nНадо, к примеру, так: *@bot добавь номер в861рт77* . Добавить можно только свой номер!\nИли *@bot добавь др 1983-08-17* - я запомню твой день рождения и приготовлю подарочек ;)"""

        elif msg[0] in ('помощь', 'Помощь','Help', 'help', 'Комманды', 'комманды', 'старт', 'начало', 'Старт', 'Начало'):
            reply = "Привет, я - бот.\n\n*!!! Важное обновление от 28 Августа 2019 - теперь то, что вы пишете мне в личку - это наш личный чат и он не относится к другим публичным чатам !!!*\n\nПонимаю следующие комманды:\n*@bot Номер в861рт77*\n - поищу по базе - кто скрывается за этим номером.\n Можно только цифры или часть букв - все равно найду\n*@bot Добавь номер в861рт77* - добавить номер в базу"
            reply += "\n*@bot Статистика* - небольшая стата по чату за сутки"
            reply += "\n*@bot Пробей х345х67* - поиск номера в базе антипаркон"
            reply += "\n*@bot Добавь др 1983-08-17* - запомнить день рождения, приготовить подарки :) "
            reply += "\n*@bot Пометка бота под картинкой* - бот постарается найти номер на фотке и пробить по базе одноклубников."
            reply += "\n*@bot чип* - голосование за лучший чип."

        elif msg[0] in ('Статистика','статистика', 'Стата', 'стата'):
            dt_from = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 0,0,0)
            dt_to = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 23,59,59)
            ms_obj = start_of_month()
            month_start = datetime(ms_obj.year, ms_obj.month, ms_obj.day, 0,0,0)
            et_obj = date.today() - timedelta(1)
            yt_from = datetime(et_obj.year, et_obj.month, et_obj.day, 0,0,0)
            yt_to = datetime(et_obj.year, et_obj.month, et_obj.day, 23,59,59)            
            
            reply = "*Всего сообщений за:*\n"
            res = botdb.botstats.find({'dt': {'$gte': dt_from, '$lte': dt_to}, 'chat_id': chat_id})
            reply += "- сегодня: %d\n" % res.count()
            
            res = botdb.botstats.find({'dt': {'$gte': yt_from, '$lte': yt_to}, 'chat_id': chat_id})
            reply += "- вчера: %d\n" % res.count()
            print("DEBUG:", month_start, dt_to)
            res = botdb.botstats.find({'dt': {'$gte': month_start, '$lte': dt_to}, 'chat_id': chat_id})
            reply += "- месяц: %d\n" % res.count()
            
            res = botdb.botstats.aggregate([
                {"$match": {'chat_id': chat_id}},
        	    {"$group": { "_id" : { "month": { "$month": "$dt" }, "day": { "$dayOfMonth": "$dt" }, "year": { "$year": "$dt" }  }, "cnt": { "$sum": 1 }}},
        	    {"$sort":{"cnt":-1}}
                ])
            if res:
                r = res.next()
                reply += "\nБольше всего сообщений ({0}) было {3}.{2}.{1}\n".format(r['cnt'], r['_id']['year'], r['_id']['month'], r['_id']['day'])
            
            res = botdb.botstats.aggregate([
                {"$match":{'dt': {'$gte': dt_from, '$lte': dt_to}, 'chat_id': chat_id}},
                {"$group":{"_id":"$name", "total": {"$sum": 1}}},
                {"$sort":{"total":-1}}, 
                {"$limit":10}
                ])
            reply += "\n*Топ 10 авторов сегодня:*\n"
            for r in res:
                reply+="@%s: %d\n" % (r['_id'], r['total'])
                users.append(str(r['_id']))
            
            res = botdb.botstats.find({'dt': {'$gte': dt_from, '$lte': dt_to}, 'blya_counter':1})
            #reply += "Слово бл* написали %d раз\n" % res.count()
            res = botdb.botstats.aggregate([
                {"$match":{'dt': {'$gte': dt_from, '$lte': dt_to}, 'blya_counter':1, 'chat_id': chat_id}},
                {"$group":{"_id":"$name", "total": {"$sum": 1}}},
                {"$sort":{"total":-1}}, 
                {"$limit":5}
                ])
            reply += "\n*Топ 5 культурных людей:*\n"
            for r in res:
                reply += "@%s: %d\n" % (r['_id'], r['total'])
                if str(r['_id']) not in users:
                    users.append(str(r['_id']))			

            res = botdb.botstats.aggregate([
                {"$match":{'chat_id': chat_id}},
                {"$group":{"_id":"$name", "total": {"$sum": 1}}},
                {"$sort":{"total":-1}}, 
                {"$limit":5}
                ])
            reply += "\n*Топ 5 болтунов за все время:*\n"
            for r in res:
                reply+="@%s: %d\n" % (r['_id'], r['total'])
                if str(r['_id']) not in users:
                    users.append(str(r['_id']))			
            m =  0

        elif msg[0] in ('матсата','ктопиздабол', 'ктопиздобол', 'матершинники', 'стата2'):
            dt_from = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 0,0,0)
            dt_to = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 23,59,59)
            ms_obj = start_of_month()
            month_start = datetime(ms_obj.year, ms_obj.month, ms_obj.day, 0,0,0)
            et_obj = date.today() - timedelta(1)
            yt_from = datetime(et_obj.year, et_obj.month, et_obj.day, 0,0,0)
            yt_to = datetime(et_obj.year, et_obj.month, et_obj.day, 23,59,59)            
            
            reply = "*Всего сообщений за:*\n"
            res = botdb.botstats.find({'dt': {'$gte': dt_from, '$lte': dt_to}, 'chat_id': chat_id})
            reply += "- сегодня: %d\n" % res.count()
            
            
            res = botdb.botstats.find({'dt': {'$gte': dt_from, '$lte': dt_to}, 'blya_counter':1})
            reply += "Слово бл* написали %d раз\n" % res.count()
            res = botdb.botstats.aggregate([
                {"$match":{'dt': {'$gte': dt_from, '$lte': dt_to}, 'blya_counter':1, 'chat_id': chat_id}},
                {"$group":{"_id":"$name", "total": {"$sum": 1}}},
                {"$sort":{"total":-1}}, 
                {"$limit":5}
                ])
            reply += "\n*Топ 5 культурных людей:*\n"
            for r in res:
                reply += "@%s: %d\n" % (r['_id'], r['total'])
                if str(r['_id']) not in users:
                    users.append(str(r['_id']))			

            res = botdb.botstats.aggregate([
                {"$match":{'chat_id': chat_id}},
                {"$group":{"_id":"$name", "total": {"$sum": 1}}},
                {"$sort":{"total":-1}}, 
                {"$limit":5}
                ])
            reply += "\n*Топ 5 болтунов за все время:*\n"
            for r in res:
                reply+="@%s: %d\n" % (r['_id'], r['total'])
                if str(r['_id']) not in users:
                    users.append(str(r['_id']))			
            m =  0

        elif msg[0] in ('Стоп','стоп', 'Хватит', 'хватит', 'Заткнись', 'заткнись', 'Молчи', 'молчи', 'Замолчи','замолчи'):
            reply = ""
        elif msg[0] in ('Test', 'test', 'тест', 'Тест'):
            m = 1
            reply = "Тест с пометкой @79261415371"
            users = ['79261415371']
        elif msg[0] in ('Пробей', 'пробей'):
            print("DEBUG: requests -> telegram")
            print("DEBUG: ", msg)
            api_id = 668594
            api_hash = '50c644ca8f583f0710a46209dac7f56c'
            tgclient = TelegramClient('session_name', api_id, api_hash, proxy=(socks.HTTP, 'easy-dns.ru', 3128, True, 'cli', 'clicli'))
            print ("DEBUG: Telegram cli prestart!")
            try:
                tgclient.start()
                print ("DEBUG: Telegram cli started!")
                with tgclient.conversation('AntiParkonBot') as conv:
                    num = msg[1]
                    if msg[1] == 'номер' and msg[2] and len(msg[2]):
                        num = msg[2]
                    conv.send_message(num)
                    reply = conv.get_response().raw_text
            except Exception as e:
                print("DEBUG: %s" % e )
                reply = "Нет связи с Telegram ботом. Коллега в запое."
                
            try:
                tgclient.disconnect()
                print ("DEBUG: Telegram cli closed!")
            except Exception:
                pass

        elif msg[0] in ('Голос', 'голос', 'чип', 'Чип', 'Голосование', 'голосование', 'ЧИП'):
            reply = process_poll(msg, message_obj['sender']['id']['user'])

        else:
            # dialogflow
            print ("Debug: dialogflow")
            request = apiai.ApiAI('4278b35c7bc6411a8bc04adf22e3a5e7').text_request()
            request.lang = 'ru'
            request.session_id = '%s-%s' % (message_obj['sender']['id']['user'], chat_id)
            request.query = in_str
            responseJson = json.loads(request.getresponse().read().decode('utf-8'))
            response = responseJson['result']['fulfillment']['speech']
            #print ("Debug: ", responseJson)
            if response:
                reply = response.replace("<br>", "\n")
            #print ("Debug: ", responseJson)

    return reply, m, users


def collect_stat(m_obj, message, chat_id):
    botdb = MongoClient('localhost', 27017).bot
    blya_counter = 0
    if hasattr(message, 'content'):
        cnt = message.content
        cnt_c = badwords_filter.mask_bad_words(cnt)
        if cnt!=cnt_c:
            blya_counter = 1
            print ('DEBUG: blya_counter triggered')
    
    try:
        botdb.botstats.insert({'dt': datetime.now(), 'name': m_obj['sender']['pushname'], 'phone':m_obj['sender']['id']['user'], 'blya_counter': blya_counter, 'chat_id': chat_id})
    except Exception:
        print (dir(m_obj))

not_allowed = "В данном чате работа бота невозможна. Свяжитесь с администратором (+79261415371) для добавления в список разрешенных чатов."

def process_message(driver, contact, message, chat_id, for_me = False, is_allowed = True):
    mynum = '79259146473'
    driver.chat_send_seen(message.chat_id['_serialized'])
    m_obj = message.get_js_obj()
    print ('DEBUG: allowed - %s ' % is_allowed )
    collect_stat(m_obj, message, chat_id)
    #raise Exception(m_obj)
    if  (not m_obj['isMedia'])  and ( for_me or ( not m_obj['isGroupMsg'] ) or ( (hasattr(message, 'content') and message.content.find(mynum)!= -1) or ('quotedParticipant' in m_obj and m_obj['quotedParticipant']['user'] == mynum) ) ):
        #print('DEBUG: ', driver.get_all_message_ids_in_chat( driver.get_chat_from_id(message.chat_id) ) )
        #quoted ! lookup for media
        if not is_allowed:            
            reply_with_mentione(driver, message.chat_id['_serialized'], m_obj['id'], [], not_allowed)
            return
        
        print('DEBUG: HERE!')
        if 'quotedStanzaID' in m_obj and m_obj['quotedStanzaID']:
            print('DEBUG: HERE5!')
            original_id = None
            all_ids = driver.get_all_message_ids_in_chat( driver.get_chat_from_id(message.chat_id) )
            for id in all_ids:
                if id.find(m_obj['quotedStanzaID'])!=-1:
                    original_id = id                    
                    break
            if original_id:
                q_message = driver.get_message_by_id(id)
                q_message_obj = q_message.get_js_obj()
                if q_message_obj['isMedia'] or q_message_obj['isMMS']:
                    process_message(driver, contact, q_message, chat_id, True)
                    print ("DEBUG: process_message -> next ")
                    return
            else:
                print("DEBUG: can't find original ID")
        #else:
        try:
            cnt = message.content
        except:
            print("DEBUG: No content")
            print (message.type)
            print (message.mime)
            if message.mime.startswith("audio"):
                filename = message.save_media('audio/', True)
                print ("DEBUG: audio saved as: %s" % filename)
                cnt = detect_intent_audio("small-talk-12661", chat_id, filename, "RU")
                reply_with_mentione(driver, message.chat_id['_serialized'], m_obj['id'], [], "Я рассылшал: %s" % cnt)            
                return 
            else:
                cnt = ""
        cnt = cnt.replace("*", "")
        if m_obj['isGroupMsg']:
            cnt = re.sub("@\d+\s?", '', cnt).strip()
            print("DEBUG: GROUP!")
        is_m = 0
        users = []
        if len(cnt):
            reply, is_m, users = process_in(cnt, m_obj, chat_id)
            print("DEBUG", reply, is_m, users)
            if len(reply) and not is_m:
                #rand_delay(1,2)
                #driver.send_message_to_id(message.chat_id['_serialized'], reply)
                driver.chat_reply_message_q(m_obj['id'], reply)
            elif len(reply) and is_m:
                reply_with_mentione(driver, message.chat_id['_serialized'], m_obj['id'], users, reply)            

    elif ( m_obj['isMedia']) and (for_me or ( not m_obj['isGroupMsg'] ) or ( (hasattr(message, 'content') and message.content.find(mynum)!= -1) or ('quotedParticipant' in m_obj and  m_obj['quotedParticipant']['user'] == mynum) or ( 'caption' in m_obj and m_obj['caption'].find(mynum)!=-1 ) ) ):
        #ok, media for me
        #print (m_obj)
        print('DEBUG: HERE2!')
        filename = message.save_media('media/', True)
        print ('DEBUG: Media saved as %s' % filename)
        SECRET_KEY = 'sk_88aa552eecc5039105cf270a'
        with open(filename, 'rb') as image_file:
            img_base64 = base64.b64encode(image_file.read())
        url = 'https://api.openalpr.com/v2/recognize_bytes?recognize_vehicle=1&country=ru&secret_key=%s' % (SECRET_KEY)
        r = requests.post(url, data = img_base64)
        res_obj=r.json()
        print("DEBUG: got reply from API")
        if not res_obj['results']:
            print("DEBUG: no number found")
            #rand_delay(1,2)
            driver.chat_reply_message_q(m_obj['id'], "Не получилось найти на картинке номер или распознать его, сорян :(")
        else:
            reply = ""
            users = []
            for res in res_obj['results']:
                reply += "Номер *%s*:\n" % normalize_num(res['plate'])
                r, u = find_num2(normalize_num(res['plate']), chat_id, True)
                users += u
                #reply += find_num(normalize_num(res['plate']), True)
                reply += r
                reply += "\n"

            #rand_delay(1,2)
            #print ('DEBUG: '+m_obj['id']+" -- "+ reply)
            #!!!fixme
            #driver.chat_reply_message_q(m_obj['id'], reply)
            reply_with_mentione(driver, message.chat_id['_serialized'], m_obj['id'], users, reply)

#happy birthdays
def cron_drs(driver, chat_id):
    #chat_id = "79250046010-1479907337@g.us"
    users = []
    now_time = datetime.now()
    happy_bd_alarms_hours = [9, 12]
    if now_time.hour in happy_bd_alarms_hours:
        #print("DEBUG: __happy_bd_alarms_hours__")
        botdb = MongoClient('localhost', 27017).bot
        res = botdb.drs.find({'day': now_time.day, 'month': now_time.month, 'chat_id': chat_id})
        if res.count():
            #print("DEBUG: __botdb.drs.count__")
            person = res.next()
            res_done = botdb.drs_done.find({'year': now_time.year, 'phone': person['phone'], 'hour': now_time.hour, 'chat_id': chat_id})
            if not res_done.count():
                #ok, we have a winner!                
                botdb.drs_done.insert({'year': now_time.year, 'phone': person['phone'], 'hour': now_time.hour, 'chat_id': chat_id})
                if now_time.hour < 10:
                    mess = "*Поздравляем с Днем рождения* @{0}!\n !!! Ура !!! ".format(person['phone'])
                else:
                    mess = "Напоминаю, cегодня с Днем рождения у @{0}!".format(person['phone'])
                users.append(person['phone'])
                message_with_mentione(driver, chat_id, users, mess)


def process_cron_jobs(driver, chat_id):
    cron_drs(driver, chat_id)


#main loop
driver = WhatsAPIDriver(profile='/home/mike/.config/google-chrome/Default/', client='Chrome')
print("Waiting for QR")
driver.wait_for_login()

print("Bot started")

allowed_chats = [
    '79261415371-1544519131@g.us', 
    '79163125109-1365608814@g.us', 
    '79645927222-1513015212@g.us', #superb
    '79999803895-1564487811@g.us', #отбитые
    '79035041429-1570652063@g.us',
    '79282261400-1525178704@g.us', #йети чат
    '79264595773-1426590086@g.us'
    ]

while True:
    rand_delay(1,2)
    try:
        for contact in driver.get_unread():
            #print ("DEBUG:", dir(contact))
            for message in contact.messages:
            
                #try:
                chat_id = message.chat_id['_serialized']
                print("DEBUG: got message!")
                print("DEBUG: chat_id {}!".format(chat_id))
                #if chat_id.endswith('c.us') or ( chat_id.endswith('g.us') and chat_id in allowed_chats ):
                rand_delay(1,2)
                process_message(driver, contact, message, chat_id)
                process_cron_jobs(driver, chat_id)
                #else:      
                #    print ("DEBUG: not allowed chat!")
                #    process_message(driver, contact, message, chat_id, False, False)
    except Exception as e:
        print ("Driver error: %s" % e)
    
