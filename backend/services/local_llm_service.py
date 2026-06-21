import os
import json
import hashlib
import time
import socket
from dotenv import load_dotenv
import ollama
from ollama import Client

load_dotenv()

class OllamaConnectionError(Exception):
    """Custom exception raised when Ollama service is not running or unreachable."""
    pass

class LocalLLMService:
    def __init__(self):
        """Initializes the LocalLLMService with configurations and cache."""
        # Read from environment variables, fallback to defaults
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Parse Host IP/Port for a quick socket pre-check (avoids long http timeouts)
        self.host_ip, self.host_port = self._parse_host(self.host)
        
        # Setup Ollama client with a timeout (default 45s to avoid UI freeze)
        self.timeout = 45.0
        self.client = Client(host=self.host, timeout=self.timeout)
        
        # Local Persistent Cache File Setup
        self.cache_file = os.path.join(os.path.dirname(__file__), "..", "..", "llm_cache.json")
        self.cache = self._load_cache()
        
        # Verify connection on startup
        self.is_configured = self.check_connection()

    def _parse_host(self, host_str: str) -> tuple[str, int]:
        """Parses a host string into (ip_or_domain, port)."""
        clean = host_str.replace("http://", "").replace("https://", "")
        if ":" in clean:
            parts = clean.split(":")
            try:
                return parts[0], int(parts[1])
            except ValueError:
                pass
        return "127.0.0.1", 11434

    def check_connection(self) -> bool:
        """
        Fast socket connection check followed by an API call verification.
        Returns True if Ollama service is running and responsive.
        """
        # 1. Quick Socket Check (non-blocking, fast fail if service is down)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((self.host_ip, self.host_port))
            sock.close()
            if result != 0:
                return False
        except Exception:
            return False

        # 2. HTTP Client Verification
        try:
            # Quick ping using list models (very fast)
            self.client.list()
            return True
        except Exception:
            return False

    def _load_cache(self) -> dict:
        """Loads persistent JSON cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading LLM cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """Saves current cache states to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving LLM cache: {e}")

    def _get_cache_key(self, prefix: str, query: str) -> str:
        """Generates a key for cache. Uses MD5 hash for longer query strings (like OCR texts)."""
        clean_q = query.strip().lower()
        if len(clean_q) > 60:
            md5_hash = hashlib.md5(clean_q.encode("utf-8")).hexdigest()
            return f"{prefix}:hash:{md5_hash}"
        return f"{prefix}:{clean_q.replace(' ', '_')}"

    def _strip_code_fences(self, content: str) -> str:
        """Strips markdown code fences from LLM JSON responses."""
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()


    def generate_object_knowledge(self, object_name: str) -> str:
        """
        Generates structured markdown educational details for an identified object.
        
        Args:
            object_name (str): Label of the target object.
            
        Returns:
            str: Markdown formatted fact sheet.
        """
        # Determine if this is a chat context instead of a simple object name
        is_chat = "User's new question:" in object_name or "Conversation history:" in object_name
        prefix = "chat" if is_chat else "info"
        
        cache_key = self._get_cache_key(prefix, object_name)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Double check connection
        if not self.check_connection():
            raise OllamaConnectionError(
                "Ollama is offline. Please make sure the Ollama application is running."
            )

        if is_chat:
            # Contextual chat query logic
            prompt = object_name
        else:
            # Fact sheet prompt logic
            prompt = f"""You are an expert educational computer vision assistant.
Provide highly detailed, comprehensive, and in-depth educational information about the object: "{object_name}". Make sure each section is thorough, descriptive, and intellectually stimulating, offering a complete learning profile.

Please format your response using EXACTLY the following structure with the exact headers listed below. 
Do not include conversational filler, greetings, or intro lines. Begin directly with the headers.

## Overview
Provide a rich, detailed overview (4-5 sentences) of what the object is, its history, primary function, and scientific or cultural significance.

## Category
Specify the scientific classification, detailed taxonomy, and common industry or academic category of this object.

## Key Characteristics
Provide a detailed list of 4-5 primary characteristics, with explanations of their physical traits, material science components, or technical specifications.

## Common Uses
Explain in detail the primary applications, case studies, and environments where this object is most commonly utilized.

## Interesting Facts
Include 3 surprising, historical, or advanced scientific facts about the object that a student would find memorable.

## Educational Notes
A dedicated, comprehensive learning section. Explain in depth a relevant scientific concept, engineering principle, historical milestone, or design philosophy related to this object.
"""

        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3 if is_chat else 0.5,
                    "top_p": 0.9,
                }
            )
            text_result = response["response"].strip()
            
            # Clean up response chat headings if present
            if is_chat:
                text_result = text_result.replace("## Overview\n", "").strip()

            self.cache[cache_key] = text_result
            self._save_cache()
            return text_result

        except Exception as e:
            raise Exception(f"Local LLM Error during generation: {str(e)}")

    # Alias to retain compatibility with UI calls
    generate_educational_info = generate_object_knowledge

    def generate_educational_data(self, object_name: str) -> dict:
        """
        Generates structured JSON data for interactive quizzes, flashcards, revision notes, and viva list.
        
        Args:
            object_name (str): Label of the target object.
            
        Returns:
            dict: Parsed study materials matching the required schema.
        """
        cache_key = self._get_cache_key("learn", object_name)
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            
            # Validate structure and heal malformed data
            cached_data, needs_update = self._validate_and_heal_educational_data(cached_data, object_name)
            
            if needs_update:
                self.cache[cache_key] = cached_data
                self._save_cache()
                
            return cached_data

        if not self.check_connection():
            raise OllamaConnectionError(
                "Ollama is offline. Please make sure the Ollama application is running."
            )

        prompt = f"""You are an expert curriculum designer and teacher. 
Generate a comprehensive, interactive learning guide for the object/animal: "{object_name}".

You MUST return your entire response as a single valid JSON object. Do not write any conversational intro or outro text.
The JSON structure MUST follow this exact schema:

{{
    "full_explanation": "A highly detailed, comprehensive markdown explanation (500-600 words) breaking down the concept/object, its core principles, theoretical foundations, historical context, and modern real-world applications.",
    "mcqs": [
        {{
            "question": "Clear multiple choice question 1?",
            "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "answer": "A"
        }},
        {{
            "question": "Clear multiple choice question 2?",
            "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "answer": "B"
        }},
        {{
            "question": "Clear multiple choice question 3?",
            "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "answer": "C"
        }},
        {{
            "question": "Clear multiple choice question 4?",
            "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "answer": "D"
        }},
        {{
            "question": "Clear multiple choice question 5?",
            "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "answer": "A"
        }}
    ],
    "flashcards": [
        {{
            "front": "Question/Term for front of flashcard 1?",
            "back": "Answer/Definition for back of flashcard 1."
        }},
        {{
            "front": "Question/Term for front of flashcard 2?",
            "back": "Answer/Definition for back of flashcard 2."
        }},
        {{
            "front": "Question/Term for front of flashcard 3?",
            "back": "Answer/Definition for back of flashcard 3."
        }},
        {{
            "front": "Question/Term for front of flashcard 4?",
            "back": "Answer/Definition for back of flashcard 4."
        }},
        {{
            "front": "Question/Term for front of flashcard 5?",
            "back": "Answer/Definition for back of flashcard 5."
        }}
    ],
    "revision_notes": "A comprehensive markdown list of detailed revision points (6-8 points, each with a brief explanation) summarizing key details and core concepts of the object.",
    "viva": [
        {{
            "question": "Challenging verbal question 1?",
            "answer": "A comprehensive answer suitable for a viva voce examination."
        }},
        {{
            "question": "Challenging verbal question 2?",
            "answer": "A comprehensive answer suitable for a viva voce examination."
        }},
        {{
            "question": "Challenging verbal question 3?",
            "answer": "A comprehensive answer suitable for a viva voce examination."
        }},
        {{
            "question": "Challenging verbal question 4?",
            "answer": "A comprehensive answer suitable for a viva voce examination."
        }},
        {{
            "question": "Challenging verbal question 5?",
            "answer": "A comprehensive answer suitable for a viva voce examination."
        }}
    ]
}}
"""

        try:
            # Force JSON format output from Ollama client
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json",
                options={
                    "temperature": 0.4,
                    "top_p": 0.9,
                }
            )
            
            content = response["response"].strip()
            
            # Clean markdown code fences if output returned them despite JSON format setting
            content = self._strip_code_fences(content)
            parsed_data = json.loads(content)
            
            # Validate structure and heal malformed data
            parsed_data, _ = self._validate_and_heal_educational_data(parsed_data, object_name)
            
            # Cache and save on success
            self.cache[cache_key] = parsed_data
            self._save_cache()
            return parsed_data

        except Exception as e:
            print(f"Ollama JSON generation failed: {e}. Attempting recovery block.")
            # Returns a fallback structured dictionary to prevent UI crashes in case of bad JSON formatting
            fallback = {
                "mcqs": self._generate_mcqs_separately(object_name),
                "flashcards": self._generate_flashcards_separately(object_name),
                "revision_notes": self._generate_notes_separately(object_name),
                "viva": self._generate_viva_separately(object_name),
                "full_explanation": self._generate_explanation_separately(object_name)
            }
            # Cache the fallback (which is now fully healed and complete!)
            self.cache[cache_key] = fallback
            self._save_cache()
            return fallback

    def generate_comparison_data(self, object_a: str, object_b: str) -> str:
        """
        Compares two objects and outputs a detailed Markdown report.
        
        Args:
            object_a (str): First object name.
            object_b (str): Second object name.
            
        Returns:
            str: Markdown formatted comparison report.
        """
        cache_key = self._get_cache_key("compare", f"{object_a}:{object_b}")
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.check_connection():
            raise OllamaConnectionError(
                "Ollama is offline. Please make sure the Ollama application is running."
            )

        prompt = f"""You are a scientific comparator and subject matter expert.
Create a comprehensive educational comparison between the two objects: "{object_a}" and "{object_b}".

Please format your response using EXACTLY the following structure with the exact headers. 
Do not write any introductory or conversational text. Begin directly with the headers.

## Comparison Table
Provide a detailed markdown-formatted table comparing key features (at least 8 rows comparing size, materials, energy, functions, lifetime, environmental impact, cost, and historical context).

## Similarities
Provide a bulleted list of 4-5 detailed common traits or shared characteristics with brief explanations.

## Differences
Provide a bulleted list of 4-5 detailed differences or opposing features with brief explanations.

## Educational Insights
A comprehensive educational essay (200-300 words) explaining why these two items are compared, their relative evolutionary or design advancements, and their ecological/societal impact.
"""

        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.4,
                    "top_p": 0.9,
                }
            )
            text_result = response["response"].strip()
            self.cache[cache_key] = text_result
            self._save_cache()
            return text_result
        except Exception as e:
            raise Exception(f"Local LLM comparison failed: {str(e)}")

    def generate_document_analysis(self, text: str) -> str:
        """
        Generates document summaries, terms, and questions from text OCR results.
        
        Args:
            text (str): Raw extracted document text.
            
        Returns:
            str: Markdown structured study guide.
        """
        cache_key = self._get_cache_key("ocr", text)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.check_connection():
            raise OllamaConnectionError(
                "Ollama is offline. Please make sure the Ollama application is running."
            )

        prompt = f"""You are a document understanding and educational assistant.
Analyze the following extracted text from a document and generate a structured educational study guide.

Please format your response using EXACTLY the following structure with the exact headers. 
Do not write any introductory or conversational text. Begin directly with the headers.

## Summary
Provide a comprehensive, high-level summary (2 paragraphs) of the main topic, context, and purpose of the text.

## Key Points
Provide a detailed list of the 8 most important facts, concepts, or takeaways from the text with descriptive points.

## Important Terms
Define 5-7 key technical terms, acronyms, or advanced concepts mentioned in the text as a detailed definition list (e.g. **Term**: A comprehensive definition and context).

## Interview Questions
Generate 3 professional interview questions (with detailed answers) that test comprehension of the topics in this text.

## Exam Questions
Generate 3 academic exam-style questions (with correct answers or explanations) that could be asked in a test based on this text.

Here is the text to analyze:
---
{text}
---
"""

        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            )
            text_result = response["response"].strip()
            self.cache[cache_key] = text_result
            self._save_cache()
            return text_result
        except Exception as e:
            raise Exception(f"Local LLM document analysis failed: {str(e)}")

    def _generate_viva_separately(self, object_name: str) -> list:
        prompt = f"""You are prepping a student for an oral exam about: "{object_name}".
Generate exactly 5 challenging oral questions and detailed answers.
You MUST return your response as a single valid JSON array of objects. Do not write any conversational text.
Format exactly as:
[
    {{
        "question": "Challenging verbal question 1?",
        "answer": "A comprehensive answer suitable for oral exam."
    }},
    {{
        "question": "Challenging verbal question 2?",
        "answer": "A comprehensive answer suitable for oral exam."
    }},
    {{
        "question": "Challenging verbal question 3?",
        "answer": "A comprehensive answer suitable for oral exam."
    }},
    {{
        "question": "Challenging verbal question 4?",
        "answer": "A comprehensive answer suitable for oral exam."
    }},
    {{
        "question": "Challenging verbal question 5?",
        "answer": "A comprehensive answer suitable for oral exam."
    }}
]
"""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json",
                options={"temperature": 0.4}
            )
            content = response["response"].strip()
            return json.loads(self._strip_code_fences(content))
        except Exception as e:
            print(f"Separate viva generation failed: {e}")
            return [
                {"question": f"What is the significance of {object_name} in its respective environment?", "answer": f"The {object_name} holds complex biological/technical value."},
                {"question": f"How does human interaction affect {object_name}?", "answer": f"Human interactions can positively or negatively affect {object_name} depending on conservation and use."},
                {"question": f"What is the history/origin of {object_name}?", "answer": f"The origins date back historically, playing a key role in taxonomy/scientific design."},
                {"question": f"Can you describe structural/functional features of {object_name}?", "answer": f"It displays specialized functional structures that help in survival or primary execution."},
                {"question": f"What are primary research topics regarding {object_name}?", "answer": f"Scientific research focusing on sustainability, design improvements, and environmental compatibility."}
            ]

    def _generate_mcqs_separately(self, object_name: str) -> list:
        prompt = f"""Generate exactly 5 multiple choice questions about: "{object_name}".
You MUST return your response as a single valid JSON array of objects. Do not write any conversational text.
Format exactly as:
[
    {{
        "question": "Clear multiple choice question 1?",
        "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
        "answer": "A"
    }},
    {{
        "question": "Clear multiple choice question 2?",
        "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
        "answer": "B"
    }},
    {{
        "question": "Clear multiple choice question 3?",
        "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
        "answer": "C"
    }},
    {{
        "question": "Clear multiple choice question 4?",
        "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
        "answer": "D"
    }},
    {{
        "question": "Clear multiple choice question 5?",
        "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
        "answer": "A"
    }}
]
"""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json",
                options={"temperature": 0.4}
            )
            content = response["response"].strip()
            return json.loads(self._strip_code_fences(content))
        except Exception:
            return [
                {
                    "question": f"What is the main classification of a {object_name}?",
                    "options": ["A. Natural Object", "B. Technical Device", "C. Domestic Tool", "D. Dynamic Entity"],
                    "answer": "A"
                }
            ]

    def _generate_flashcards_separately(self, object_name: str) -> list:
        prompt = f"""Generate exactly 5 flashcards about: "{object_name}".
You MUST return your response as a single valid JSON array of objects. Do not write any conversational text.
Format exactly as:
[
    {{
        "front": "Question/Term for front of flashcard 1?",
        "back": "Answer/Definition for back of flashcard 1."
    }},
    {{
        "front": "Question/Term for front of flashcard 2?",
        "back": "Answer/Definition for back of flashcard 2."
    }},
    {{
        "front": "Question/Term for front of flashcard 3?",
        "back": "Answer/Definition for back of flashcard 3."
    }},
    {{
        "front": "Question/Term for front of flashcard 4?",
        "back": "Answer/Definition for back of flashcard 4."
    }},
    {{
        "front": "Question/Term for front of flashcard 5?",
        "back": "Answer/Definition for back of flashcard 5."
    }}
]
"""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json",
                options={"temperature": 0.4}
            )
            content = response["response"].strip()
            return json.loads(self._strip_code_fences(content))
        except Exception:
            return [
                {
                    "front": f"What is a {object_name}?",
                    "back": "Details could not be parsed. Please check if Ollama is running correctly."
                }
            ]

    def _generate_notes_separately(self, object_name: str) -> str:
        prompt = f"""Generate a concise markdown bulleted list of revision points (4-5 points) summarizing key details of: "{object_name}". Do not write any other text."""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={"temperature": 0.4}
            )
            return response["response"].strip()
        except Exception:
            return f"* **{object_name}**: Revision notes could not be generated."

    def _generate_explanation_separately(self, object_name: str) -> str:
        prompt = f"""Generate a detailed, comprehensive educational markdown explanation (200-300 words) explaining the concept/object: "{object_name}". Detail its background, core principles, and real-world significance. Do not write any conversational text."""
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={"temperature": 0.4}
            )
            return response["response"].strip()
        except Exception:
            return f"### {object_name}\n\nA detailed explanation could not be compiled at this time. Please make sure Ollama is active."

    def _validate_and_heal_educational_data(self, data: dict, object_name: str) -> tuple[dict, bool]:
        """
        Validates the structure of the generated or cached educational data and heals
        any missing, incorrect type, or malformed sections.
        """
        if not isinstance(data, dict):
            data = {}
        
        healed = False

        # Validate full_explanation
        if "full_explanation" not in data or not isinstance(data["full_explanation"], str) or not data["full_explanation"].strip():
            print(f"VisionAI: 'full_explanation' section is missing or malformed for '{object_name}'. Healing...")
            data["full_explanation"] = self._generate_explanation_separately(object_name)
            healed = True

        # Validate mcqs
        mcqs_valid = True
        if "mcqs" not in data or not isinstance(data["mcqs"], list) or not data["mcqs"]:
            mcqs_valid = False
        else:
            for item in data["mcqs"]:
                if not isinstance(item, dict) or "question" not in item or "options" not in item or "answer" not in item or not isinstance(item["options"], list):
                    mcqs_valid = False
                    break
        if not mcqs_valid:
            print(f"VisionAI: 'mcqs' section is missing or malformed for '{object_name}'. Healing...")
            data["mcqs"] = self._generate_mcqs_separately(object_name)
            healed = True

        # Validate flashcards
        fc_valid = True
        if "flashcards" not in data or not isinstance(data["flashcards"], list) or not data["flashcards"]:
            fc_valid = False
        else:
            for item in data["flashcards"]:
                if not isinstance(item, dict) or "front" not in item or "back" not in item:
                    fc_valid = False
                    break
        if not fc_valid:
            print(f"VisionAI: 'flashcards' section is missing or malformed for '{object_name}'. Healing...")
            data["flashcards"] = self._generate_flashcards_separately(object_name)
            healed = True

        # Validate revision_notes
        if "revision_notes" not in data or not isinstance(data["revision_notes"], str) or not data["revision_notes"].strip():
            print(f"VisionAI: 'revision_notes' section is missing or malformed for '{object_name}'. Healing...")
            data["revision_notes"] = self._generate_notes_separately(object_name)
            healed = True

        # Validate viva
        viva_valid = True
        if "viva" not in data or not isinstance(data["viva"], list) or not data["viva"]:
            viva_valid = False
        else:
            for item in data["viva"]:
                if not isinstance(item, dict) or "question" not in item or "answer" not in item:
                    viva_valid = False
                    break
        if not viva_valid:
            print(f"VisionAI: 'viva' section is missing or malformed for '{object_name}'. Healing...")
            data["viva"] = self._generate_viva_separately(object_name)
            healed = True

        return data, healed
