# Import necessary libraries
import random

import openai
import streamlit as st
from datasets import load_dataset
from supabase import create_client

# Set API Key
openai.api_key = st.secrets["OPENAI_API_KEY"]


# Initialize DB connection once
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase = init_connection()

# System prompt for OpenAI API
system_prompt = '''You are a wine bot that helps clients understand what kind of wine they want. Given a list of wines and a description of the client, tell me what wines they want by giving me the names of the wines. Include a reason preceding each pick to explain to the user why they might like it. Give me the information  as a numbered list of wines with reasons why they might like it.'''


# Cache wine dataset once
@st.cache_resource
def load_wines():
    wine_dataset = load_dataset("alfredodeza/wine-ratings")
    return list(wine_dataset['train'])  # only use train set for now


# Convert wine to string
def convert_wine_to_string(wine):
    return f'{wine["name"]} is from {wine["region"]} and is a {wine["variety"]}. {wine["notes"]}'


# Update reaction in DB
def react_to_row(row, reaction):
    supabase.table("response").update(
        {"reaction": reaction or None}, returning="minimal"
    ).eq("id", row['id']).execute()


# User input elements
user_description = st.text_input("Describe the client",
                                 "The client likes red wine and is looking for a wine to drink with dinner.")
n = st.number_input("How many wines to pull from the cellar?", min_value=1, max_value=10, value=3, step=1)


# Function to get recommendations
def get_recommendations(n=3, user_description=''):
    wines = random.sample(load_wines(), n)
    wines_formatted = "\n---\n".join([convert_wine_to_string(w) for w in wines])
    user_prompt = f'User Description: {user_description}\nWines to select from:\n{wines_formatted}'

    # Create chat completion with OpenAI
    chat_completion = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}]
    )

    # Show the wine recommendations and store in Supabase
    st.write('Wines pulled from cellar to choose from')
    st.table(wines)

    row = supabase.table("response").insert(
        [{"system_prompt": system_prompt, "user_prompt": user_prompt,
          "response": chat_completion.choices[0].message.content, "prototype": "wine"}]
    ).execute().data[0]
    st.write(chat_completion.choices[0].message.content)
    st.session_state['row'] = row


# Button to get recommendations
st.button(
    "Get recommendations", on_click=get_recommendations,
    kwargs={'n': n, 'user_description': user_description}
)

# User reaction
reaction = st.selectbox("How do you feel about the response?", ("", "👍", "👎"))
if 'row' in st.session_state:
    st.button(
        "Submit reaction", on_click=react_to_row,
        kwargs={'row': st.session_state['row'], 'reaction': reaction}
    )
