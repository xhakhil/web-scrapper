import streamlit as st
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Course Scraper", layout="wide")

st.title("🧠 Course Rewrite")

# ---------------------------------------------------
# PLATFORM SELECTOR
# ---------------------------------------------------

platform = st.selectbox(
    "Select Platform",
    ["Alison", "Florence", "Praxhub"]
)

# ---------------------------------------------------
# COURSE INPUT
# ---------------------------------------------------

course_url = st.text_input("Course URL")

# ---------------------------------------------------
# LOG STYLE
# ---------------------------------------------------

st.markdown("""
<style>

.log-box {
background:#0e1117;
padding:15px;
border-radius:10px;
height:350px;
overflow-y:auto;
font-family:monospace;
font-size:13px;
}

.log-info {color:#4fc3f7;}
.log-success {color:#81c784;}
.log-error {color:#ef5350;}

</style>
""", unsafe_allow_html=True)

log_container = st.empty()

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

if "running" not in st.session_state:
    st.session_state.running = False

# ---------------------------------------------------
# BUTTON
# ---------------------------------------------------

if st.session_state.running:
    st.button("⏳ Processing...", disabled=True)

else:
    if st.button("🚀 Start Scraping"):
        st.session_state.running = True
        st.rerun()

# ---------------------------------------------------
# EXECUTION
# ---------------------------------------------------

if st.session_state.running:

    progress = st.progress(0)
    stage = st.empty()

    # Pass course url to env
    os.environ["COURSE_URL"] = course_url
    os.environ["URL"] = course_url

    # Script selection
    if platform == "Praxhub":
        script = "scraper.py"
    else:
        script = "comb.py"

    process = subprocess.Popen(
        ["python", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    log_html = "<div class='log-box'>"

    for line in process.stdout:

        text = line.strip()

        # ---------------------------
        # Progress logic
        # ---------------------------

        if "starting crawler" in text.lower():
            progress.progress(10)
            stage.info("🚀 Starting crawler")

        elif "detected alison" in text.lower():
            progress.progress(25)
            stage.info("🔎 Alison course detected")

        elif "detected florence" in text.lower():
            progress.progress(25)
            stage.info("🔎 Florence course detected")

        elif "login" in text.lower():
            progress.progress(30)
            stage.info("🔐 Logging in")

        elif "opening:" in text.lower() or "opening course page" in text.lower():
            progress.progress(50)
            stage.info("📄 Scraping course pages")

        elif "download" in text.lower():
            progress.progress(65)
            stage.info("⬇ Downloading resources")

        elif "raw content saved" in text.lower():
            progress.progress(70)
            stage.info("💾 Raw content saved")

        elif "gemini" in text.lower():
            progress.progress(85)
            stage.info("🤖 Processing...")

        elif "finished" in text.lower() or "completed" in text.lower():
            progress.progress(100)
            stage.success("✅ Completed")

        # ---------------------------
        # LOG COLOR
        # ---------------------------

        if "error" in text.lower():

            log_html += f"<div class='log-error'>❌ {text}</div>"

        elif "finished" in text.lower() or "completed" in text.lower():

            log_html += f"<div class='log-success'>✅ {text}</div>"

        else:

            log_html += f"<div class='log-info'>• {text}</div>"

        log_container.markdown(
            log_html + "</div>",
            unsafe_allow_html=True
        )

    # ---------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------

    output_file = None

    if platform == "Praxhub":
        output_file = "lesson_output.txt"
    else:
        output_file = "course_rewritten.txt"

    if os.path.exists(output_file):

        with open(output_file, "r", encoding="utf8") as f:
            output = f.read()

        st.success("Processing complete")

        st.subheader("📄 Output")

        st.download_button(
            "⬇ Download Output",
            output,
            file_name=output_file
        )

        st.code(output)

    else:
        st.error("Output file not found")

    st.session_state.running = False