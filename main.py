# -*- coding: utf-8 -*-
"""
Created on Fri Dec 15 18:53:01 2023

@author: Sergey
"""

import random, gspread, os, time
import PySimpleGUI as sg
from datetime import date
from dotenv import load_dotenv
import pandas as pd
import requests, json
from numpy import nan
# import pyperclip
import re
from oauth2client.service_account import ServiceAccountCredentials

from openai import OpenAI, NOT_GIVEN
import anthropic

ASSISTANT_ID = 'asst_9RsOhqrpjyfCtKqlJQCb56Va'  
# THREAD_ID = 'thread_bkuZx2KYrj27MxilUBDmXP5x'#'thread_YfDGV3jGfkSo4pBtbkpC5CqG' - to delete

THREAD_ID = 'thread_FJLF4PcM5UbEgcLWLs3A3wri' #testing thread, delete later

load_dotenv()

API_KEY = os.getenv('API_KEY')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_KEY')
MODEL = 'gpt-4o'

TG_TOKEN = os.getenv('TG_TOKEN')
client = OpenAI(api_key = API_KEY)
client2 = anthropic.Anthropic(api_key = ANTHROPIC_KEY)
CHAT_ID = "330959414"

rewrite_mapping = {
    'EXP_REWRITE': 'explanation',
    'ORIG_REWRITE': 'origin',
    'EXMP_REWRITE': 'examples'
    }


# example1 = '''Here's a good example for the word "flamboyant":
# "Flamboyant" 🌈✨

# Когда ваша одежда так ярка, что пугает солнечные зайчики... когда ваша личность сверкает ярче, чем диско-шар на лучшей вечеринке города... когда даже ваша собака отказывается выходить на прогулку с вами, потому что её "слишком много"... Вот тогда вы **flamboyant**.

# Перевод: вычурный, экстравагантный, кричащий - слово, которое описывает все, что настолько яркое и броское, что вызывает восхищение у стилистов и лёгкое замешательство у остальных. От пышных розовых пламенеющих фламинго до вашего дяди Васи в его новом зелёном костюме для гольфа - **flamboyant** вокруг нас, и это прекрасно!

# Слово "flamboyant" происходит от французского "flamboyant", что в буквальном переводе означает "пламенеющий". Этот термин, в свою очередь, происходит от французского глагола "flamber", означающего "гореть пламенем" или "вспыхивать". Изначально это слово использовалось для описания стиля архитектуры с обилием украшений, напоминающих пламя, а в современном английском языке "flamboyant" описывает яркость, экстравагантность и выразительность в поведении, стиле или дизайне.

# Использование в предложении:
    
# - The designer's latest collection was flamboyant, filled with bright colors and extravagant designs that caught everyone's eye.

# - Последняя коллекция дизайнера была вычурной, наполненной яркими цветами и экстравагантными дизайнами, которые привлекали внимание всех.    

# Используйте это слово, чтобы описать все, что притягивает взгляды в комнате и не оставляет равнодушным. И помните, иногда немного flamboyant-а в жизни - это именно то, что нужно, чтобы сделать серые будни ярче!

# тэги: #flamboyant #вычурный #экстравагантный #кричащий
# '''


def connect_to_spreadsheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds_file = r'.secrets\token.json'
        # if not os.path.isfile(creds_file):
        #     creds_file = input('Input path to creds file')#G:\Shared drives\70 Data & Technology\70.03 Scripts\mellanni_2\google-cloud\competitor_pricing.json
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        
        #open Google Sheets sheet
        book = client.open_by_key('1TNgDtiUKNFeRDBOSrYEksArLudYhNAh-6A69O9Y9N6k')
        # book = client.open_by_url('https://docs.google.com/spreadsheets/d/1szVxXEaScCtgXgVZQhjn3KZp2zJ_KPxytWfjIVJcBhk')
        sheet = book.get_worksheet_by_id(1386834576)
        data = pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        raise Exception(e)
    return data

def generate_image(word: str) -> None:
    response = client.images.generate(
      model="dall-e-3",
      prompt=f'create an image that best describes the meaning of "{word}"',
      size="1024x1024",
      # size = '1792x1024',
      quality="standard",
      n=1,
    )
    
    image_url = response.data[0].url
    return image_url

def generate_sound(word: str) -> None:
    out_file = f'{word}.mp3'
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=word
        )
    response.stream_to_file(out_file)
    return None

def assistant_response(word: str, additional_instr: bool = True) -> str:
    if additional_instr:
        add_instr = 'Start your post with the subjecct word. Make sure to inclue 1-2 relevant emojis after the title word. Do not put single or double quotes around usage examples'
    thread = client.beta.threads.retrieve(thread_id = THREAD_ID)
    content = [{'type':'text','text':word}]
    messages = client.beta.threads.messages.create(thread_id = thread.id, content = content, role = 'user')
    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id=ASSISTANT_ID,
        additional_instructions=add_instr if additional_instr else NOT_GIVEN,
        stream = False,
        truncation_strategy={"type": "last_messages","last_messages": 6})
    current_status = 'queued'
    while current_status in ('queued','in_progress'):
        time.sleep(3)
        current_run = client.beta.threads.runs.retrieve(thread_id = thread.id, run_id = run.id)
        current_status = current_run.status
        print(current_status)
    messages = client.beta.threads.messages.list(thread.id)
    response = messages.data[0].content[0].text.value
    
    # chunks = []
    # for chunk in run:
    #     chunks.append(chunk)
    return response

