import os
import json
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from dotenv import load_dotenv

load_dotenv()

def analyze_email_with_agents(email_item, rag_context):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
    You are an expert HR Email Analyzer and Career Coach Agent.
    
    Email Subject: {email_item['subject']}
    Email Sender: {email_item['sender']}
    Email Content:
    {email_item['body']}

    Candidate Resume Context:
    {rag_context}

    First, decide if this email is directly related to a job application, candidate evaluation, interview request, or assessment link.
    If it is NOT job-related (e.g., delivery failure, platform update, marketing email), set "is_job_related": false.

    Return ONLY a valid JSON object matching this schema:
    {{
        "is_job_related": true or false,
        "company": "Company Name (or 'Unknown')",
        "job_title": "Position Title (or 'N/A')",
        "status": "Applied | Interview Scheduled | Assessment Sent | Action Required | Offer Received | Rejected",
        "next_steps": "Clear action item for candidate (e.g., 'Fill out form by Friday', 'Schedule call', 'None')",
        "summary": "1 concise sentence summarizing email intent"
    }}
    """

    model_name = 'gemini-3.8-flash'

    for attempt in range(3):
        try:
            print(f"  -> Sending to {model_name} (Attempt {attempt+1})...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            print(f"  -> Success!")
            return json.loads(response.text)

        except ServerError:
            print(f"  [WARN] 503 Server busy. Waiting {2**attempt}s...")
            time.sleep(2 ** attempt)

        except ClientError as e:
            err_msg = str(e)
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                print("  [ERROR] Daily API Quota Limit Reached.")
                return {
                    "is_job_related": True,
                    "company": "Quota Exceeded",
                    "job_title": "N/A",
                    "status": "Quota Exceeded",
                    "next_steps": "Gemini API daily limit reached. Try again tomorrow or upgrade API key.",
                    "summary": email_item['subject']
                }
            print(f"  [ERROR] Client error: {e}")
            break
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            break

    return {
        "is_job_related": True,
        "company": "Parse Error",
        "job_title": "N/A",
        "status": "Error",
        "next_steps": "Could not parse email content.",
        "summary": email_item['subject']
    }