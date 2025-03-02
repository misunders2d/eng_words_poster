import random, gspread, os, time
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from datetime import date
from dotenv import load_dotenv
import pandas as pd
import requests, json
from numpy import nan
import re
from oauth2client.service_account import ServiceAccountCredentials

from openai import OpenAI, NOT_GIVEN, NotFoundError
# import anthropic

ASSISTANT_ID = 'asst_9RsOhqrpjyfCtKqlJQCb56Va'  
# THREAD_ID = 'thread_bkuZx2KYrj27MxilUBDmXP5x'#'thread_YfDGV3jGfkSo4pBtbkpC5CqG' - to delete

THREAD_ID = 'thread_WPMGB3p05d3CNYv4DuqtodEM' #testing thread, delete later

load_dotenv()

API_KEY = os.getenv('API_KEY')
# ANTHROPIC_KEY = os.getenv('ANTHROPIC_KEY')
MODEL = 'gpt-4o'

TG_TOKEN = os.environ['TG_TOKEN']
print(TG_TOKEN)
client = OpenAI(api_key = API_KEY)
# client2 = anthropic.Anthropic(api_key = ANTHROPIC_KEY)
CHAT_ID = "330959414"

rewrite_mapping = {
    'EXP_REWRITE': 'explanation',
    'ORIG_REWRITE': 'origin',
    'EXMP_REWRITE': 'examples'
    }

