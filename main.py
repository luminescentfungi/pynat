# Import necessary libraries
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import httpx, re
from bs4 import BeautifulSoup
from settings import *
from utils import *

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Store cards in a simple in-memory dict for demo purposes
cards_data = {}

# Route for the main page, renders cards if search params are present
@app.route("/")
def index():
    log_message("Rendering index page", "LOG")
    # If search params are present, trigger search and render index.html
    name = request.args.get('name')
    age_min = request.args.get('age_min')
    age_max = request.args.get('age_max')
    city = request.args.get('city')
    country = request.args.get('country')
    if any([name, age_min, age_max, city, country]):
        # Pass search params to template for JS to trigger search
        return render_template("index.html", title="Oh! Naturist News", search_params={
            'name': name or '',
            'age_min': age_min or '',
            'age_max': age_max or '',
            'city': city or '',
            'country': country or ''
        })
    return render_template("index.html", title="Oh! Naturist News", search_params=None)

# Endpoint to render a card using the card.html template
@app.route("/render_card/<member_id>")
def render_card(member_id):
    # Look up card data from the in-memory dict
    card = cards_data.get(member_id)
    if not card:
        # Fallback to empty card if not found
        card = {
            'id': member_id,
            'username': 'undefined',
            'location': 'undefined',
            'photo': '',
            'age': '',
            'photoIndex': 0
        }
    return render_template("card.html", card=card)

# Endpoint to change the card photo (left/right)
@app.route("/change_photo/<member_id>/<direction>")
def change_photo(member_id, direction):
    log_message(f"Photo change requested for member {member_id} direction {direction}", "LOG")

    # Look up card data from the in-memory dict
    card = cards_data.get(member_id)
    photoIndex = card.get('photoIndex', 0) if card else 0

    if direction not in ['left', 'right']:
        return {"error": "Invalid direction"}, 400
    if direction == 'left':
        photoIndex = max(0, photoIndex - 1)
    else:
        photoIndex += 1
    card['photoIndex'] = photoIndex
    
    photos = card.get('photos', [])
    if not 0 <= photoIndex < len(photos):
        photoIndex = 0  # Reset to first photo if out of bounds
        card['photoIndex'] = photoIndex
    photo = photos[photoIndex]
    return {"photo": photo}

# Route to proxy images from the external site
@app.route("/proxy_image/<path:img_path>")
def proxy_image(img_path):
    log_message(f"Proxying image for path: {img_path}", "LOG")
    img_url = BASE_URL + img_path
    with httpx.Client(timeout=10) as client:
        response = client.get(img_url, headers=HEADERS)
    if response.status_code == 200:
        log_message(f"Image found and returned for {img_path}", "LOG")
        return response.content, 200, {'Content-Type': 'image/jpeg'}
    log_message(f"Image not found for {img_path}", "LOG")
    return "Image not found", 404


# Route for the search page
@app.route("/search")
def search():
    log_message("Rendering search page", "LOG")
    return render_template("search.html")


