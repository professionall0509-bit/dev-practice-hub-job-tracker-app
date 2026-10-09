import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv

load_dotenv()

# Keywords that indicate automated system emails to skip
IGNORED_SENDERS = [
    "github.com", "noreply", "no-reply", "mailer-daemon", 
    "google.com", "accounts.google", "linkedin.com/e/"
]

IGNORED_SUBJECTS = [
    "delivery status notification", "oauth", "security alert", 
    "verification code", "confirm your email", "password reset"
]

def is_relevant_email(subject, sender):
    sub_lower = subject.lower()
    sender_lower = sender.lower()

    if any(ign_s in sender_lower for ign_s in IGNORED_SENDERS):
        # Allow if it explicitly mentions application status despite no-reply
        if not any(k in sub_lower for k in ["application", "interview", "status", "offer"]):
            return False

    if any(ign_sub in sub_lower for ign_sub in IGNORED_SUBJECTS):
        return False

    return True

def fetch_job_emails(max_results=20):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        raise ValueError("Missing Gmail credentials in .env file.")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(gmail_user, gmail_password)
    mail.select("inbox")

    # Target specific job-related keywords in inbox search
    search_query = '(OR OR OR OR (SUBJECT "application") (SUBJECT "interview") (SUBJECT "offer") (SUBJECT "assessment") (SUBJECT "candidate"))'
    status, messages = mail.search(None, search_query)

    email_list = []
    if status != "OK" or not messages[0]:
        mail.logout()
        return email_list

    msg_nums = messages[0].split()[::-1]  # Latest first

    for num in msg_nums:
        if len(email_list) >= max_results:
            break

        _, msg_data = mail.fetch(num, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                subject, encoding = decode_header(msg.get("Subject", ""))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")
                
                sender = str(msg.get("From", ""))
                date = str(msg.get("Date", ""))

                # Apply local rule filter before keeping email
                if not is_relevant_email(subject, sender):
                    continue

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                            except Exception:
                                pass
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                email_list.append({
                    "id": num.decode(),
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "body": body[:1200]
                })

    mail.logout()
    return email_list