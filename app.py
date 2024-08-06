from flask import Flask, request, jsonify
import os
import pymupdf
import re
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
BASE_UPLOAD_FOLDER = './receipts'
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

# Set your OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def convert_pdf_to_text(pdf_path):
    doc = pymupdf.open(pdf_path) # open a document
    result = ""
    for page in doc: # iterate the document pages
        text = page.get_text() # get plain text encoded as UTF-8
        result += f"\n\n{text}"
    return result

def parse_response(text):
    pattern = re.compile(
        r"Recipient:\s*(?P<recipient>.+?)\s*\n"
        r"Date:\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\n"
        r"Amount:\s*(?P<amount>\d+\.\d+)\s*"
    )

    match = pattern.search(text)
    if match:
        recipient = match.group("recipient")
        date = match.group("date")
        amount = match.group("amount")
        
        # Convert amount to float
        amount = float(amount)
        
        return {
            "recipient": recipient,
            "date": date,
            "amount": amount
        }
    else:
        return {
            "recipient": "Unknown",
            "date": "1970-01-01",
            "amount": 0.0
        }

def extract_info_using_gpt(text):    
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": f'''
        You are a helpful assisstant. I will give you a charitable tax receipt. Please extract the information required in the format below. Only respond in this format.

        Format:

        Recipient: <name>
        Date: <YYY-MM-DD>
        Amount: <float>
        '''},
        {"role": "user", "content": text}
    ]
    )
    
    result = completion.choices[0].message.content
    
    return parse_response(result)

def get_user_folder(year):
    user_ip = request.remote_addr.replace(':', '_')
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, str(year), user_ip)
    if os.path.exists(user_folder):
        for file in os.listdir(user_folder):
            file_path = os.path.join(user_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
    else:
        os.makedirs(user_folder)
    return user_folder

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'year' not in request.form:
        return jsonify({'error': 'No file part or year part'})
    files = request.files.getlist('file')
    year = request.form['year']
    donations = []
    user_folder = get_user_folder(year)
    
    total_amount = 0
    for file in files:
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        filename = os.path.join(user_folder, file.filename)
        file.save(filename)
        
        text = convert_pdf_to_text(filename)
        donation_details = extract_info_using_gpt(text)
        donation_details["file"] = filename
        donations.append(donation_details)
        total_amount += donation_details["amount"]
        
    summary = {
        "items": donations,
        "total_amount": total_amount
    }
    return jsonify(summary)

if __name__ == "__main__":
    app.run(debug=True)
