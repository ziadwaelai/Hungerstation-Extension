from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import traceback
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import concurrent.futures
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

# OpenAI Model Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2, max_tokens=100, openai_api_key=OPENAI_API_KEY)

def rewrite_description(description: str) -> str:
    if not description.strip():
        return ""

    template = ChatPromptTemplate.from_template(
        "Rewrite the following description with different words: \"{description}\" "
        "Return the rewritten description without changing the meaning and without adding new details."
    )

    chain = template | model
    response = chain.invoke({"description": description})

    return response.content if hasattr(response, "content") else response

@app.route("/create-sheet", methods=["POST"])
def create_new_sheet():
    try:
        request_data = request.json
        mode = request_data.get("mode", "full")
        sheet_name = request_data.get("sheet_name", "New Google Sheet")
        data = request_data.get("values", [])

        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Create a new Google Sheet
        new_file = drive_service.files().create(
            body={'name': sheet_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'},
            fields='id'
        ).execute()
        spreadsheet_id = new_file.get('id')

        # Set permissions to public
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"role": "writer", "type": "anyone"},
            fields="id"
        ).execute()

        # Open the new sheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.sheet1

        # Define headers based on mode
        headers = ["Title"]
        if mode != "products-only":
            headers += ["Description", "Price", "Image"]
        if mode == "full":
            headers.append("Rewritten Description")

        worksheet.append_row(headers)

        # Append data
        rows = []
        for row in data:
            new_row = [row.get("title", "")]
            if mode != "products-only":
                new_row += [row.get("description", ""), row.get("price", ""), row.get("image", "")]
            if mode == "full":
                new_row.append(rewrite_description(row.get("description", "")))
            rows.append(new_row)

        worksheet.append_rows(rows)

        return jsonify({"status": "success", "sheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"}), 200

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
