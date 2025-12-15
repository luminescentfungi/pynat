# Import necessary libraries
from flask import Flask, render_template, request
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
    return render_template("card.html", card=card, MSG_TO_URL=MSG_TO_URL)

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
    
    soup_partial, _ = get_member_soup_and_text(member_id)
    if soup_partial:
            thumbnails = soup_partial.find_all('a', class_='Thumbnail')
            if thumbnails:
                try:
                    img = thumbnails[photoIndex].find('img')
                except IndexError:
                    img = thumbnails[0].find('img')
                    card['photoIndex'] = 0
                if img and img.get('src'):
                    img_path = img['src'].replace("_t", "_l")
                    photo = f"/proxy_image/{img_path}"
                    log_message(f"Found photo: {photo}", "LOG")
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
    for member_id in ids:
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
    for idx, news_block in enumerate(news_blocks[:10]):
        log_message(f"Processing news block {idx+1}", "LOG")
        onclick_attr = news_block.get('onclick', '')
        match = re.search(r'MemberShow\((\d+),', onclick_attr)
        member_id = None
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
            thumbnail = soup_partial.find('a', class_='Thumbnail')
            if thumbnail:
                img = thumbnail.find('img')
                if img and img.get('src'):
                    img_path = img['src'].replace("_t", "_l")
                    photo = f"/proxy_image/{img_path}"
                    log_message(f"Found photo: {photo}", "LOG")
        # Store card data for rendering
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
            log_message(f"Emitting new_card: {card}", "LOG")
            emit('new_card', card)
        # Emit card update with age and photo
        log_message(f"Emitting update_card for id {member_id} with age: {age}, photo: {photo}", "LOG")
        emit('update_card', {
            'id': member_id,
            'age': age,
            'photo': photo
        })

# Main entry point
if __name__ == "__main__":
    log_message("Starting Flask-SocketIO server on 0.0.0.0:5000", "LOG")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)