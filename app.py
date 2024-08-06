from flask import Flask, request, jsonify
import os
import pymupdf
import openai
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
BASE_UPLOAD_FOLDER = './receipts'
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

# Set your OpenAI API key
openai.api_key = open

def convert_pdf_to_text(pdf_path):
    doc = pymupdf.open(pdf_path) # open a document
    result = ""
    for page in doc: # iterate the document pages
        text = page.get_text() # get plain text encoded as UTF-8
        result += f"\n\n{text}"
    return result

def extract_info_using_gpt(text):
    prompt = f"Extract the following information from the text: name, date, amount. Here is the text:\n\n{text}"
    
    response = openai.Completion.create(
        model="text-davinci-004",
        prompt=prompt,
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.5,
    )
    result = response.choices[0].text.strip()
    return result

def parse_donation_details(text):
    extracted_info = extract_info_using_gpt(text)
    # You may need to process extracted_info further to format it properly
    # Assuming extracted_info is a dictionary with 'name', 'date', 'amount' keys
    return eval(extracted_info)

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
    
    for file in files:
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        filename = os.path.join(user_folder, file.filename)
        file.save(filename)
        
        text = convert_pdf_to_text(filename)
        donation_details = parse_donation_details(text)
        donation_details["file"] = filename
        donations.append(donation_details)
    
    total_amount = sum(donation["amount"] for donation in donations)
    summary = {
        "items": donations,
        "total": total_amount
    }
    return jsonify(summary)

if __name__ == "__main__":
    app.run(debug=True)
