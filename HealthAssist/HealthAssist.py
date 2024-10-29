import streamlit as st
import google.generativeai as genai
import PyPDF2
import io

# Set up Google Gemini-Pro AI model
GOOGLE_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

# Set up the chat model
chat_model = genai.GenerativeModel('gemini-pro')

# Set page configuration
st.set_page_config(
    page_title="HealthAssist",
    page_icon=":hospital:",
    layout="wide"
)

# Function to translate roles between Gemini-Pro and Streamlit terminology
def translate_role_for_streamlit(user_role):
    return "assistant" if user_role == "model" else user_role

# Initialize chat session in Streamlit if not already present
if "chat_session" not in st.session_state:
    st.session_state.chat_session = chat_model.start_chat(history=[])

# Function to check if the query is medical-related using Gemini-Pro
def is_medical_query(query):
    prompt = f"""
    Determine if the following query is related to medical or health topics.
    Respond with only 'Yes' if the query is medical-related, and 'No' if it's not.
    
    Query: {query}
    Is this a medical-related query?
    """
    response = chat_model.generate_content(prompt)
    return response.text.strip().lower() == "yes"

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to summarize medical report
def summarize_medical_report(report):
    prompt = f"""
    Summarize the following medical report concisely. Focus on key findings, diagnoses, and recommendations.
    
    Medical Report:
    {report}
    
    Summary:
    """
    response = chat_model.generate_content(prompt)
    return response.text

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["ChatBot", "Medical Report Summary"])

# ChatBot interface
if page == "ChatBot":
    st.title("MedBot")

    # Display the chat history
    for message in st.session_state.chat_session.history:
        with st.chat_message(translate_role_for_streamlit(message.role)):
            st.markdown(message.parts[0].text)

    # Input field for user's message
    user_prompt = st.chat_input("Ask MedBot...")

    if user_prompt:
        # Add user's message to chat and display it
        st.chat_message("user").markdown(user_prompt)

        # Check if the query is medical-related
        if is_medical_query(user_prompt):
            # Send user's message to Gemini-Pro and get the response
            gemini_response = st.session_state.chat_session.send_message(user_prompt)
            # Display Gemini-Pro's response
            with st.chat_message("assistant"):
                st.markdown(gemini_response.text)
        else:
            # Respond with a polite message if the query is not medical-related
            with st.chat_message("assistant"):
                st.markdown("I'm here to help with medical-related questions. Please ask me about symptoms, treatments, medications, and other health-related topics.")

# Medical Report Summary interface
elif page == "Medical Report Summary":
    st.title("Medical Report Summary")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Extract text from the uploaded PDF
        pdf_text = extract_text_from_pdf(uploaded_file)
        
        if st.button("Summarize Report"):
            summary = summarize_medical_report(pdf_text)
            st.subheader("Summary:")
            st.write(summary)
            
            # Option to download the summary
            summary_download = summary.encode()
            st.download_button(
                label="Download Summary",
                data=summary_download,
                file_name="medical_report_summary.txt",
                mime="text/plain"
            )
    else:
        st.info("Please upload a PDF file to summarize.")
