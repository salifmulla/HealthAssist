import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
import json
from datetime import datetime

# Set up Google Gemini-Pro AI model
GOOGLE_API_KEY = "AIzaSyBgNe7hMdllxXWn3TBumP7QBzuqngqX_TY"
genai.configure(api_key=GOOGLE_API_KEY)

# Set up the chat models
chat_model = genai.GenerativeModel('gemini-pro')
advanced_chat_model = genai.GenerativeModel('gemini-pro')

# Set page configuration
st.set_page_config(
    page_title="HealthAssist",
    page_icon=":hospital:",
    layout="wide"
)

# Initialize all session states
if "chat_session" not in st.session_state:
    st.session_state.chat_session = chat_model.start_chat(history=[])
if "advanced_chat_session" not in st.session_state:
    st.session_state.advanced_chat_session = advanced_chat_model.start_chat(history=[])
if 'consultation_started' not in st.session_state:
    st.session_state.consultation_started = False
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'questions_queue' not in st.session_state:
    st.session_state.questions_queue = []
if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'diagnosis_complete' not in st.session_state:
    st.session_state.diagnosis_complete = False
if 'chief_complaint_recorded' not in st.session_state:
    st.session_state.chief_complaint_recorded = False
if 'urgent_case_handled' not in st.session_state:
    st.session_state.urgent_case_handled = False

# Function to translate roles between Gemini-Pro and Streamlit terminology
def translate_role_for_streamlit(user_role):
    return "assistant" if user_role == "model" else user_role

# Function to check if the query is medical-related using Gemini-Pro
def is_medical_query(query):
    prompt = f"""
    Determine if the following query is related to medical or health topics.
    Respond with only 'Yes' if the query is medical-related, and 'No' if it's not.
    Consider as medical if it includes:
    - Symptoms or health conditions
    - Medical procedures or treatments
    - Health-related questions
    - Body parts or bodily functions
    - Medications or medical devices
    
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
    Summarize the following medical report accurately and concisely in simple and few medical terms so that even a person without medical knowledge should understand it. 
    Focus on key findings, diseases, and recommendations as the 3 main sections.
    Avoid using complex medical terms and do not include the patient's personal information.
    Furthermore in the disease section, include the name of the disease and explain it in one sentence to make a normal human understand. 
    
    Medical Report:
    {report}
    
    Summary:
    """
    response = chat_model.generate_content(prompt)
    return response.text

# Function to check if PDF content is a medical report
def is_medical_report(text):
    prompt = f"""
    Determine if the following content is from a medical report. Respond with 'Yes' if it is a medical report, and 'No' if it is not.
    
    Content: {text[:500]}  # Checking only the beginning of the text for efficiency
    Is this a medical report?
    """
    response = chat_model.generate_content(prompt)
    return response.text.strip().lower() == "yes"

# Function to check for urgent symptoms and generate immediate response
def check_urgent_symptoms(text):
    prompt = f"""
    As a medical professional, analyze this patient's response for ANY potentially urgent or emergency symptoms:
    "{text}"
    
    Check for red flags including but not limited to:
    - Severe chest pain or pressure
    - Difficulty breathing
    - Signs of stroke (facial drooping, arm weakness, speech difficulty)
    - Severe abdominal pain
    - Signs of severe infection or sepsis
    - Suicidal thoughts or severe mental health crisis
    - Severe allergic reactions
    - Head injuries with concerning symptoms
    - Severe bleeding
    - Loss of consciousness
    
    Return ONLY a JSON object with this exact format:
    {{
        "is_urgent": true/false,
        "condition": "Name of the suspected emergency condition",
        "immediate_action": "Specific immediate actions to take",
        "emergency_response": "Detailed emergency guidance including what to do and where to go",
        "additional_instructions": "Any additional safety measures or precautions"
    }}
    """
    
    response = advanced_chat_model.generate_content(prompt)
    try:
        result = json.loads(response.text)
        return result["is_urgent"], result if result["is_urgent"] else None
    except:
        return False, None