# Endpoint to open a message
@app.route("/open_conversation/<member_id>")
def open_conversation(member_id):
    log_message(f"Opening conversation for member_id: {member_id}", "LOG")
    # First obtain soup and text to verify member exists
    soup_partial, text = get_member_soup_and_text(member_id)
    if not text:
        log_message(f"Member {member_id} not found", "ERR")
        return "Member not found", 404
    pattern = re.compile(
        r"KeyConversation=(\d+)"
    )
    match = pattern.search(str(soup_partial))
    if match:
        key_conversation = match.group(1)
        log_message(f"Found conversation: KeyConversation={key_conversation}", "LOG")
        url = f"{CONVERSATION_URL}{key_conversation}"
        log_message("Opening conversation URL:", url)

        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=HEADERS)
        html_content = response.text
        conversation_data = parse_conversation(html_content)

        # Extract the value of formMsg_New_KeyMessage from the HTML
        formMsg_New_KeyMessage = None
        input_elem = BeautifulSoup(html_content, "html.parser").find("input", {"name": "formMsg_New_KeyMessage"})
        if input_elem and input_elem.has_attr("value"):
            formMsg_New_KeyMessage = input_elem["value"]
        log_message(f"Key formMsg_New_KeyMessage: {formMsg_New_KeyMessage}", "DEB")

        # Extract the value of formMsg_New_Subject from the HTML
        formMsg_New_Subject = None
        input_elem_subject = BeautifulSoup(html_content, "html.parser").find("input", {"name": "formMsg_New_Subject"})
        if input_elem_subject and input_elem_subject.has_attr("value"):
            formMsg_New_Subject = input_elem_subject["value"]
        log_message(f"Key formMsg_New_Subject: {formMsg_New_Subject}", "DEB")
        
        log_message(f"Parsed conversation data for member {member_id}", "LOG")
        
        # Preparamos los mensajes para inyectar en el nuevo HTML
        messages_html_list = []
        for msg in conversation_data['messages']:
            # Creamos la estructura del mensaje para el nuevo template
            css_class = 'msg-sent' if msg['alignment'] == 'right' else 'msg-received'
            messages_html_list.append(f"""
                <div class="message-row {msg['alignment']}">
                    <div class="message-bubble {css_class}">
                        <div class="message-text">{msg['body']}</div>
                        <div class="message-time">{msg['time']}</div>
                    </div>
                </div>
            """)
        messages_html = "\n".join(messages_html_list)
        log_message(f"Rendering messenger template for member {member_id}", "DEB")
        log_message(f"Contact id: {member_id}, Contact name: {conversation_data['contact']}, Subject: {conversation_data['subject']}", "DEB")
        return render_template(
            'messenger.html',
            contact_id = member_id,
            contact_name=conversation_data['contact'],
            key_message=formMsg_New_KeyMessage,
            subject=formMsg_New_Subject,
            messages_html=messages_html
        )
    else:
        if soup_partial:
            username_container =soup_partial.find('div', id='divMemberTitle')
            if username_container:
                if '.' in username_container.get_text(strip=True):
                    username = username_container.get_text(strip=True).split('.')[-1]
                else:
                    username = username_container.get_text(strip=True)
        return render_template(
            'messenger.html',
            contact_id = member_id,
            contact_name=username if username else "Unknown",
            subject="Unknown",
            messages_html=""
        )

# SocketIO event to handle search and streaming of cards
@socketio.on('get_search_users')
def handle_get_search_users(data):
    global cards_data
    cards_data.clear()

    name = data.get('name')
    age_min = data.get('age_min')
    age_max = data.get('age_max')
    city = data.get('city')
    country = data.get('country')
    ids = get_ids_from_city(city)

    member_ids = []
    count = 0
    for member_id in ids:
        if count >= MAX_RESULTS:
            break
        soup_partial, text = get_member_soup_and_text(member_id)
        username = None
        location = None
        age = None
        photo = None

        if text:
            match_age = re.search(r'(Edad|Age|Âge|Alter|Età|Leeftijd|Возраст|年齢|나이|年龄)[^\d]{0,10}(\d{1,3})', text, re.IGNORECASE)
            if match_age:
                age = match_age.group(2)
                if age_min and int(age) < int(age_min):
                    continue
                if age_max and int(age) > int(age_max):
                    continue

        if soup_partial:
            username_container =soup_partial.find('div', id='divMemberTitle')
            if username_container:
                if '.' in username_container.get_text(strip=True):
                    username = username_container.get_text(strip=True).split('.')[-1]
                else:
                    username = username_container.get_text(strip=True)
            location_div = soup_partial.find('td', class_='MemberAddress')
            if location_div:
                location_div = location_div.find_all('a')[-1] if location_div.find_all('a') else location_div
                location = location_div.get_text(strip=True)
            thumbnail = soup_partial.find('a', class_='Thumbnail')
            if thumbnail:
                img = thumbnail.find('img')
                if img and img.get('src'):
                    img_path = img['src'].replace("_t", "_l")
                    photo = f"/proxy_image/{img_path}"
        card = {
            'id': member_id,
            'username': username or 'undefined',
            'location': location or 'undefined',
            'photo': photo or '',
            'age': age or '',
            'photoIndex': 0
        }
        cards_data[member_id] = card
        if member_id and member_id not in member_ids:
            member_ids.append(member_id)
            emit('new_card', card)
            count += 1
        emit('update_card', {
            'id': member_id,
            'age': age,
            'photo': photo
        })


