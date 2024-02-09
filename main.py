# -*- coding: utf-8 -*-
"""
Created on Fri Dec 15 18:53:01 2023

@author: Sergey
"""

import random, gspread, os
from dotenv import load_dotenv
import pandas as pd
import requests
from oauth2client.service_account import ServiceAccountCredentials
import threading
from queue import Queue

from openai import OpenAI

load_dotenv()

API_KEY = os.getenv('API_KEY')
MODEL = 'gpt-4-0125-preview'

TG_TOKEN = os.getenv('TG_TOKEN')
bot = OpenAI(api_key = API_KEY)

def connect_to_spreadsheet():
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
    return data

def generate_image(word,q):
    response = bot.images.generate(
      model="dall-e-3",
      prompt=word,
      size="1024x1024",
      # size = '1792x1024',
      quality="standard",
      n=1,
    )
    
    image_url = response.data[0].url
    q.put(image_url)
    return None

def get_response(word,q):
    example = '''Here's a good example for the world "repugnance":
"Repugnance"

Слово "repugnance" в английском языке означает сильное отвращение или неприязнь к чему-либо. Это существительное передаёт чувство глубокого презрения или антипатии, которое может возникнуть в результате встречи с чем-то, что кажется отталкивающим или морально отвратительным.

В русском языке близкими по смыслу словами будут "отвращение", "неприязнь".

Пример в предложении на английском и его перевод:
- He felt a deep repugnance towards corruption.
- Он испытывал глубокое отвращение к коррупции.

Использование слова "repugnance" подразумевает не просто лёгкое раздражение, а сильное эмоциональное отторжение.

тэги: #repugnance #отвращение #неприязнь
    '''
    
    query = f'''You need to translate and explain the meaning of the word or phrase "{word}" to them. Skip all the greetings and to straight to business.
Please end your message with tags which include the word itself and a couple of its Russian translations (remember to replace whitespaces with underscore.Please avoid using mentions of Russia as a country.
Please follow the pattern of the below example:\n\n{example}'''
    
    messages = [
        {'role':'system', 'content':'You are a Russian teacher who teaches English language to Russian students.'},
        {'role':'user', 'content':query}
        ]
    
    response = bot.chat.completions.create(messages = messages, model = MODEL)
    if response.choices[0].finish_reason == 'stop':
        explanation = response.choices[0].message.content
    else:
        explanation = 'Error occurred'
    q.put(explanation)
    return None
        

def main():
    q1, q2 = Queue(), Queue()
    df = connect_to_spreadsheet()
    remaining = (df['✓'] == 'FALSE').sum()
    print(f'{remaining} objects remaining out of {len(df)}')
    df = df[df['Posted on'] == '']
    word = random.choice(df['Задача'].values.tolist())
    print(f'The word is {word.upper()}\n\n')

    image_task = threading.Thread(target = generate_image, args = (word,q1))
    word_task = threading.Thread(target = get_response, args = (word,q2))
    
    for proc in [image_task,word_task]:
        proc.start()
    
    image_url = q1.get()
    explanation = q2.get()
    
    for proc in [image_task,word_task]:
        proc.join()
    os.startfile(os.getcwd())

    split_word = 'тэги:'
    explanation1, tags = explanation.split(split_word)

    chat_id = "330959414"
    sound_url = f'https://d1qx7pbj0dvboc.cloudfront.net/{word.replace(" ","%20")}.mp3'
    audio_str = f'[Прослушать произношение]({sound_url})'
    
    audio_check = requests.get(sound_url)
    if audio_check.ok:
        text_params = {'chat_id':chat_id, 'text':explanation1 + audio_str + '\n\n' + split_word + tags}
    else:
        text_params = {'chat_id':chat_id, 'text':explanation}
    
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    send_text = requests.post(url, params = text_params)

    
    photo_params = {'chat_id':chat_id, 'photo':image_url}
    photo_url = f'https://api.telegram.org/bot{TG_TOKEN}/sendPhoto'
    send_image = requests.post(photo_url, params = photo_params)
    if send_text.ok and send_image.ok:
        print('Success')
    else:
        print('Error')
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    print('Done')

