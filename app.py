import os
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "your-secret-key"  # Required for session

# Send WhatsApp Message
def send_whatsapp_message(name, std, phone, amount, sid, token, from_number):
    try:
        if not phone.startswith("whatsapp:"):
            phone = f"whatsapp:+91{phone.strip()}"
        client = Client(sid, token)
        message = (
            f"✅ *Payment Received - Kunjeer Public School* ✅\n\n"
            f"Dear Parent,\n\nWe have received ₹{amount} for *{name}* (Class: {std}).\n"
            f"Thank you for your timely payment.\n\nRegards,\nKunjeer Public School 🏫"
        )
        client.messages.create(body=message, from_=from_number, to=phone)
        print("✅ WhatsApp message sent successfully!")
    except Exception as e:
        print("⚠️ WhatsApp error:", e)

# CONFIG route
@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        # Save form-based config to session
        session['sheet_name'] = request.form.get('sheet_name')
        session['twilio_sid'] = request.form.get('twilio_sid')
        session['twilio_token'] = request.form.get('twilio_token')
        session['twilio_number'] = request.form.get('twilio_number')

        # Save uploaded credentials.json into session (as base64)
        creds_file = request.files.get('creds_file')
        if creds_file:
            creds_content = creds_file.read()
            creds_base64 = base64.b64encode(creds_content).decode('utf-8')
            session['creds_base64'] = creds_base64

        flash("✅ Configuration saved successfully.")
        return redirect(url_for('Fees_form'))

    return render_template('config.html')

# FEES FORM route
@app.route('/', methods=['GET', 'POST'])
def Fees_form():
    if request.method == 'GET':
        # Block if config missing
        if not all([
            session.get('sheet_name'),
            session.get('twilio_sid'),
            session.get('twilio_token'),
            session.get('twilio_number'),
            session.get('creds_base64')
        ]):
            flash("⚠️ Please save configuration first.")
            return redirect(url_for('config'))

    if request.method == 'POST':
        data = [
            request.form.get('student_id'),
            request.form.get('student_name'),
            request.form.get('gender'),
            request.form.get('standard'),
            request.form.get('division'),
            request.form.get('parent_email'),
            request.form.get('fee_payable'),
            request.form.get('payment_date'),
            request.form.get('payment_mode'),
            request.form.get('transaction_id'),
            request.form.get('fees_per_installment'),
            request.form.get('amount_paid'),
            request.form.get('remaining_balance'),
            request.form.get('category'),
            request.form.get('due_date'),
            request.form.get('installment'),
            request.form.get('fees_status'),
            request.form.get('remarks')
        ]

        # Restore config
        sheet_name = session.get('sheet_name')
        twilio_sid = session.get('twilio_sid')
        twilio_token = session.get('twilio_token')
        twilio_number = session.get('twilio_number')
        creds_base64 = session.get('creds_base64')

        if not all([sheet_name, twilio_sid, twilio_token, twilio_number, creds_base64]):
            return "⚠️ Missing configuration. Please re-save config.", 400

        # Write Google Sheet
        creds_content = base64.b64decode(creds_base64)
        with open("temp_creds.json", "wb") as f:
            f.write(creds_content)

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("temp_creds.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        sheet.append_row(data)
        os.remove("temp_creds.json")

        # Send WhatsApp
        send_whatsapp_message(
            name=request.form.get('student_name'),
            std=request.form.get('standard'),
            phone=request.form.get('parent_mobile'),
            amount=request.form.get('amount_paid'),
            sid=twilio_sid,
            token=twilio_token,
            from_number=twilio_number
        )

        return redirect(url_for('thank_you'))

    return render_template('form copy 3.html')

@app.route('/thanks')
def thank_you():
    return '''
    <h1 style="text-align:center; color:green;">✅ Thank you for your payment!</h1>
    <p style="text-align:center;">Your entry has been recorded in the Google Sheet.</p>
    <p style="text-align:center;"><a href="/">⬅️ Go back to form</a></p>
    '''

if __name__ == '__main__':
    app.run(debug=True)
