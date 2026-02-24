import streamlit as st
import requests
import re

# Set up the webpage interface
st.title("SOAP API Addition Calculator")
st.markdown("Powered by dneonline.com")

# Create two number input columns
col1, col2 = st.columns(2)
with col1:
    num1 = st.number_input("Number 1", value=0, step=1)
with col2:
    num2 = st.number_input("Number 2", value=0, step=1)

# Create the calculate button
if st.button("Calculate via SOAP"):
    
# 1. Prepare the API Call
    url = "http://dneonline.com/calculator.asmx"
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'http://tempuri.org/Add',
        # This new line tricks the firewall into thinking you are using Google Chrome on Windows
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    
    # We use f-strings to insert num1 and num2 directly into the XML
    payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <Add xmlns="http://tempuri.org/">
          <intA>{num1}</intA>
          <intB>{num2}</intB>
        </Add>
      </soap:Body>
    </soap:Envelope>"""

    # 2. Make the Call and Handle the Response
    try:
        with st.spinner('Calculating...'):
            response = requests.post(url, data=payload, headers=headers)
            
            if response.status_code == 200:
                # Extract the result using a regular expression
                match = re.search(r'<AddResult>(.*?)</AddResult>', response.text)
                if match:
                    result = match.group(1)
                    # Display a green success box with the answer
                    st.success(f"**Result: {result}**")
                else:
                    st.error("Error: Could not parse the XML response.")
            else:
                st.error(f"API Error! Status Code: {response.status_code}")
                
    except Exception as e:
        st.error(f"Request failed: {e}")
