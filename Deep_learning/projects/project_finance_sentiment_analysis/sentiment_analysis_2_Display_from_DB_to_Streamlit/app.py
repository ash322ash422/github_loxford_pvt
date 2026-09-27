import streamlit as st
import pandas as pd
# import numpy as np
from textblob import TextBlob
import plotly.express as st_px
import plotly.graph_objects as st_go
import sqlite3

DB_NAME = "news_risk.db"

# --- Page Configuration ---
st.set_page_config(page_title="News Sentiment Risk Tracker",
                   page_icon="🚨",
                   layout="wide")

# --- App Header ---
st.title("🚨 News Sentiment Risk Tracker")
st.markdown("This dashboard tracks real-time news articles, analyzes their polarity, and visualizes sentiment risk profiles.")

# Optional: cache expires every 60 seconds to check for new database updates
@st.cache_data(ttl=60)  
def fetch_news_from_db():
    """
    Retrieves all articles from the SQLite database.
    Returns: pandas.DataFrame formatted for the Streamlit app.
    """
    conn = sqlite3.connect(DB_NAME)
    
    query = """
        SELECT title, source, date, risk_score 
        FROM articles 
        ORDER BY date DESC
    """
    # pd.read_sql_query automatically converts database rows into a DataFrame
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert the date column back from string to datetime object
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        
    return df


# --- NLP Function ---
def analyze_sentiment(text):
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    # Map Polarity [-1.0, 1.0] to Risk Level [0.0 (High Pos/Low Risk), 1.0 (High Neg/High Risk)]
    risk_level = ((-polarity + 1) / 2) 
    return polarity, risk_level

# --- Load and Process Data ---
df = fetch_news_from_db()
df['Polarity'], df['Calculated Risk'] = zip(*df['title'].map(analyze_sentiment))

# --- Sidebar Controls ---
st.sidebar.header("Risk Filters")
risk_threshold = st.sidebar.slider("Maximum Permissible Sentiment Risk:", 0.0, 1.0, 1.0, 0.1)
keyword_filter = st.sidebar.text_input("Filter by Keyword:")

# Apply Filters
filtered_df = df[df['Calculated Risk'] <= risk_threshold]
if keyword_filter:
    filtered_df = filtered_df[filtered_df['title'].str.contains(keyword_filter, case=False, na=False)]

# --- Main Layout Dashboard ---
col1, col2, col3 = st.columns(3)

avg_risk = filtered_df['Calculated Risk'].mean()
avg_polarity = filtered_df['Polarity'].mean()

col1.metric("Average Sentiment Polarity", f"{avg_polarity:.2f}", 
            help="1.0 is highly positive, -1.0 is highly negative.")
col2.metric("Aggregate Sentiment Risk", f"{avg_risk * 100:.1f}%", 
            help="Higher percentage indicates higher negative sentiment risk.")
col3.metric("Articles Monitored", len(filtered_df))

st.markdown("---")

# --- Visualizations ---
c1, c2 = st.columns([2, 1])

# 1. Bubble chart for Risk Over Time
fig_timeline = st_px.scatter(
    filtered_df, x="date", y="Calculated Risk", 
    size=(filtered_df['Calculated Risk'] * 20), color="Calculated Risk",
    color_continuous_scale="Reds", hover_name="title", 
    title="News Sentiment Risk Over Time"
)
fig_timeline.update_layout(xaxis_title="Time", yaxis_title="Sentiment Risk Score")
c1.plotly_chart(fig_timeline, use_container_width=True)

# 2. Risk Gauge
risk_category = "High" if avg_risk > 0.6 else "Moderate" if avg_risk > 0.3 else "Low"
fig_gauge = st_go.Figure(st_go.Indicator(
    mode="gauge+number+delta",
    value=avg_risk * 100,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': "Current Risk Level"},
    gauge={'axis': {'range': [0, 100]},
           'bar': {'color': "darkred"},
           'steps': [
               {'range': [0, 33], 'color': "lightgreen"},
               {'range': [33, 66], 'color': "navajowhite"},
               {'range': [66, 100], 'color': "salmon"}
           ]}
))
c2.plotly_chart(fig_gauge, use_container_width=True)

# --- Data Display ---
st.markdown("### 📰 Recent News Feed")
st.dataframe(filtered_df[['title', 'source', 'date', 'Calculated Risk']], use_container_width=True)