# def get_response(word: str, bot = 'openai') -> str:
    
#     query = f'''You are asked to translate and explain the meaning of the word or phrase "{word}" to them.
# Do so in a fun and smart humored manner, so that the chances of remembering this word or phrase are increased.
# You may use a game of words, if applicable. Add 2-3 sentences describing the origin of the word, if applicable. Add a usage example. Skip all the greetings and to straight to business.
# Please end your message with tags which include the word itself and a couple of its Russian translations (remember to replace whitespaces with underscore).
# Please avoid using mentions of Russia as a country.
# Create your description in Russian, avoid making grammatical mistakes. Make sure to provide both English version and Russian translation when you are giving usage examples.
# Please follow the pattern of the below example (or stay close to it), make sure to inclue 1-2 relevant emojis after the title word:\n\n{example1}'''
    
#     messages = [
#         {'role':'system', 'content':'You are a Russian teacher who teaches English language to Russian students. Your main language of communication is Russian'},
#         {'role':'user', 'content':query}
#         ]
#     if bot == 'openai':
#         response = client.chat.completions.create(messages = messages, model = MODEL)#, stream = True)
#     # chunks = []
#     # explanation = ''
#     # for chunk in response:
#     #     if chunk.choices[0].delta.content is not None:
#     #         print(chunk.choices[0].delta.content, end = '')
#     #         chunks.append(chunk)
#     # for chunk in chunks:
#     #     explanation += chunk.choices[0].delta.content
#     else:
#         response = client2.messages.create(max_tokens = 2048, messages = messages, model = "claude-3-5-sonnet-20240620")
    
#     explanation = response.choices[0].message.content
    
#     return explanation

def check_explanation(explanation: str) -> str:
    query = f'''Please check the following text and correct any grammatical or stylistic errors.
    Do not alter the text except for the corrections you are making:\n\n{explanation}'''
    messages = [
        {'role':'system', 'content':'You are a copywriter capable of checking text and correcting mistakes.'},
        {'role':'user', 'content':query}
        ]
    
    response = client.chat.completions.create(messages = messages, model = MODEL, stream = True)
    # if response.choices[0].finish_reason == 'stop':
    #     corrected = response.choices[0].message.content
    # else:
    #     corrected = 'Error occurred'
    chunks = []
    corrected = ''
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end = '')
            chunks.append(chunk)
    for chunk in chunks:
        corrected += chunk.choices[0].delta.content        
    return corrected

def summarize(month: date):
    def extract_hashtags(text):
        pattern = r"#\w+"
        words = re.findall(pattern, text)
        return ' '.join(words) if words else nan
        
    df = connect_to_spreadsheet()
    df = df[~df['Posted on'].isin(['','cancelled, review later'])]
    df = df[['Задача', 'Posted on', 'Text']]
    df['Posted on'] = pd.to_datetime(df['Posted on'], format = '%d.%m.%Y')
    df['year'] = df['Posted on'].dt.year
    df['month'] = df['Posted on'].dt.month
    selection = df[(df['year']==month.year) & (df['month']==month.month)]
    words = selection['Text'].apply(extract_hashtags)
    summary = "Вспомним, что у нас было в январе:\n\n- " + '\n- '.join(words.values)


    chat_id = CHAT_ID
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    text_params = {'chat_id':chat_id, 'text':summary}    
    send_text = requests.post(url, params = text_params)    
    return '\n'.join(words.values)

def get_available_words(spreadsheet: pd.DataFrame) -> list:
    remaining = (spreadsheet['✓'] == 'FALSE').sum()
    spreadsheet = spreadsheet[(spreadsheet['Posted on'] == '') & (spreadsheet['Задача'] != '')]
    words = spreadsheet['Задача'].unique().tolist()
    return words, f'{remaining} objects remaining out of {len(spreadsheet)}'
    
def select_word(words: list) -> str:
    return random.choice(words).upper()

def get_audio(word: str) -> str|None:
    sound_url = f'https://d1qx7pbj0dvboc.cloudfront.net/{word.replace(" ","%20").lower()}.mp3'
    audio_check = requests.get(sound_url)
    if audio_check.ok:
        audio_str = f'🎧 [Прослушать произношение]({sound_url})'+'\n\n'
    else:
        audio_str = '\n\n'
    return audio_str
    
def structure_json(json_response):
    explanation = json_response.get('explanation')
    origin = json_response.get('origin')
    usage_examples = '\n\n'.join(['- ' + x.get('english') + '\n- ' + x.get('russian') for x in json_response.get('examples')])
    synonyms = ', '.join(json_response.get('synonyms')) if isinstance(json_response.get('synonyms'), list) else json_response.get('synonyms')
    antonyms = ', '.join(json_response.get('antonyms')) if isinstance(json_response.get('antonyms'), list) else json_response.get('antonyms')
    tags = ', '.join(json_response.get('tags')) if isinstance(json_response.get('tags'), list) else json_response.get('tags')
    return explanation, origin, usage_examples, synonyms, antonyms, tags


