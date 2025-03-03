from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import traceback
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import concurrent.futures  # For parallel processing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required API keys
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"Error: {var} is missing. Set it in your environment variables.")

print("🚀 Server starting...")

app = Flask(__name__)
print("✅ Server ready")

# Google API Credentials
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive",
          "https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build("drive", "v3", credentials=creds)

# OpenAI Model Configuration (Optimized Model)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2, max_tokens=100, openai_api_key=OPENAI_API_KEY)

def rewrite_description(description: str) -> str:
    """
    Rewrite a description using OpenAI while keeping the same meaning.
    Runs in parallel for speed optimization.
    """
    if not description.strip():  # Skip calling GPT for empty descriptions
        return ""

    template = ChatPromptTemplate.from_template(
        "Rewrite the following description with different words: \"{description}\" "
        "Return the rewritten description without changing the meaning and without adding new details. "
        "Format it as a complete sentence with proper grammar and punctuation."
    )

    chain = template | model
    response = chain.invoke({"description": description})

    return response.content if hasattr(response, "content") else response

@app.route("/create-sheet", methods=["POST"])
def create_new_sheet():
    try:
        request_data = request.json
        sheet_name = request_data.get("sheet_name", "New Google Sheet")
        data = request_data.get("values", [])

        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Step 1: Create a new Google Sheet
        spreadsheet_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        new_file = drive_service.files().create(body=spreadsheet_metadata, fields='id').execute()
        spreadsheet_id = new_file.get('id')

        # Step 2: Make the sheet publicly accessible
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"role": "writer", "type": "anyone"},
            fields="id"
        ).execute()

        # Step 3: Open the new sheet and add data
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.sheet1  # Default first sheet

        # Add headers
        worksheet.append_row(["Title", "Description", "Price", "Image", "Rewritten Description"])

        # Step 4: Process descriptions in parallel
        descriptions = [row.get("description", "") for row in data]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            rewritten_descriptions = list(executor.map(rewrite_description, descriptions))

        # Step 5: Batch append all rows to Google Sheets
        rows = [
            [row.get("title", ""), row.get("description", ""), row.get("price", ""), row.get("image", ""), rewritten_descriptions[i]]
            for i, row in enumerate(data)
        ]
        worksheet.append_rows(rows)

        # Generate sheet URL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        print(f"✅ New Google Sheet created: {sheet_url}")

        return jsonify({"status": "success", "sheetUrl": sheet_url}), 200

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
