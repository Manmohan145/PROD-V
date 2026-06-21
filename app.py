import os
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import time
import base64

# Import backend modules
from backend.detector import ObjectDetector
from backend.local_llm_service import LocalLLMService, OllamaConnectionError
from backend.image_utils import (
    validate_image_file, 
    load_image_from_bytes, 
    convert_cv2_to_pil, 
    save_uploaded_image,
    get_wikipedia_image
)
from backend.history_db import (
    save_scan, 
    get_history, 
    delete_record, 
    clear_history
)
from backend.ocr_service import OCRService
from backend.tts_service import generate_tts_html

# ----------------------------------------------------
# Page Configuration & Styling
# ----------------------------------------------------
st.set_page_config(
    page_title="VisionAI - Intelligent Object Recognition",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    .title-text {
        font-weight: 700;
        background: linear-gradient(135deg, #F97316, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle-text {
        font-size: 1.15rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    
    .sidebar-title {
        font-weight: 700;
        color: #F97316;
        font-size: 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Digital Flashcard Styling */
    .flashcard-box {
        padding: 2.5rem;
        border-radius: 12px;
        text-align: center;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-size: 1.3rem;
        font-weight: 500;
        margin-bottom: 15px;
        transition: transform 0.3s ease;
        border: 1px solid rgba(128,128,128,0.25);
    }
    .flashcard-front {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
    }
    .flashcard-back {
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.1), rgba(236, 72, 153, 0.1));
        color: #F97316;
        border: 1px solid rgba(249, 115, 22, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# Services Caching
# ----------------------------------------------------
@st.cache_resource
def load_detector_model():
    """Initializes and caches the ObjectDetector model (loads classification mode by default)."""
    detector = ObjectDetector(mode="classification")
    detector.load_model()
    return detector

@st.cache_resource
def load_llm_service():
    """Initializes and caches the LocalLLMService (Ollama)."""
    return LocalLLMService()

@st.cache_resource
def load_ocr_service():
    """Initializes and caches the OCRService."""
    return OCRService()

# Instantiate cached services
try:
    detector = load_detector_model()
    llm_service = load_llm_service()
    ocr_service = load_ocr_service()
except Exception as e:
    st.error(f"Error loading system components: {e}")
    st.stop()

# ----------------------------------------------------
# Sidebar Controls & Navigation
# ----------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">👁️ VisionAI</div>', unsafe_allow_html=True)
    st.markdown("Real-Time Intelligent Object Recognition and Learning Assistant.")
    st.markdown("---")
    
    # Page selector
    nav_selection = st.radio(
        "Choose Mode",
        options=[
            "📸 Analyze Image", 
            "📹 Live Capture", 
            "🔍 Search Object", 
            "🎓 Learning Mode",
            "📖 Text Reader & Summarizer",
            "⏳ Scan History",
            "⚖️ Compare Objects",
            "ℹ️ About & Guide"
        ],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### Settings")
    
    # 1. Vision Mode Toggle
    vision_mode = st.selectbox(
        "Vision Engine Mode",
        options=["Classification Mode", "Detection Mode"],
        index=0,
        help="Classification Mode identifies the main object. Detection Mode uses YOLOv8 to locate multiple elements."
    )
    
    # Apply selected mode to detector dynamically
    active_mode = "classification" if vision_mode == "Classification Mode" else "detection"
    if detector.mode != active_mode:
        with st.spinner(f"Loading {vision_mode} engine..."):
            detector.set_mode(active_mode)
            
    # Adjustable threshold
    confidence_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.10,
        max_value=0.90,
        value=0.25,
        step=0.05,
        help="Minimum confidence needed to display predictions."
    )
    
    # Presentation Mode Toggle
    demo_mode = st.toggle("🖥️ Enable Demo Mode", value=False, help="Display technical architecture charts and live API metrics.")
    
    st.markdown("---")
    
    # Connection Check status
    llm_service.is_configured = llm_service.check_connection()
    if llm_service.is_configured:
        st.markdown(f'<span style="color:#22C55E; font-weight:500;">🟢 Ollama Active ({llm_service.model_name})</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#EF4444; font-weight:500;">🔴 Ollama Offline</span>', unsafe_allow_html=True)
        st.warning("""
        **Ollama is not running locally!**
        
        To enable local AI assistants:
        1. Download and run **Ollama** from [ollama.com](https://ollama.com).
        2. Run this command in your terminal to pull the model:
           ```bash
           ollama run llama3.2:3b
           ```
        """)

# Initialize Session States
if "last_detected_object" not in st.session_state:
    st.session_state["last_detected_object"] = "Tiger"  # Default fallback object
if "last_confidence" not in st.session_state:
    st.session_state["last_confidence"] = 0.96
if "last_latency_ms" not in st.session_state:
    st.session_state["last_latency_ms"] = 45.0
if "last_llm_latency" not in st.session_state:
    st.session_state["last_llm_latency"] = 1.8
if "last_num_objects" not in st.session_state:
    st.session_state["last_num_objects"] = 1

# ----------------------------------------------------
# Main Process & Rendering Block
# ----------------------------------------------------
def process_and_display_results(image_bytes: bytes, filename: str):
    """Handles inference, box overlays, SQLite logging, Chat integrations, and TTS."""
    try:
        # Load and decode
        bgr_image = load_image_from_bytes(image_bytes)
        
        # Save file to uploads folder
        save_path = save_uploaded_image(image_bytes, filename)
        
        # 1. Run inference & time it
        start_time = time.perf_counter()
        with st.spinner("Executing computer vision calculations..."):
            detections = detector.detect_and_classify(bgr_image, min_confidence=confidence_threshold)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Update metrics states
        st.session_state["last_latency_ms"] = latency_ms
        st.session_state["last_num_objects"] = len(detections)
        
        if not detections:
            st.warning("No elements detected above confidence threshold. Try lowering the threshold value in the sidebar.")
            st.image(convert_cv2_to_pil(bgr_image), caption="Original Uploaded Image", width=800)
            return

        # Log highest confidence detection to scan history database
        top_det = detections[0]
        st.session_state["last_detected_object"] = top_det['label']
        st.session_state["last_confidence"] = top_det['confidence']
        save_scan(top_det['label'], top_det['confidence'], save_path)

        # 2. Bounding Box Overlay
        annotated_bgr = detector.draw_detections(bgr_image, detections)
        pil_annotated = convert_cv2_to_pil(annotated_bgr)
        
        col_img, col_info = st.columns([1.1, 0.9])
        
        with col_img:
            st.markdown("### Object Localization")
            st.image(pil_annotated, caption="Overlay Bounding Box Detections", width=800)
            
            st.markdown("#### Detected Elements")
            for det in detections:
                box_x, box_y, box_w, box_h = det['box']
                st.write(f"🟢 **{det['label']}** - {det['confidence']:.1%} confidence `[x={box_x}, y={box_y}, w={box_w}, h={box_h}]`")
                st.progress(det['confidence'])
                
            # Stats Panel
            st.markdown("---")
            st.markdown("#### 📊 Image & Inference Statistics")
            st1, st2, st3 = st.columns(3)
            st1.metric("Latency", f"{latency_ms:.1f} ms")
            st2.metric("Resolution", f"{bgr_image.shape[1]}x{bgr_image.shape[0]}")
            st3.metric("Detections", f"{len(detections)}")
            
        with col_info:
            st.markdown("### 🎓 Local LLM Knowledge Engine")
            
            # Select target label if multiple detections are present
            if len(detections) > 1:
                selected_label = st.selectbox("Explore detailed details for:", options=[d['label'] for d in detections])
            else:
                selected_label = top_det['label']
                st.markdown(f"Displaying educational details for: **{selected_label}**")

            # Fetch local LLM educational sheet
            if llm_service.check_connection():
                cache_key = f"llm_info_{selected_label.lower().replace(' ', '_')}"
                if cache_key not in st.session_state:
                    llm_start = time.perf_counter()
                    with st.spinner(f"Generating learning profile for '{selected_label}'..."):
                        try:
                            info = llm_service.generate_educational_info(selected_label)
                            st.session_state[cache_key] = info
                            st.session_state["last_llm_latency"] = time.perf_counter() - llm_start
                        except Exception as ex:
                            st.error(f"Local LLM error: {ex}")
                            st.session_state[cache_key] = None
                
                cached_info = st.session_state[cache_key]
                if cached_info:
                    with st.container(border=True):
                        st.markdown(cached_info)
                        
                    # 🔊 Read Aloud Voice Synthesis (extracts the Overview block for conciseness)
                    overview_text = ""
                    lines = cached_info.split('\n')
                    capturing = False
                    for line in lines:
                        if "overview" in line.lower():
                            capturing = True
                            continue
                        elif capturing and (line.startswith("## ") or line.startswith("### ")):
                            break
                        elif capturing:
                            overview_text += line + " "
                    
                    speech_payload = overview_text.strip() if overview_text.strip() else cached_info[:400]
                    tts_html_code = generate_tts_html(speech_payload)
                    st.markdown(tts_html_code, unsafe_allow_html=True)
            else:
                st.warning("Ollama is currently offline. Start the service on your local machine to load details.")
                with st.container(border=True):
                    st.markdown(f"### {selected_label}")
                    st.write("Identified successfully by local computer vision model.")
                    
        # 💬 Ask About This Object (Contextual Chat Interface)
        st.markdown("---")
        st.markdown(f"### 💬 Ask About This Object: {selected_label}")
        
        chat_key = f"chat_{selected_label.lower().replace(' ', '_')}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = [
                {"role": "assistant", "content": f"Hi there! I'm your local offline learning assistant. Ask me anything about the **{selected_label}**."}
            ]
            
        # Draw previous messages
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Handle new chat entries
        if chat_input := st.chat_input("Ask a question about this object...", key=f"input_{chat_key}"):
            st.session_state[chat_key].append({"role": "user", "content": chat_input})
            with st.chat_message("user"):
                st.write(chat_input)
                
            # Query local LLM with conversation context
            chat_context = f"""You are an educational tutor answering questions about the object: "{selected_label}".
            
            Conversation history:
            {chr(10).join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state[chat_key][:-1]])}
            
            User's new question: {chat_input}
            
            Provide a clear, engaging, and scientifically accurate answer in 2-3 sentences. Do not use markdown headers."""
            
            with st.chat_message("assistant"):
                with st.spinner("Formulating answer..."):
                    try:
                        reply = llm_service.generate_educational_info(chat_context)
                        st.write(reply)
                        st.session_state[chat_key].append({"role": "assistant", "content": reply})
                        st.rerun()
                    except Exception as cex:
                        st.error(f"Failed to generate answer locally: {cex}")
 
    except Exception as e:
        st.error(f"Critical analysis error occurred: {e}")

# ----------------------------------------------------
# Presentation Mode Router
# ----------------------------------------------------
def render_presentation_diagram():
    """Renders a Mermaid-based architecture diagram inside an iframe."""
    mermaid_html = """
    <div style="background-color:#0F172A; padding:15px; border-radius:8px; border:1px solid #1E293B;">
      <div class="mermaid" style="display:flex; justify-content:center;">
        graph TD
            A[Input Photo / Webcam] -->|Bytes| B[Vision Routing Model]
            B -->|MobileNetV2| C[Classification Pipeline]
            B -->|YOLOv8 Nano| D[Multi-Object Detector]
            C -->|Contours Crop| E[Labels + Conf Extraction]
            D -->|Bbox Scaling| E
            E -->|SQLite Save| F[(scan_history.db)]
            E -->|Active Selection| G[Local Ollama LLM Engine]
            G -->|Concise Markdown| H[Educational Fact Sheet]
            G -->|JSON Formatting| I[Interactive Quizzes & Flashcards]
            G -->|TTS Conversion| J[pyttsx3 Audio Controls]
      </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad:true, theme:'dark'});</script>
    """
    st.iframe(src="data:text/html;charset=utf-8," + base64.b64encode(mermaid_html.encode('utf-8')).decode('utf-8'), height=450)

def show_demo_dashboard():
    """Renders the Demo Mode overlay dashboard in the main content page."""
    st.markdown("### 🖥_ Demo Presentation Dashboard")
    col_d1, col_d2 = st.columns([1.2, 0.8])
    with col_d1:
        st.markdown("**System Architecture Pipeline Diagram**")
        render_presentation_diagram()
    with col_d2:
        st.markdown("**Live Pipeline Metrics**")
        with st.container(border=True):
            st.metric("Last Identified Object", st.session_state["last_detected_object"])
            st.metric("Inference Score", f"{st.session_state['last_confidence']:.1%}")
            st.metric("Vision Engine Latency", f"{st.session_state['last_latency_ms']:.1f} ms")
            st.metric("Local LLM Latency", f"{st.session_state['last_llm_latency']:.2f} s")
            st.metric("Detections Counter", st.session_state["last_num_objects"])
    st.markdown("---")

# ----------------------------------------------------
# Page Selection Router
# ----------------------------------------------------
st.markdown(f'<div class="title-text">VisionAI Assistant</div>', unsafe_allow_html=True)

# Show demo metrics dashboard if enabled
if demo_mode:
    show_demo_dashboard()

if nav_selection == "📸 Analyze Image":
    st.markdown('<div class="subtitle-text">Upload a photograph and discover educational insights instantly.</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Drag & Drop or Browse an Image",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG. Max file size: 10MB."
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        is_valid, err_msg = validate_image_file(uploaded_file.name, len(file_bytes))
        if not is_valid:
            st.error(err_msg)
        else:
            process_and_display_results(file_bytes, uploaded_file.name)

elif nav_selection == "📹 Live Capture":
    st.markdown('<div class="subtitle-text">Use your webcam to snap a picture of a real-world object to analyze.</div>', unsafe_allow_html=True)
    captured_file = st.camera_input("Take a Snapshot")
    if captured_file is not None:
        file_bytes = captured_file.read()
        process_and_display_results(file_bytes, "captured_snapshot.png")

elif nav_selection == "🔍 Search Object":
    st.markdown('<div class="subtitle-text">Search for any animal or object to fetch its image and detailed educational facts.</div>', unsafe_allow_html=True)
    
    search_query = st.text_input(
        "Search Name",
        placeholder="e.g., Tiger, Elephant, Smartphone, Banana",
        help="Enter any term to explore."
    ).strip()
    
    if search_query:
        st.session_state["last_detected_object"] = search_query.title()
        
        with st.spinner(f"Searching for '{search_query}' on Wikipedia..."):
            img_url, wiki_summary = get_wikipedia_image(search_query)
            
        col_img, col_info = st.columns([1.1, 0.9])
        
        with col_img:
            st.markdown("### Visual Profile")
            if img_url:
                st.image(img_url, caption=f"Wikipedia Image: '{search_query}'", width=800)
            else:
                st.info("No picture found on Wikipedia. Displaying placeholder.")
                
            if wiki_summary:
                with st.container(border=True):
                    st.markdown("#### Wikipedia Summary")
                    st.write(wiki_summary)
                    
        with col_info:
            st.markdown("### 🎓 Local LLM Knowledge Engine")
            if llm_service.check_connection():
                cache_key = f"llm_search_{search_query.lower().replace(' ', '_')}"
                if cache_key not in st.session_state:
                    with st.spinner(f"Generating educational profile..."):
                        try:
                            info = llm_service.generate_educational_info(search_query)
                            st.session_state[cache_key] = info
                        except Exception as ex:
                            st.error(f"Failed to query local LLM: {ex}")
                            st.session_state[cache_key] = None
                
                cached_info = st.session_state[cache_key]
                if cached_info:
                    with st.container(border=True):
                        st.markdown(cached_info)
            else:
                st.warning("Ollama is offline. Start the service on your local machine.")

elif nav_selection == "🎓 Learning Mode":
    st.markdown('<div class="subtitle-text">Interactive learning curriculum generated automatically by Local Ollama LLM.</div>', unsafe_allow_html=True)
    
    # Retrieve the last scanned/searched object name as default
    default_object = st.session_state.get("last_detected_object", "Tiger")
    
    # Allow user to search/input any custom object to generate curriculum for
    target_object = st.text_input(
        "Enter Object to Study",
        value=default_object,
        placeholder="e.g. Tiger, Elephant, Laptop, Smartphone",
        help="Type any object name to generate interactive quizzes, flashcards, revision notes, and viva questions."
    ).strip()
    
    if not target_object:
        st.warning("Please specify an object to generate the learning guide.")
        st.stop()
        
    st.write(f"Showing interactive learning guide for: **{target_object}**")
    
    if llm_service.check_connection():
        cache_key = f"llm_learn_{target_object.lower().replace(' ', '_')}"
        
        if (cache_key not in st.session_state or 
            not st.session_state[cache_key] or 
            "viva" not in st.session_state[cache_key] or 
            not st.session_state[cache_key]["viva"]):
            with st.spinner("Designing curriculum, flashcards, and quizzes..."):
                try:
                    learn_data = llm_service.generate_educational_data(target_object)
                    st.session_state[cache_key] = learn_data
                except Exception as ex:
                    st.error(f"Failed to generate study guide: {ex}")
                    st.session_state[cache_key] = None
                    
        data = st.session_state[cache_key]
        
        if data:
            # Create interactive tabs
            tab_quiz, tab_flash, tab_notes, tab_viva = st.tabs([
                "📝 Interactive Quiz", 
                "🎴 Digital Flashcards", 
                "📖 Quick Revision Notes", 
                "🗣️ Viva Voce Preparation"
            ])
            
            with tab_quiz:
                st.markdown("### 📝 Test Your Knowledge")
                mcqs = data.get("mcqs", [])
                
                # Render interactive quiz form
                if isinstance(mcqs, list) and mcqs:
                    valid_mcqs = [m for m in mcqs if isinstance(m, dict) and "question" in m and "options" in m and "answer" in m and isinstance(m["options"], list)]
                    if valid_mcqs:
                        user_answers = {}
                        for i, mcq in enumerate(valid_mcqs):
                            st.markdown(f"**Question {i+1}:** {mcq['question']}")
                            # Radio selector
                            user_answers[i] = st.radio(
                                f"Select answer for Q{i+1}:",
                                options=mcq["options"],
                                index=None,
                                key=f"mcq_{target_object}_{i}"
                            )
                            st.write("")
                            
                        if st.button("Submit Quiz Answers"):
                            score = 0
                            st.markdown("---")
                            st.markdown("### 📊 Quiz Results Summary")
                            for i, mcq in enumerate(valid_mcqs):
                                selected = user_answers[i]
                                # Extract option prefix (A, B, C, D)
                                correct_prefix = mcq["answer"].strip()
                                
                                # Find which option corresponds to correct prefix
                                correct_option = None
                                for opt in mcq["options"]:
                                    if opt.startswith(correct_prefix) or opt.split(".", 1)[0].strip() == correct_prefix:
                                        correct_option = opt
                                        break
                                
                                if correct_option is None:
                                    # Fallback comparison logic
                                    correct_option = mcq["options"][0] if correct_prefix == "A" else (
                                        mcq["options"][1] if correct_prefix == "B" else (
                                            mcq["options"][2] if correct_prefix == "C" else mcq["options"][3]
                                        )
                                    )
                                    
                                if selected == correct_option:
                                    score += 1
                                    st.write(f"✅ **Q{i+1} Correct!** You selected: *{selected}*")
                                elif selected is None:
                                    st.write(f"⚠️ **Q{i+1} Unanswered.** Correct Answer: **{correct_option}**")
                                else:
                                    st.write(f"❌ **Q{i+1} Incorrect.** You selected: *{selected}*. Correct Answer: **{correct_option}**")
                            st.write(f"**Final Score:** {score} / {len(valid_mcqs)} ({score/len(valid_mcqs):.0%})")
                    else:
                        st.info("Quiz questions are not formatted correctly. Please try generating again.")
                else:
                    st.info("No quiz data available.")
                    
            with tab_flash:
                st.markdown("### 🎴 Digital Flashcards")
                flashcards = data.get("flashcards", [])
                
                if isinstance(flashcards, list) and flashcards:
                    valid_flashcards = [f for f in flashcards if isinstance(f, dict) and "front" in f and "back" in f]
                    if valid_flashcards:
                        # Session state tracking for active card index and flipped status
                        if "card_idx" not in st.session_state:
                            st.session_state["card_idx"] = 0
                        if "card_flipped" not in st.session_state:
                            st.session_state["card_flipped"] = False
                            
                        # Reset indices if object changes
                        if f"last_flash_obj" not in st.session_state or st.session_state["last_flash_obj"] != target_object:
                            st.session_state["card_idx"] = 0
                            st.session_state["card_flipped"] = False
                            st.session_state["last_flash_obj"] = target_object
                            
                        idx = st.session_state["card_idx"]
                        flipped = st.session_state["card_flipped"]
                        
                        # Prevent IndexError if list indices differ between objects
                        if idx >= len(valid_flashcards):
                            idx = 0
                            st.session_state["card_idx"] = 0
                            
                        card = valid_flashcards[idx]
                        
                        # Styled flashcard display block
                        if not flipped:
                            st.markdown(f'<div class="flashcard-box flashcard-front">❓ {card["front"]}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="flashcard-box flashcard-back">💡 {card["back"]}</div>', unsafe_allow_html=True)
                            
                        col_f1, col_f2, col_f3 = st.columns([1,1,1])
                        with col_f1:
                            if st.button("⬅️ Previous Card"):
                                st.session_state["card_idx"] = (idx - 1) % len(valid_flashcards)
                                st.session_state["card_flipped"] = False
                                st.rerun()
                        with col_f2:
                            if st.button("🔄 Flip Card"):
                                st.session_state["card_flipped"] = not flipped
                                st.rerun()
                        with col_f3:
                            if st.button("➡️ Next Card"):
                                st.session_state["card_idx"] = (idx + 1) % len(valid_flashcards)
                                st.session_state["card_flipped"] = False
                                st.rerun()
                                
                        st.write(f"Card {idx+1} of {len(valid_flashcards)}")
                    else:
                        st.info("Flashcards are not formatted correctly. Please try generating again.")
                else:
                    st.info("No flashcards available.")
                    
            with tab_notes:
                st.markdown("### 📖 Quick Revision Notes")
                st.markdown(data.get("revision_notes", "No notes generated."))
                
            with tab_viva:
                st.markdown("### 🗣️ Viva Voce Preparation")
                vivas = data.get("viva", [])
                if isinstance(vivas, list) and vivas:
                    valid_vivas = [v for v in vivas if isinstance(v, dict) and "question" in v and "answer" in v]
                    if valid_vivas:
                        for i, viva in enumerate(valid_vivas):
                            with st.expander(f"Question {i+1}: {viva['question']}"):
                                st.write(viva['answer'])
                    else:
                        st.info("Viva questions are not formatted correctly. Please try generating again.")
                else:
                    st.info("No viva data available.")
    else:
        st.warning("Learning Mode requires an active local Ollama connection.")

elif nav_selection == "📖 Text Reader & Summarizer":
    st.markdown('<div class="subtitle-text">Upload book pages, documents, or notes to extract text and analyze.</div>', unsafe_allow_html=True)
    
    ocr_file = st.file_uploader(
        "Upload Document Image",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG. Max file size: 10MB."
    )
    
    if ocr_file is not None:
        file_bytes = ocr_file.read()
        is_valid, err_msg = validate_image_file(ocr_file.name, len(file_bytes))
        
        if not is_valid:
            st.error(err_msg)
        else:
            st.image(ocr_file, caption="Uploaded Document", width=800)
            
            # Run OCR extraction
            with st.spinner("Extracting text from image..."):
                try:
                    text, method = ocr_service.extract_text(file_bytes)
                    st.success(f"Text successfully extracted via: {method}")
                    
                    with st.expander("Show Extracted Raw Text"):
                        st.text_area("Extracted Text", value=text, height=250)
                        
                    # Document summarization & analysis
                    if llm_service.check_connection():
                        with st.spinner("Analyzing document structure..."):
                            analysis = ocr_service.analyze_document(text)
                        
                        st.markdown("### 📊 Document Analysis & Study Guide")
                        st.markdown(analysis)
                        
                        # Package text contents to download
                        download_data = f"VisionAI OCR Document Study Guide\nSource Method: {method}\n\n=== Raw Extracted Text ===\n{text}\n\n=== Analysis Guide ===\n{analysis}"
                        st.download_button(
                            label="📥 Download Study Guide as TXT",
                            data=download_data,
                            file_name="visionai_study_guide.txt",
                            mime="text/plain"
                        )

                        # 🔊 Text-to-Speech Assistant (Ollama Online Mode)
                        st.markdown("---")
                        st.markdown("### 🔊 Text-to-Speech Assistant")
                        tts_choice = st.radio(
                            "Select content to read aloud:",
                            options=["📋 Read AI Summary", "📝 Read Raw Extracted Text"],
                            horizontal=True,
                            key="ocr_tts_choice"
                        )
                        
                        if tts_choice == "📋 Read AI Summary":
                            # Extract summary section (usually under ## Summary header)
                            summary_text = ""
                            lines = analysis.split('\n')
                            capturing = False
                            for line in lines:
                                if "summary" in line.lower():
                                    capturing = True
                                    continue
                                elif capturing and (line.startswith("## ") or line.startswith("### ")):
                                    break
                                elif capturing:
                                    summary_text += line + " "
                            
                            speech_payload = summary_text.strip() if summary_text.strip() else analysis[:400]
                        else:
                            speech_payload = text
                            
                        if len(speech_payload) > 1500:
                            st.info("💡 Note: The selected text is long. Browser-native voice synthesis will be used to ensure smooth performance.")
                            
                        tts_html_code = generate_tts_html(speech_payload)
                        st.markdown(tts_html_code, unsafe_allow_html=True)
                    else:
                        st.info("To see automatic summaries, key terms, and sample test questions, start Ollama locally.")

                        # 🔊 Text-to-Speech Assistant (Ollama Offline Mode - Raw Text only)
                        st.markdown("---")
                        st.markdown("### 🔊 Text-to-Speech Assistant")
                        st.info("Ollama is offline. You can listen to the raw extracted text.")
                        
                        speech_payload = text
                        if len(speech_payload) > 1500:
                            st.info("💡 Note: The selected text is long. Browser-native voice synthesis will be used to ensure smooth performance.")
                            
                        tts_html_code = generate_tts_html(speech_payload)
                        st.markdown(tts_html_code, unsafe_allow_html=True)
                except Exception as ex:
                    st.error(f"OCR execution failed: {ex}")

elif nav_selection == "⏳ Scan History":
    st.markdown('<div class="subtitle-text">Previous scan analyses.</div>', unsafe_allow_html=True)
    
    # Clear history button
    if st.button("🗑️ Clear All Scan History"):
        clear_history()
        st.success("Scan history cleared successfully.")
        st.rerun()
        
    history = get_history()
    
    if not history:
        st.info("No scan logs found in the database. Scanned objects will appear here.")
    else:
        st.markdown("### SQLite Scan Records")
        for item in history:
            # HTML structure for list view
            col_thumb, col_details, col_actions = st.columns([0.4, 1.2, 0.4])
            
            with col_thumb:
                if item["thumbnail"]:
                    st.markdown(f'<img src="{item["thumbnail"]}" style="border-radius:6px; max-width:120px;" />', unsafe_allow_html=True)
                else:
                    st.info("No thumbnail")
                    
            with col_details:
                st.markdown(f"#### {item['object_name']}")
                st.write(f"🎯 **Confidence:** {item['confidence']:.1%}")
                st.write(f"📅 **Date/Time:** {item['timestamp']}")
                
            with col_actions:
                if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                    delete_record(item["id"])
                    st.success("Record deleted.")
                    st.rerun()
                if st.button("👁️ Inspect", key=f"inspect_{item['id']}"):
                    # Sets session state to reload and redirect to upload/analyze page
                    st.session_state["last_detected_object"] = item["object_name"]
                    st.session_state["last_confidence"] = item["confidence"]
                    st.success(f"Loaded '{item['object_name']}'. Navigate to Learning Mode to explore!")
            st.markdown("---")

elif nav_selection == "⚖️ Compare Objects":
    st.markdown('<div class="subtitle-text">Compare structural, ecological, or technical differences between two concepts.</div>', unsafe_allow_html=True)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        object_a = st.text_input("Object A", value="Tiger", placeholder="e.g. Tiger").strip()
    with col_c2:
        object_b = st.text_input("Object B", value="Lion", placeholder="e.g. Lion").strip()
        
    if st.button("⚖️ Compare Concepts"):
        if object_a and object_b:
            if llm_service.check_connection():
                cache_key = f"llm_compare_{object_a.lower()}_{object_b.lower()}"
                if cache_key not in st.session_state:
                    with st.spinner(f"Comparing '{object_a}' vs '{object_b}'..."):
                        try:
                            comp_res = llm_service.generate_comparison_data(object_a, object_b)
                            st.session_state[cache_key] = comp_res
                        except Exception as ex:
                            st.error(f"Failed to query local LLM comparison: {ex}")
                            st.session_state[cache_key] = None
                            
                results = st.session_state[cache_key]
                if results:
                    st.markdown("### Comparison Results")
                    st.markdown(results)
            else:
                st.warning("Comparison mode requires an active local Ollama connection.")
        else:
            st.warning("Please specify both object fields.")

elif nav_selection == "ℹ️ About & Guide":
    st.markdown('<div class="subtitle-text">Learn about the science and technology powering VisionAI.</div>', unsafe_allow_html=True)
    
    col_about_1, col_about_2 = st.columns(2)
    
    with col_about_1:
        st.markdown("""
        ### Vision Engine Architecture
        
        VisionAI operates through an adaptive dual-engine computer vision pipeline:
        
        1. **Classification Mode (MobileNetV2)**:
           * Converts image inputs to grayscale and runs a Gaussian blur.
           * Applies Canny edge filters and morphological operations to close open edges.
           * Identifies structural contours and filters regions of interest (ROIs).
           * Preprocesses ROIs and routes them to a 1,000-class **MobileNetV2** model loaded in OpenCV DNN.
        
        2. **Detection Mode (YOLOv8 Nano)**:
           * Bypasses localization preprocessing and passes full frames directly to **YOLOv8** at $640 \\times 640$.
           * Parses output bounding coordinates, class labels, and confidence grids.
           * Runs OpenCV Non-Maximum Suppression (NMS) to eliminate overlapping bounding boxes, enabling simultaneous multi-object detection.
        """)
        
    with col_about_2:
        st.markdown("""
        ### Features Instructions
        
        1. **AI Chat with Objects**:
           * Scan any image or search for an object. The interactive chat widget below allows you to ask contextual questions about it.
        2. **Educational Learning Mode**:
           * Automatically designs flashcards, quizzes, and viva lists based on your last scanned item or custom search queries.
        3. **OCR Document Understander**:
           * Extract document text using PyTesseract, and instantly compile revision notes and question lists via local Ollama.
        4. **Scan History**:
           * Records are logged in a local SQLite database with date stamps and thumbnails.
        """)
        
        st.markdown("---")
        st.markdown("### Technologies Used")
        st.code("""
- Streamlit (Web UI Framework)
- OpenCV DNN (MobileNetV2 & YOLOv8 Inference Engine)
- PyTesseract (Offline Text OCR)
- Pyttsx3 (Offline Voice Synthesis Assistant)
- SQLite3 (Scan Run Logger Database)
- Ollama (Local AI Generative Learning & Chat engine)
        """, language="text")

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #64748B; font-size: 0.85rem;">'
    'VisionAI Upgraded Suite • Built with OpenCV DNN, Local Ollama, SQLite, and Pyttsx3</div>',
    unsafe_allow_html=True
)