# SocketIO event to handle card fetching and streaming
@socketio.on('get_new_users')
def handle_get_new_users():
    global cards_data
    log_message("Received 'get_new_users' event from client", "LOG")
    # Fetch the new members page
    with httpx.Client(timeout=10) as client:
        log_message("Fetching new members page", "LOG")
        response = client.get(NEWS_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    news_blocks = soup.find_all(class_='News')
    member_ids = []
    log_message(f"Found {len(news_blocks)} news blocks", "LOG")
    count = 0
    for idx, news_block in enumerate(news_blocks):
        if count >= MAX_RESULTS:
            break
        log_message(f"Processing news block {idx+1}", "LOG")
        onclick_attr = news_block.get('onclick', '')
        match = re.search(r'MemberShow\((\d+),', onclick_attr)
        member_id = None
        photos = []
        if match:
            member_id = match.group(1)
            log_message(f"Found member_id: {member_id}", "LOG")
        else:
            log_message("No member_id found in this block", "LOG")
            continue
        username = None
        username_container = news_block.select_one('.News_Username')
        if username_container:
            username = username_container.get_text(strip=True)
            log_message(f"Found username: {username}", "LOG")
        location = None
        location_div = news_block.select_one('.News_Address')
        if location_div:
            location = location_div.get_text(strip=True)
            log_message(f"Found location: {location}", "LOG")
        age = None
        photo = None
        log_message(f"Fetching member details for id {member_id}", "LOG")
        soup_partial, text = get_member_soup_and_text(member_id)
        if DEBUG and text and len(text) < 1000:
            log_message(f"[DEB] Partial HTML for member {member_id} (up to 1000 chars): {text[:1000]}", "DEB")
        if text:
            match_age = re.search(r'(Edad|Age|Âge|Alter|Età|Leeftijd|Возраст|年齢|나이|年龄)[^\d]{0,10}(\d{1,3})', text, re.IGNORECASE)
            if match_age:
                age = match_age.group(2)
                log_message(f"Found age: {age}", "LOG")
        if soup_partial:
            thumbnails = soup_partial.find_all('a', class_='Thumbnail')
            if thumbnails:
                imgs = [t.find('img') for t in thumbnails]
                for img in imgs:
                    if img and img.get('src'):
                        img_path = img['src'].replace("_t", "_l")
                        photos.append(f"/proxy_image/{img_path}")
                log_message(f"Found {len(photos)} photos", "LOG")
        # Store card data for rendering
        card = {
            'id': member_id,
            'username': username or 'undefined',
            'location': location or 'undefined',
            'photos': photos,
            'photo': photos[0] if photos else '',
            'age': age or '',
            'photoIndex': 0
        }
        cards_data[member_id] = card
        if member_id and member_id not in member_ids:
            member_ids.append(member_id)
            log_message(f"Emitting new_card: {card}", "LOG")
            emit('new_card', card)
            count += 1
        # Emit card update with age and photo
        log_message(f"Emitting update_card for id {member_id} with age: {age}, photo: {photo}", "LOG")
        emit('update_card', {
            'id': member_id,
            'age': age,
            'photo': photo
        })

# Endpoint to send a message to a contact
@app.route("/send_message/<contact_id>", methods=["POST"])
def send_message_route(contact_id):
    data = request.get_json()
    log_message(f"[DEBUG] Incoming POST /send_message/{contact_id} data: {data}", "DEB")
    message = data.get("message")
    subject = data.get("subject", "")
    key_message = data.get("key_message", "0")
    key_conversation = data.get("key_conversation")  # <-- Add this
    log_message(f"Sending message to contact {contact_id} with subject '{subject}' and key_message '{key_message}'", "LOG")
    if not message:
        return jsonify(success=False, error="No message provided"), 400
    try:
        resp = send_message(contact_id, message, key_message, subject, key_conversation)
        log_message(f"[DEBUG] Response from send_message: {getattr(resp, 'status_code', None)} {getattr(resp, 'text', None)}", "DEB")
        return jsonify(success=True)
    except Exception as e:
        log_message(f"Error sending message: {e}", "ERR")
        return jsonify(success=False, error=str(e)), 500

# Main entry point
if __name__ == "__main__":
    log_message("Starting Flask-SocketIO server on 0.0.0.0:5000", "LOG")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)