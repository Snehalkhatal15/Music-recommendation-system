import streamlit as st
from textblob import TextBlob
import requests
import sqlite3

# === CONFIG ===
YOUTUBE_API_KEY = "AIzaSyCwIUI-LWE4NJgulgGc5-5STcwVd0iLV6A"  # Replace with your actual API key

# === Mood Tags — distinct per mood ===
MOOD_TAGS = {
    "happy": [
        "happy hindi song",
        "feel good bollywood",
        "bollywood celebration song",
        "cheerful hindi song",
        "uplifting bollywood track"
    ],
    "energetic": [
        "energetic hindi song",
        "bollywood dance song",
        "bollywood workout music",
        "bollywood party anthem",
        "high energy bollywood song"
    ],
    "melancholic": [
        "melancholic hindi song",
        "nostalgic bollywood music",
        "old hindi emotional song",
        "lonely hindi song",
        "reflective bollywood song"
    ],
    "sad": [
        "sad hindi song",
        "breakup bollywood song",
        "heartbreak hindi song",
        "emotional crying hindi song",
        "tragic bollywood song"
    ]
}

# === Session State Setup ===
st.session_state.setdefault("page", 1)
st.session_state.setdefault("last_mood", None)
st.session_state.setdefault("last_input", "")
st.session_state.setdefault("search_history", [])

# === SQLite Setup ===
conn = sqlite3.connect("music_recommendation.db", check_same_thread=False)
cursor = conn.cursor()

# Create table (if not exists)
cursor.execute("""
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT,
    mood TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Auto-upgrade: add missing columns if needed
# Add 'tag_used'
try:
    cursor.execute("ALTER TABLE search_history ADD COLUMN tag_used TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # column already exists — OK

# Add 'last_song_title'
try:
    cursor.execute("ALTER TABLE search_history ADD COLUMN last_song_title TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # column already exists — OK

# === Mood Detection ===
def detect_mood(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity >= 0.6:
        return 'happy'
    elif polarity >= 0.2:
        return 'energetic'
    elif polarity >= -0.2:
        return 'melancholic'
    else:
        return 'sad'

# === Save to DB ===
def log_search(user_input, mood, tag_used, last_song_title):
    cursor.execute("""
        INSERT INTO search_history (user_input, mood, tag_used, last_song_title)
        VALUES (?, ?, ?, ?)
    """, (user_input, mood, tag_used, last_song_title))
    conn.commit()

# === Show History ===
def show_history():
    st.subheader("📜 Your Mood Search History")
    cursor.execute("""
        SELECT user_input, mood, tag_used, last_song_title, timestamp
        FROM search_history
        ORDER BY timestamp DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        st.write(f"🕒 {row[4]} — *{row[0]}* → **{row[1]}** — Tag: `{row[2]}` — Last song: 🎵 {row[3]}")

# === YouTube Search with tags ===
def search_youtube_tags(tags, api_key, max_total_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"
    results = []

    for tag in tags:
        params = {
            "part": "snippet",
            "q": tag,
            "type": "video",
            "maxResults": 5,
            "key": api_key
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for item in data["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]

                if not any(r['video_id'] == video_id for r in results):
                    results.append({
                        "title": title,
                        "video_id": video_id
                    })

                if len(results) >= max_total_results:
                    break
        else:
            st.error(f"Failed to fetch from YouTube API for tag: {tag}")

        if len(results) >= max_total_results:
            break

    return results

# === UI ===
st.title("MOODIFY")
st.markdown("How you're feeling, and we'll recommend some Hindi songs!")

user_input = st.text_input("How are you feeling today?")

if st.button("Analyze Mood & Recommend"):
    if user_input.strip():
        mood = detect_mood(user_input)
        st.session_state["last_mood"] = mood
        st.session_state["last_input"] = user_input

        # Prepare tags for YouTube
        tags = MOOD_TAGS.get(mood, [f"{mood} hindi song"])

        # Search songs
        songs = search_youtube_tags(tags, YOUTUBE_API_KEY, max_total_results=10)

        # Pick first tag used + first song title
        tag_used = tags[0]
        last_song_title = songs[0]['title'] if songs else "None"

        # Log into DB
        log_search(user_input, mood, tag_used, last_song_title)

        st.success(f"Detected mood: **{mood}** 🎧")

        # Show songs
        st.subheader(" Recommended Songs ")
        if songs:
            for song in songs:
                st.markdown(f"**{song['title']}**")
                st.video(f"https://www.youtube.com/watch?v={song['video_id']}")
        else:
            st.warning("No songs found for this mood.")
    else:
        st.warning("Please enter something to analyze.")

# Show past search history

