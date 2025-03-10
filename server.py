from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import traceback
import asyncio  # Async processing for AI calls
import aiohttp  # Asynchronous HTTP requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY is missing. Set it in your environment variables.")

print("🚀 Server starting...")

app = Flask(__name__)

# Google API Credentials
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build("drive", "v3", credentials=creds)

# OpenAI Model Configuration (Optimized for Faster Processing)
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2, max_tokens=100, openai_api_key=OPENAI_API_KEY)

async def rewrite_descriptions_async(descriptions):
    """
    Asynchronously rewrite multiple descriptions using GPT-4o-mini.
    """
    async def request_rewrite(session, description):
        """
        Make an async API request for rewriting a description.
        """
        if not description.strip():
            return ""
        
        template = ChatPromptTemplate.from_template(
            "Rewrite the following description with different words: \"{description}\" "
            "Return the rewritten description without changing the meaning and without adding new details."
        )
        
        chain = template | model

        # Send API request asynchronously
        response = await asyncio.to_thread(chain.invoke, {"description": description})

        return response.content if hasattr(response, "content") else response

    async with aiohttp.ClientSession() as session:
        tasks = [request_rewrite(session, desc) for desc in descriptions]
        rewritten_descriptions = await asyncio.gather(*tasks)
    
    return rewritten_descriptions

@app.route("/create-sheet", methods=["POST"])
async def create_new_sheet():
    try:
        request_data = request.json
        mode = request_data.get("mode", "full")
        sheet_name = request_data.get("sheet_name", "New Google Sheet")
        data = request_data.get("values", [])

        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Step 1: Create a new Google Sheet
        new_file = drive_service.files().create(
            body={'name': sheet_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'},
            fields='id'
        ).execute()
        spreadsheet_id = new_file.get('id')

        # Step 2: Make the sheet publicly accessible
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"role": "writer", "type": "anyone"},
            fields="id"
        ).execute()

        # Step 3: Open the new sheet and add headers
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.sheet1

        headers = ["Title"]
        if mode != "products-only":
            headers += ["Description", "Price", "Image"]
        if mode == "full":
            headers.append("Rewritten Description")

        worksheet.append_row(headers)

        # Step 4: Process Descriptions in Parallel for Full Mode
        rows = []
        descriptions = [row.get("description", "") for row in data] if mode == "full" else []
        rewritten_descriptions = await rewrite_descriptions_async(descriptions) if mode == "full" else []

        # Step 5: Batch Write Data to Google Sheets
        for i, row in enumerate(data):
            new_row = [row.get("title", "")]
            if mode != "products-only":
                new_row += [row.get("description", ""), row.get("price", ""), row.get("image", "")]
            if mode == "full":
                new_row.append(rewritten_descriptions[i])
            rows.append(new_row)

        worksheet.append_rows(rows)  # Batch write all rows at once

        return jsonify({"status": "success", "sheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"}), 200

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
