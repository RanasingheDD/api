import time
from datetime import datetime
import mimetypes
import requests
from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
from supabase import create_client, Client

app = Flask(__name__)

# Supabase setup
url = "https://lofjpbnbmctceszsclzp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvZmpwYm5ibWN0Y2VzenNjbHpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQwODA5OTUsImV4cCI6MjA0OTY1Njk5NX0.KIXj0gMLkY7wwTkh1iHwRP-k4mvvnvjsHfVChVY7Fbo"
supabase: Client = create_client(url, key)

# Thresholds and suggestions (example)
THRESHOLDS = {
    "light_intensity": 200,
    "humidity": 60,
    "temperature": 30
}
SUGGESTIONS = {
    "light_intensity": "Please decrease the light intensity.",
    "humidity": "Please reduce the humidity.",
    "temperature": "Please lower the temperature."
}

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        # Get JSON data from the request
        data = request.get_json()
        room_number = data.get('room_number', 'N/A')
        date = data.get('date', 'N/A')
        time = data.get('time', 'N/A')
        details = data.get('details', [])

        # File path for the PDF
        pdf_path = "Room_Report.pdf"

        # Create the PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []

        # Add the header
        styles = getSampleStyleSheet()
        elements.append(Paragraph("<b>Room Report Summary</b>", styles['Title']))
        elements.append(Paragraph(f"Date: {date}", styles['Normal']))
        elements.append(Paragraph(f"Time: {time}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Create the detailed report table
        table_data = [["Room", "Voltage (V)", "Current (A)", "Power (W)", "Humidity (%)", "Light (lux)", "Temperature (°C)"]]
        cell_styles = []
        warnings = []

        for row_idx, row in enumerate(details, start=1):
            room = row.get('room', 'N/A')
            voltage = row.get('voltage', 'N/A')
            current = row.get('current', 'N/A')
            power = row.get('power', 'N/A')
            humidity = row.get('humidity', 'N/A')
            light_intensity = row.get('light_intensity', 'N/A')
            temperature = row.get('temperature', 'N/A')

            # Add the row to the table
            table_row = [room, voltage, current, power, humidity, light_intensity, temperature]
            table_data.append(table_row)

            # Check thresholds and highlight risk values
            if light_intensity != 'N/A' and light_intensity > THRESHOLDS["light_intensity"]:
                cell_styles.append(('TEXTCOLOR', (5, row_idx), (5, row_idx), colors.red))
                warnings.append((room, f"<font color='red'>Light intensity ({light_intensity} lux) exceeds safe level.</font>", 
                                f"<font color='green'>{SUGGESTIONS['light_intensity']}</font>"))
            if humidity != 'N/A' and humidity > THRESHOLDS["humidity"]:
                cell_styles.append(('TEXTCOLOR', (4, row_idx), (4, row_idx), colors.red))
                warnings.append((room, f"<font color='red'>Humidity ({humidity}%) exceeds safe level.</font>", 
                                f"<font color='green'>{SUGGESTIONS['humidity']}</font>"))
            if temperature != 'N/A' and temperature > THRESHOLDS["temperature"]:
                cell_styles.append(('TEXTCOLOR', (6, row_idx), (6, row_idx), colors.red))
                warnings.append((room, f"<font color='red'>Temperature ({temperature}°C) exceeds safe level.</font>", 
                                f"<font color='green'>{SUGGESTIONS['temperature']}</font>"))

        # Style the table
        table = Table(table_data, colWidths=[80] * 7, repeatRows=1)
        table_style = TableStyle([ 
            ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ] + cell_styles)
        table.setStyle(table_style)
        elements.append(table)

        # Add warnings and suggestions
        if warnings:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("<b>Warnings and Suggestions</b>", styles['Title']))
            for room, reason, suggestion in warnings:
                elements.append(Paragraph(f"<b>{room}</b>: {reason}", styles['Normal']))
                elements.append(Paragraph(f"Suggestion: {suggestion}", styles['Normal']))
                elements.append(Spacer(1, 6))

        # Build the PDF
        doc.build(elements)

        # Generate a unique filename by adding a timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        file_path = f"{timestamp}.pdf"

        # Upload the generated PDF to Supabase storage
        with open(pdf_path, "rb") as file:
            file_data = file.read()

            # The name of your Supabase bucket
            bucket_name = "reports/reports"

        headers = {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/pdf'
        }

        new_url = f'{url}/storage/v1/object/{bucket_name}/{file_path}'
        response = requests.post(new_url, headers=headers, files={'file': (file_path, file_data)})

        # Get the URL of the uploaded file
        file_url = supabase.storage.from_(bucket_name).get_public_url(file_path)

        # Return the file URL to the user (for downloading)
        return jsonify({"file_url": file_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