def delete_thread(thread_id):
    try:
        client.beta.threads.delete(thread_id = thread_id)
    except Exception as e:
        print(e)


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

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry('1000x800')
        self.executor = ThreadPoolExecutor()
        self.additional_instr = True
        
        self.title('English words poster')
        self.explanation_window = ctk.CTkTextbox(self, width=950)
        self.explanation_window.pack(pady=2)
        self.origin_window = ctk.CTkTextbox(self, width=950, height=100)
        self.origin_window.pack(pady=2)
        self.examples_window = ctk.CTkTextbox(self, width=950, height=100)
        self.examples_window.pack(pady=2)
        self.synonyms_window = ctk.CTkTextbox(self, width=950, height=100)
        self.synonyms_window.pack(pady=2)
        self.input_frame = ctk.CTkFrame(self, width=950, height=100)
        self.input_frame.pack()
        self.user_input = ctk.CTkTextbox(self.input_frame, width=800, height=100, fg_color='whitesmoke')
        self.user_input.pack(side='left')
        self.chat_button = ctk.CTkButton(self.input_frame, text='Send')
        self.chat_button.pack(side='right')
        self.stats = ctk.CTkLabel(self, text='Stats')
        self.stats.pack()
        self.button_frame = ctk.CTkFrame(self, width=950)
        self.button_frame.pack()

        self.spreadsheet_button = ctk.CTkButton(self.button_frame, text='Read spreadsheet', command=self.read_spreadsheet)
        self.spreadsheet_button.pack(side='left')
        self.getword_button = ctk.CTkButton(self.button_frame, text='Get word', command=self.select_word)
        self.getword_button.pack(side='left')
        self.process_button = ctk.CTkButton(self.button_frame, text='Process', fg_color='green', command = self.process)
        self.process_button.pack(side='left')
        self.post_button = ctk.CTkButton(self.button_frame, text='Post', command=self.post)
        self.post_button.pack(side='right')

    def read_spreadsheet(self):
        self.df = self.connect_to_spreadsheet()
        self.get_available_words()

    def connect_to_spreadsheet(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
            creds_file = '.secrets/token.json'
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
                client = gspread.authorize(creds)
            except Exception as e:
                print(e)
            
            #open Google Sheets sheet
            book = client.open_by_key('1TNgDtiUKNFeRDBOSrYEksArLudYhNAh-6A69O9Y9N6k')
            # book = client.open_by_url('https://docs.google.com/spreadsheets/d/1szVxXEaScCtgXgVZQhjn3KZp2zJ_KPxytWfjIVJcBhk')
            sheet = book.get_worksheet_by_id(1386834576)
            data = pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            raise Exception(e)
        return data

    def get_available_words(self):
        remaining = len(self.df[(self.df['✓'] == 'FALSE') & (self.df['Задача'] != '')])
        self.stats.configure(text=f'{remaining} objects remaining out of {len(self.df)+remaining}')
        self.df = self.df[(self.df['Posted on'] == '') & (self.df['Задача'] != '') & (self.df['✓'] == 'FALSE')]
        self.words = self.df['Задача'].unique().tolist()

    def select_word(self):
        self.word = random.choice(self.words).upper()
        self.getword_button.configure(text=self.word.upper())

    def process(self):
        self.explanation_window.insert(0.0,'Please wait...')
        self.assistant_response()
        self.json_response = json.loads(self.response)
        self.structure_json()

    def assistant_response(self) -> str:
        if self.additional_instr:
            add_instr = 'Start your post with the subject word. Make sure to inclue 1-2 relevant emojis after the title word. Do not put single or double quotes around usage examples'
        try:
            thread = client.beta.threads.retrieve(thread_id = THREAD_ID)
        except NotFoundError:
            thread = client.beta.threads.create()
        content = [{'type':'text','text':self.word}]
        messages = client.beta.threads.messages.create(thread_id = thread.id, content = content, role = 'user')
        run = client.beta.threads.runs.create_and_poll(
            thread_id = thread.id,
            assistant_id=ASSISTANT_ID,
            additional_instructions=add_instr if self.additional_instr else NOT_GIVEN,
            truncation_strategy={"type": "last_messages","last_messages": 6})
        messages = client.beta.threads.messages.list(thread.id)
        self.response = messages.data[0].content[0].text.value

    def structure_json(self):
        self.explanation = self.json_response.get('explanation')
        self.explanation_window.delete(0.0, ctk.END)
        self.explanation_window.insert(0.0, self.explanation)

        self.origin = self.json_response.get('origin')
        self.origin_window.delete(0.0, ctk.END)
        self.origin_window.insert(0.0, self.origin)

        self.usage_examples = '\n\n'.join(['- ' + x.get('english') + '\n- ' + x.get('russian') for x in self.json_response.get('examples')])
        self.examples_window.delete(0.0, ctk.END)
        self.examples_window.insert(0.0, self.usage_examples)

        self.synonyms = ', '.join(self.json_response.get('synonyms')) if isinstance(self.json_response.get('synonyms'), list) else self.json_response.get('synonyms')
        self.antonyms = ', '.join(self.json_response.get('antonyms')) if isinstance(self.json_response.get('antonyms'), list) else self.json_response.get('antonyms')
        self.tags = ', '.join(self.json_response.get('tags')) if isinstance(self.json_response.get('tags'), list) else self.json_response.get('tags')
        self.quiz_options = self.json_response.get('quiz_options')
        self.synonyms_window.delete(0.0, ctk.END)
        self.synonyms_window.insert(0.0, f'Synonyms: {self.synonyms}\nAntonyms: {self.antonyms}\nTags: {self.tags},\noptions: {','.join(self.quiz_options)}')
        
    def post(self):
        self.get_audio()
        self.structure_json()
        
        self.full_post = self.explanation\
            + '\n\n'\
            + self.origin\
            + "\n\nНапример:\n\n"\
            + self.usage_examples\
            + '\n\nСинонимы: ' + self.synonyms\
            + '\nАнтонимы: ' + self.antonyms + '\n\n'\
            + self.audio_str\
            + 'тэги: ' + self.tags\
            + "опрос: " + ', '.join(self.quiz_options)
                
        chat_id = CHAT_ID
        text_params = {'chat_id':chat_id, 'text':self.full_post}
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, params = text_params)
        
        if self.audio_str == '\n\n':
            image_url =self.generate_image(self.word)
            photo_params = {'chat_id':chat_id, 'photo':image_url}
            photo_url = f'https://api.telegram.org/bot{TG_TOKEN}/sendPhoto'
            requests.post(photo_url, params = photo_params)

    def get_audio(self):
        sound_url = f'https://d1qx7pbj0dvboc.cloudfront.net/{self.word.replace(" ","%20").lower()}.mp3'
        audio_check = requests.get(sound_url)
        if audio_check.ok:
            self.audio_str = f'🎧 [Прослушать произношение]({sound_url})'+'\n\n'
        else:
            self.audio_str = '\n\n'


    def generate_image(self) -> None:
        response = client.images.generate(
        model="dall-e-3",
        prompt=f'create an image that best describes the meaning of "{self.word}"',
        size="1024x1024",
        # size = '1792x1024',
        quality="standard",
        n=1,
        )
        image_url = response.data[0].url
        return image_url


def main():
    app = App()
    app.mainloop()
        
        
#         elif event == 'Send':
#             rewrite_check = [rewrite_mapping[key] for key,value in values.items() if key in ('EXP_REWRITE','ORIG_REWRITE','EXMP_REWRITE') and value]
#             prompt = values['CHAT']
#             if len(rewrite_check) > 0:
#                 prompt = f'''Нужно исправить "{'" и "'.join(rewrite_check)}". Всё остальное оставь неизменённым.\n{prompt}'''
#             window.start_thread(lambda: process(prompt, window, additional_instr=False),('CORRECTED',None))
        

#         elif event == 'POST':
#             window['POST'].update(disabled = True)
#             window.start_thread(lambda: post(payload, word), ('SENDING',None))
            
    
#     window.close()
if __name__ == '__main__':
    main()