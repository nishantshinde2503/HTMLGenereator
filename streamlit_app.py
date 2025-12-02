import streamlit as st
from docx import Document
import re
import io
import base64

# --- Core Logic Functions ---

def extract_quiz_content_from_docx(docx_file):
    """
    Reads DOCX content from a BytesIO object (from Streamlit upload) and extracts
    quiz content based on the provided structure.

    Args:
        docx_file: A file-like object (BytesIO) of the uploaded DOCX.

    Returns:
        list: A list of cleaned strings, containing questions, options, and answers.
    """
    try:
        document = Document(docx_file)
        content_lines = []

        # Iterate through all paragraphs in the document
        for para in document.paragraphs:
            text = para.text.strip()
            if text:
                # Check for the distinct patterns based on the structure provided in the first prompt
                
                # Question lines (e.g., '1. What is...')
                if re.match(r'^\d{1,2}\. .*', text):
                    content_lines.append(text)
                
                # Answer lines (e.g., '✅ Answer: B. ...')
                elif text.startswith('✅ Answer:'):
                    content_lines.append(text)
                
                # Options (A. B. C. D. lines) or split continuations
                elif re.match(r'^[A-D]\. .*', text) or \
                     text.lower().startswith('to increase profit') or \
                     text.lower().startswith('they eliminate human') or \
                     text.lower().startswith('using encryption to'):
                    content_lines.append(text)

        return content_lines
    except Exception as e:
        st.error(f"Error reading DOCX file: {e}")
        return []

def generate_quiz_html(quiz_content_lines):
    """
    Extracts quiz questions and answers from a list of lines (from DOCX)
    and formats them into an HTML string structure.
    """
    html_output = []
    current_question = {}
    in_question_block = False
    
    i = 0
    while i < len(quiz_content_lines):
        line = quiz_content_lines[i].strip()
        
        if not line:
            i += 1
            continue

        # Start of a new question: e.g., "1. What is..."
        if re.match(r'^\d{1,2}\. .*', line):
            if in_question_block:
                # Close the previous question block
                html_output.append(f'<p><b>✔ Correct Answer</b>: {current_question["answer"]}</p>')
            
            in_question_block = True
            parts = line.split('.', 1)
            q_num = parts[0].strip()
            
            # Combine the question line with the following option line(s)
            question_block = line
            next_index = i + 1
            while next_index < len(quiz_content_lines) and not re.match(r'^\d{1,2}\. .*|✅ Answer:.*', quiz_content_lines[next_index].strip()):
                 question_block += quiz_content_lines[next_index].strip()
                 next_index += 1
            
            # Extract question text and options by splitting at the first option 'A.'
            a_pos = question_block.find("A.")
            if a_pos != -1:
                # Question text is everything between the number/dot and 'A.'
                q_text = question_block.split('.', 1)[1][:a_pos - len(question_block.split('.', 1)[0]) - 1].strip()
                options_block = question_block[a_pos:].strip()
                
                # Split options by B., C., D. while preserving A.
                options_list = re.split(r'([B-D]\. )', options_block)
                
                # Reconstruct options list properly: [A. optA, B. optB, C. optC, D. optD]
                final_options = []
                temp_opt = ""
                for item in options_list:
                    if re.match(r'^[A-D]\. ', item):
                        if temp_opt:
                            final_options.append(temp_opt.strip())
                        temp_opt = item
                    else:
                        temp_opt += item
                if temp_opt:
                    final_options.append(temp_opt.strip())

            else:
                q_text = question_block.split('.', 1)[1].strip()
                final_options = []


            current_question = {
                "number": q_num,
                "text": q_text,
                "options": final_options,
                "answer": ""
            }
            
            # HTML for Question Header
            html_output.append(f'<p>{q_num}. <b>{current_question["text"]}</b></p>')

            # HTML for Options
            for opt in current_question["options"]:
                if opt:
                    html_output.append(f'<p>• {opt}</p>')


            # Process the answer
            answer_index = next_index
            if answer_index < len(quiz_content_lines) and quiz_content_lines[answer_index].strip().startswith("✅ Answer:"):
                answer_line = quiz_content_lines[answer_index].strip()
                
                # Extract the answer text, removing "✅  Answer: X. "
                answer_text = answer_line.split(":", 1)[-1].strip()
                # Use regex to find the answer option letter and text
                match = re.match(r'([A-D]\. )?(.+)', answer_text)
                if match:
                    current_question["answer"] = answer_text
                
                # Update 'i' to the line *after* the answer
                i = answer_index
            else:
                # Update 'i' to the line *before* the next question/answer
                i = next_index - 1
        
        i += 1

    # Add the final question's answer
    if in_question_block:
        html_output.append(f'<p><b>✔ Correct Answer</b>: {current_question["answer"]}</p>')

    return '\n\n' + '\n'.join(html_output)