def process(word, window, additional_instr = True):
    window['EXPLANATION'].update('Please wait...')
    window['PROCESS'].update(disabled = True)
    json_response = assistant_response(word, additional_instr)
    json_response = json.loads(json_response)
    
    explanation, origin, usage_examples, synonyms, antonyms, tags = structure_json(json_response)
    window['EXPLANATION'].update(explanation) 
    window['ORIGIN'].update(origin) 
    window['EXAMPLES'].update(usage_examples) 
    window['MISC'].update(f'Synonyms: {synonyms}\nAntonyms: {antonyms}\nTags: {tags}')
    window['PROCESS'].update(disabled = False)
    window.write_event_value('FINISHED', json_response)
    return None
    
def post(payload, word):
    audio_str = get_audio(word)
    explanation, origin, usage_examples, synonyms, antonyms, tags = structure_json(payload)
    
    full = explanation\
        + '\n\n'\
        + origin\
        + "\n\nНапример:\n\n"\
        + usage_examples\
        + '\n\nСинонимы: ' + synonyms\
        + '\nАнтонимы: ' + antonyms + '\n\n'\
        + audio_str\
        + 'тэги: ' + tags
            
    chat_id = CHAT_ID
    text_params = {'chat_id':chat_id, 'text':full}
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    send_text = requests.post(url, params = text_params)
    
    if audio_str == '\n\n':
        image_url = generate_image(word)
        photo_params = {'chat_id':chat_id, 'photo':image_url}
        photo_url = f'https://api.telegram.org/bot{TG_TOKEN}/sendPhoto'
        send_image = requests.post(photo_url, params = photo_params)
    return None
    
       
        
def main():
    spreadsheet_btn_visibility = False if 'words' not in locals() else True
    layout = [
        [sg.Text('Explanation')],
        [sg.Multiline('', key = 'EXPLANATION', size = (80, 8)), sg.Checkbox('Rewrite', key = 'EXP_REWRITE')],
        [sg.Text('Origin')],
        [sg.Multiline('', key = 'ORIGIN', size = (80, 3)), sg.Checkbox('Rewrite', key = 'ORIG_REWRITE')],
        [sg.Text('Examples')],
        [sg.Multiline('', key = 'EXAMPLES', size = (80, 6)), sg.Checkbox('Rewrite', key = 'EXMP_REWRITE')],
        [sg.Text('Synonyms, antonyms, tags')],
        [sg.Multiline('', key = 'MISC', size = (80,3))],
        [sg.HorizontalSeparator()],
        [sg.Text('User input')],
        [sg.Multiline('', key = 'CHAT', size = (80,4),background_color='yellow'), sg.Button('Send')],
        [sg.Text('', key = 'STATS')],
        [sg.Button('Read spreadsheet', disabled=spreadsheet_btn_visibility, key = 'READ_SPREADSHEET'),
         sg.Button('Get word', disabled= not spreadsheet_btn_visibility, key = 'GET_WORD'),
         sg.Button('Post', visible = False, key = 'POST')],
        [sg.Button('Process', disabled = True, key = 'PROCESS'), sg.Button('Cancel')]
        ]
    
    window = sg.Window('English words', layout = layout, )
    
    while True:
        event, values = window.read()
        
        if event in (sg.WINDOW_CLOSED, 'Cancel'):
            break
        elif event == 'READ_SPREADSHEET':
            df = connect_to_spreadsheet()
            words, remaining = get_available_words(df)
            spreadsheet_btn_visibility = False if 'words' not in locals() else True
            window['READ_SPREADSHEET'].update('Spreadsheet done', disabled = spreadsheet_btn_visibility)
            window['GET_WORD'].update(disabled = not spreadsheet_btn_visibility)
            window['STATS'].update(remaining)
        
        elif event == 'GET_WORD':
            word = select_word(words)
            window['GET_WORD'].update(word.upper())
            window['PROCESS'].update(disabled = False)
        
        elif event == 'PROCESS':
            window.start_thread(lambda: process(word, window),('INITIAL',None))
        
        elif event == 'Send':
            rewrite_check = [rewrite_mapping[key] for key,value in values.items() if key in ('EXP_REWRITE','ORIG_REWRITE','EXMP_REWRITE') and value]
            prompt = values['CHAT']
            if len(rewrite_check) > 0:
                prompt = f'''Нужно исправить "{'" и "'.join(rewrite_check)}". Всё остальное оставь неизменённым.\n{prompt}'''
            window.start_thread(lambda: process(prompt, window, additional_instr=False),('CORRECTED',None))
        
        elif event == 'FINISHED':
            payload = values['FINISHED']
            window['POST'].update(visible = True)
        
        elif event == 'POST':
            window['POST'].update(disabled = True)
            window.start_thread(lambda: post(payload, word), ('SENDING',None))
            
    
    window.close()
if __name__ == '__main__':
    main()