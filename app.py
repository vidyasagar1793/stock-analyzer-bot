import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
import openai
import os
import re
from langchain.llms import OpenAI

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY"
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI LLM
llm = OpenAI(temperature=0, model_name="gpt-3.5-turbo-16k-0613")

# Function definitions
def get_stock_price(ticker, history=5):
    if "." in ticker:
        ticker = ticker.split(".")[0]
    ticker = ticker + ".NS"
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    df = df[["Close", "Volume"]]
    df.index = [str(x).split()[0] for x in list(df.index)]
    df.index.rename("Date", inplace=True)
    df = df[-history:]
    return df.to_string()

def google_query(search_term):
    if "news" not in search_term:
        search_term = search_term + " stock news"
    url = f"https://www.google.com/search?q={search_term}&cr=countryIN"
    url = re.sub(r"\s", "+", url)
    return url

def get_recent_stock_news(company_name):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    g_query = google_query(company_name)
    res = requests.get(g_query, headers=headers).text
    soup = BeautifulSoup(res, "html.parser")
    news = []
    for n in soup.find_all("div", "n0jPhd ynAwRc tNxQIb nDgy9d"):
        news.append(n.text)
    for n in soup.find_all("div", "IJl0Z"):
        news.append(n.text)
    if len(news) > 6:
        news = news[:4]
    news_string = "\n".join([f"{i + 1}. {n}" for i, n in enumerate(news)])
    return f"Recent News:\n\n{news_string}"

def get_financial_statements(ticker):
    if "." in ticker:
        ticker = ticker.split(".")[0]
    ticker = ticker + ".NS"
    company = yf.Ticker(ticker)
    balance_sheet = company.balance_sheet
    if balance_sheet.shape[1] >= 3:
        balance_sheet = balance_sheet.iloc[:, :3]
    balance_sheet = balance_sheet.dropna(how="any")
    return balance_sheet.to_string()

function = [
    {
        "name": "get_company_Stock_ticker",
        "description": "This will get the indian NSE/BSE stock ticker of the company",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {"type": "string", "description": "This is the stock symbol of the company."},
                "company_name": {"type": "string", "description": "This is the name of the company given in query"},
            },
            "required": ["company_name", "ticker_symbol"],
        },
    }
]

def get_stock_ticker(query):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[{"role": "user", "content": f"Given the user request, what is the comapany name and the company stock ticker ?: {query}?"}],
        functions=function,
        function_call={"name": "get_company_Stock_ticker"},
    )
    message = response["choices"][0]["message"]
    arguments = json.loads(message["function_call"]["arguments"])
    company_name = arguments["company_name"]
    company_ticker = arguments["ticker_symbol"]
    return company_name, company_ticker

def analyze_stock(query):
    company_name, ticker = get_stock_ticker(query)
    stock_data = get_stock_price(ticker, history=10)
    stock_financials = get_financial_statements(ticker)
    stock_news = get_recent_stock_news(company_name)
    available_information = f"Stock Financials: {stock_financials}\n\nStock News: {stock_news}"
    analysis = llm(
        f"Give detail stock analysis, Use the available data and provide investment recommendation. "
        f"The user is fully aware about the investment risk, don't include any kind of warning like "
        f"'It is recommended to conduct further research and analysis or consult with a financial advisor before making an investment decision' in the answer. "
        f"User question: {query}. "
        f"You have the following information available about {company_name}. "
        f"Write (5-8) pointwise investment analysis to answer user query, At the end conclude with proper explanation. "
        f"Try to give positives and negatives: {available_information}"
    )
    return analysis

# Streamlit UI
st.title("Stock Analysis Tool")
st.write("Enter your stock query below to get detailed analysis:")

user_query = st.text_input("Enter your query here:")
if st.button("Analyze"):
    if user_query:
        with st.spinner("Analyzing..."):
            analysis = analyze_stock(user_query)
            st.write("### Analysis")
            st.write(analysis)
    else:
        st.write("Please enter a query to analyze.")