def generate_full_html_template(quiz_html_content):
    """Generates the full HTML file content by inserting the quiz content."""
    
    # Using f-string for template insertion, escaping CSS with double curly braces {{}}
    full_html_template = f"""
<!doctype html>
<html lang="en">

<head>

    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
    <link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;700&display=swap" rel="stylesheet">

    <style>
        img.capdevlogo {{
            position: relative;
            left: 55px;
            top: 12px;
        }}
    </style>

    <style>
        img.harbingerlogo {{
            position: relative;
            right: -450px;
            top: 11px;
        }}
    </style>
    <title> Pro Coder Quiz </title>
    <style>
        body {{
            border: 2px solid #1D3557;
            border-radius: 20px;
            margin: 30px;
            background-color: white;
            font-family: 'Red Hat Display', sans-serif;
        }}

        .logo-wrapper {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
        }}

        .title-wrapper {{
            background-color: #E63946;
            color: #fff;
            padding: 10px;
            margin-bottom: 40px;
        }}

        .title-wrapper h2 {{
            font-weight: 700;
            margin: 0;
        }}

        .congrats {{
            font-weight: 300;
            font-size: 32px;
            position: relative;
            margin-bottom: 30px;
        }}

        .congrats::after {{
            content: '';
            height: 5px;
            width: 8%;
            background-color: #E63946;
            position: absolute;
            top: calc(100% + 5px);
            border-radius: 3px;
            left: 0px;
        }}

        .text-blue {{
            color: #1D3557;
        }}
    </style>
</head>

<body>
    <div class="container">
        <div class="logo-wrapper"><img src="https://academy.harbingergroup.com/procoder/Assets/capdev.png" alt="CapDev" class="atto_image_button_left" width="126" height="52"> <img src="https://academy.harbingergroup.com/procoder/Assets/harbingerlogo.png"
                alt="Harbinger Group" class="img-responsive atto_image_button_right" width="147" height="52"></div>
    </div>
    
    <div class="title-wrapper">
        <h2 class="text-center">ProCoder Quiz Oct 2025</h2>
        <h2 class="text-center">Responsible AI and AI Guardrails</h2>
    </div>
    <div class="container">
    <p>Top 3 Winners:</p>
    <p><strong style="font-size: 0.95rem; letter-spacing: 0px;"><span>Mayuri Chaudhari,&nbsp;</span><span style="font-weight: bolder;">Deepa Menghani and&nbsp;</span></strong>
        <strong style="font-size: 0.95rem; letter-spacing: 0px;"><span>Eshan Chattaraj</span></strong>

    </p>
    <p>Congratulations!!</p>

    <p>Quiz Questions and answers are as below:</p>
    <p><br></p>

    <div class="container">
   
{quiz_html_content}

</div>

    <div class="container">
    <center>
        <footer>
            <p><i>For any queries, please write to</i> <a href="https://academy.harbingergroup.com/">capdev@harbingergroup.com</a></p>
        </footer>
    </center>
</div>
</body>
</html>
"""
    return full_html_template


# --- Streamlit UI ---

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="DOCX to HTML Quiz Converter", layout="wide")

    st.title("📄 DOCX to HTML Quiz Converter")
    st.markdown("Upload your **ProCoder Quiz DOCX** file to generate the styled HTML page.")

    # File Uploader
    uploaded_file = st.file_uploader("Upload Word File (DOCX)", type=['docx'])

    if uploaded_file is not None:
        # Read the file content into a BytesIO object for python-docx
        docx_content = io.BytesIO(uploaded_file.getvalue())
        
        # 1. Extract content
        with st.spinner('Extracting quiz content...'):
            quiz_data_lines = extract_quiz_content_from_docx(docx_content)

        if quiz_data_lines:
            # 2. Generate HTML content block
            quiz_html_content = generate_quiz_html(quiz_data_lines)
            
            # 3. Generate Full HTML file
            final_html = generate_full_html_template(quiz_html_content)

            st.success("✅ Conversion Complete!")
            
            # 4. Provide Download Button
            # Encode HTML string for download
            html_bytes = final_html.encode('utf-8')
            b64 = base64.b64encode(html_bytes).decode()
            
            download_link = f'<a href="data:file/html;base64,{b64}" download="ProCoder_Quiz_Output.html">Click to Download HTML File</a>'
            
            st.markdown(download_link, unsafe_allow_html=True)
            
            st.subheader("Preview of Generated HTML Quiz Section")
            # Display a sanitized preview for verification
            st.markdown(quiz_html_content.replace('<b>', '**').replace('</b>', '**'), unsafe_allow_html=True)

        else:
            st.warning("Could not extract quiz questions. Please ensure your DOCX file follows the expected format.")


if __name__ == "__main__":
    main()