def generate_emergency_response(emergency_data):
    """Format emergency response for display"""
    return f"""
    # EMERGENCY MEDICAL SITUATION DETECTED
    
    ## Suspected Condition
    {emergency_data['condition']}
    
    ## IMMEDIATE ACTION REQUIRED
    {emergency_data['immediate_action']}
    
    ## Emergency Response Instructions
    {emergency_data['emergency_response']}
    
    ## Additional Instructions
    {emergency_data['additional_instructions']}
    
    ⚠️ This AI system is not a substitute for emergency medical care.
    🚑 Please seek immediate medical attention as advised above.
    """

def get_initial_question():
    return "Hello there. Please describe your main symptoms/situation."

def generate_follow_up_questions(complaint):
    prompt = f"""
    As a medical doctor, analyze this chief complaint and generate follow-up questions.
    Chief complaint: {complaint}
    
    Generate 4-5 specific, relevant follow-up questions to aid diagnosis.
    Each question should:
    1. Be specific and require a direct answer
    2. Help narrow down the diagnosis
    3. Cover different aspects (duration, severity, triggers, associated symptoms, etc.)
    
    Return ONLY a JSON array of questions, like:
    ["question1", "question2", ...]
    """
    response = advanced_chat_model.generate_content(prompt)
    try:
        questions = json.loads(response.text)
        questions.append("Have you experienced any other symptoms or is there anything else you'd like to tell me?")
        return questions
    except:
        return ["How long have you had these symptoms?", 
                "Can you rate the severity from 1-10?",
                "What makes it better or worse?",
                "Have you experienced any other symptoms?"]

def get_next_dynamic_question(conversation_history):
    """Generate a dynamic follow-up question based on previous responses"""
    prompt = f"""
    As a medical doctor, review this conversation history and generate the most relevant next question.
    
    Conversation:
    {conversation_history}
    
    Generate ONE specific follow-up question that:
    1. Builds on the information already provided
    2. Doesn't repeat anything already asked
    3. Helps clarify the diagnosis
    
    Return ONLY the question text, nothing else.
    """
    response = advanced_chat_model.generate_content(prompt)
    return response.text.strip()

def generate_diagnosis(history):
    prompt = f"""
    As a medical doctor, analyze this consultation:
    {history}
    
    Provide a structured assessment with:
    1. Provisional diagnosis (2-3 possibility)
    2. Reasoning behind this diagnosis
    3. Recommended next steps (tests/treatments)
    4. Important precautions
    5. When to seek immediate medical attention
    
    Format in clear sections with markdown headings.
    """
    response = advanced_chat_model.generate_content(prompt)
    return response.text

# Main interface
st.title("🏥 HealthAssist")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["MedBot", "AI Medical Consultation", "Medical Report Summary"])

# ChatBot interface
if page == "MedBot":
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

# Advanced Medical Chatbot interface
elif page == "AI Medical Consultation":
    st.title("AI Medical Consultation")

    # Status in sidebar
    with st.sidebar:
        st.header("📋 Consultation Status")
        if st.session_state.consultation_started:
            if not st.session_state.diagnosis_complete:
                st.info("Consultation in progress...")
            else:
                st.success("Consultation complete!")

    # Start New Consultation button
    if st.button("Start New Consultation", use_container_width=True):
        st.session_state.consultation_started = True
        st.session_state.current_question_index = 0
        st.session_state.questions_queue = []
        st.session_state.patient_info = {}
        st.session_state.conversation_history = []
        st.session_state.diagnosis_complete = False
        st.session_state.chief_complaint_recorded = False
        st.session_state.urgent_case_handled = False
        st.rerun()

    # Main consultation flow
    if st.session_state.consultation_started:
        # Display conversation history
        for message in st.session_state.conversation_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        # Handle consultation flow
        if not st.session_state.diagnosis_complete:
            # Initial question if conversation just started
            if len(st.session_state.conversation_history) == 0:
                initial_question = get_initial_question()
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": initial_question
                })
                st.rerun()

            # Get user input
            user_input = st.chat_input("Your response...")
            
            if user_input:
                # Check if the input is medical-related when recording chief complaint
                if not st.session_state.chief_complaint_recorded:
                    if not is_medical_query(user_input):
                        st.session_state.conversation_history.append({
                            "role": "user",
                            "content": user_input
                        })
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": "I apologize, but I can only help with medical-related concerns. Please describe your medical symptoms or health-related issues."
                        })
                        st.rerun()

                # Add user response to history
                st.session_state.conversation_history.append({
                    "role": "user",
                    "content": user_input
                })

                # Check for urgent symptoms if this is the chief complaint
                if not st.session_state.chief_complaint_recorded:
                    is_urgent, emergency_data = check_urgent_symptoms(user_input)
                    
                    if is_urgent and not st.session_state.urgent_case_handled:
                        # Generate and display emergency response
                        emergency_response = generate_emergency_response(emergency_data)
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": emergency_response
                        })
                        st.session_state.urgent_case_handled = True
                        st.session_state.diagnosis_complete = True
                        st.rerun()
                    
                    # Continue with normal flow if not urgent
                    st.session_state.patient_info["chief_complaint"] = user_input
                    st.session_state.chief_complaint_recorded = True
                    st.session_state.questions_queue = generate_follow_up_questions(user_input)
                    
                    if st.session_state.questions_queue and not st.session_state.urgent_case_handled:
                        next_question = st.session_state.questions_queue[0]
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": next_question
                        })

                # Handle follow-up questions
                elif not st.session_state.urgent_case_handled:
                    # Store response
                    question = st.session_state.conversation_history[-2]["content"]
                    st.session_state.patient_info[f"response_{st.session_state.current_question_index}"] = {
                        "question": question,
                        "answer": user_input
                    }

                    st.session_state.current_question_index += 1

                    # Check if we have more questions in queue
                    if st.session_state.current_question_index < len(st.session_state.questions_queue):
                        next_question = st.session_state.questions_queue[st.session_state.current_question_index]
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": next_question
                        })
                    else:
                        # Generate diagnosis
                        diagnosis = generate_diagnosis(str(st.session_state.conversation_history))
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": f"Based on our consultation, here is my assessment:\n\n{diagnosis}"
                        })
                        st.session_state.diagnosis_complete = True

                st.rerun()

        # Show download button when complete
        if st.session_state.diagnosis_complete:
            consultation_text = "\n\n".join([
                f"{message['role'].upper()}: {message['content']}" 
                for message in st.session_state.conversation_history
            ])
            
            st.download_button(
                label="💾 Download Consultation Summary",
                data=consultation_text,
                file_name=f"medical_consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    else:
        st.info("Click 'Start New Consultation' above to begin")

# Medical Report Summary interface
elif page == "Medical Report Summary":
    st.title("Medical Report Summary")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Extract text from the uploaded PDF
        pdf_text = extract_text_from_pdf(uploaded_file)
        
        # Check if the content is a medical report
        if is_medical_report(pdf_text):
            if st.button("Summarize Report"):
                summary = summarize_medical_report(pdf_text)
                st.subheader("Summary:")
                st.write(summary)
                st.write("**Note: Patient's personal information cannot be accessed for privacy and security reasons.**")
                # Option to download the summary
                summary_download = summary.encode()
                st.download_button(
                    label="Download Summary",
                    data=summary_download,
                    file_name="medical_report_summary.txt",
                    mime="text/plain"
                )
        else:
            st.warning("The uploaded file does not appear to be a medical report. Please upload a valid medical report.")
    else:
        st.info("Please upload a PDF file to summarize.")