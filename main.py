import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import cohere
from gtts import gTTS
import pygame
import io
from RealtimeSTT import AudioToTextRecorder
from multiprocessing import freeze_support
import sounddevice as sd
import os
import json
from datetime import datetime
import logging

class ArabicVoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arabic Voice Assistant - صالح")
        self.root.geometry("700x550")
        self.root.configure(bg="#f0f0f0")
        self.root.iconbitmap(self.resource_path("icon.ico")) if os.path.exists(self.resource_path("icon.ico")) else None
        
        # Set up logging
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize Cohere client
        self.co = cohere.Client(self.config.get('cohere_api_key', 'tHiVKkzc86vTQ6CdMHkMpuXSf87yILUWCmuZsmLm'))
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Initialize variables
        self.recorder = None
        self.is_listening = False
        self.conversation_history = []
        self.audio_devices = []
        
        # Set up the GUI components
        self.setup_ui()
        
        # Display available audio devices
        self.update_text("الأجهزة الصوتية المتاحة:")
        try:
            devices = sd.query_devices()
            self.audio_devices = devices
            for i, device in enumerate(devices):
                self.update_text(f"{i}: {device['name']}")
                # Add to combobox
                self.device_combobox['values'] = (*self.device_combobox['values'], f"{i}: {device['name']}")
            
            # Select default device
            default_device = sd.default.device[0]
            self.device_combobox.current(default_device)
            
            self.update_text(f"\nتم اختيار الجهاز: {devices[default_device]['name']}")
        except Exception as e:
            self.logger.error(f"Error querying audio devices: {e}")
            self.update_text(f"خطأ في قراءة الأجهزة الصوتية: {e}")
        
        self.update_text("جاري تهيئة نظام التعرف على الكلام...")
        
        # Initialize the recorder in a separate thread to avoid blocking the GUI
        threading.Thread(target=self.initialize_recorder, daemon=True).start()
    
    def setup_logging(self):
        """Set up logging configuration"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, f"assistant_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ArabicAssistant')
        self.logger.info("Logging initialized")
    
    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    
    def load_config(self):
        """Load configuration from config.json file"""
        config_path = self.resource_path("config.json")
        default_config = {
            "cohere_api_key": "tHiVKkzc86vTQ6CdMHkMpuXSf87yILUWCmuZsmLm",
            "speech_model": "small",
            "silero_sensitivity": 0.4,
            "webrtc_sensitivity": 2,
            "post_speech_silence_duration": 0.7,
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}  # Merge with defaults
            else:
                # Create default config file
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
        
        return default_config

    def initialize_recorder(self):
        """Initialize RealtimeSTT recorder"""
        try:
            self.recorder = AudioToTextRecorder(
                model=self.config.get("speech_model", "small"),
                spinner=False,
                use_microphone=True,
                silero_sensitivity=self.config.get("silero_sensitivity", 0.4),
                webrtc_sensitivity=self.config.get("webrtc_sensitivity", 2),
                post_speech_silence_duration=self.config.get("post_speech_silence_duration", 0.7),
                min_length_of_recording=0.5,
                min_gap_between_recordings=0,
                enable_realtime_transcription=False,
                realtime_processing_pause=0.2,
                realtime_model_type='tiny',
                language="ar"  # Set language to Arabic
            )
            self.root.after(0, lambda: self.update_status("النظام جاهز للاستخدام!", "green"))
            self.root.after(0, lambda: self.update_text("صالح: أهلاً وسهلاً! أنا صالح، كيف يمكنني مساعدتك اليوم؟"))
            self.root.after(0, lambda: self.speak("أهلاً وسهلاً! أنا صالح، كيف يمكنني مساعدتك اليوم؟"))
            
            self.logger.info("Recorder initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing recorder: {e}")
            self.root.after(0, lambda: self.update_status(f"خطأ في تهيئة نظام التعرف: {e}", "red"))
    
    def setup_ui(self):
        """Set up the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title label with icon
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=5)
        
        title_label = ttk.Label(title_frame, text="المساعد الصوتي العربي - صالح", 
                              font=("Arial", 18, "bold"))
        title_label.pack(side=tk.TOP)
        
        # Response text area with proper Arabic text direction (right to left)
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.response_text = scrolledtext.ScrolledText(text_frame, width=60, height=15, 
                                                     font=("Arial", 12), wrap=tk.WORD)
        self.response_text.pack(fill=tk.BOTH, expand=True)
        self.response_text.tag_configure("user", foreground="blue")
        self.response_text.tag_configure("assistant", foreground="green")
        self.response_text.tag_configure("system", foreground="gray")
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="جاري التهيئة...",
                                   font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress bar for visual feedback
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=200)
        self.progress.pack(side=tk.RIGHT, padx=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="إعدادات")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Device selection
        device_frame = ttk.Frame(settings_frame)
        device_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(device_frame, text="جهاز الإدخال:").pack(side=tk.LEFT, padx=5)
        
        self.device_combobox = ttk.Combobox(device_frame, width=40, state="readonly")
        self.device_combobox.pack(side=tk.LEFT, padx=5)
        self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)
        
        # Volume slider
        volume_frame = ttk.Frame(settings_frame)
        volume_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(volume_frame, text="مستوى الصوت:").pack(side=tk.LEFT, padx=5)
        
        self.volume_scale = ttk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL)
        self.volume_scale.set(70)  # Default volume at 70%
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.volume_scale.configure(command=self.set_volume)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Start listening button with icon
        self.listen_button = ttk.Button(button_frame, text="بدء الاستماع", 
                                     command=self.toggle_listening,
                                     width=20)
        self.listen_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        self.clear_button = ttk.Button(button_frame, text="مسح المحادثة", 
                               command=self.clear_text,
                               width=15)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Save conversation button
        self.save_button = ttk.Button(button_frame, text="حفظ المحادثة", 
                               command=self.save_conversation,
                               width=15)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        self.exit_button = ttk.Button(button_frame, text="خروج", 
                               command=self.exit_application,
                               width=10)
        self.exit_button.pack(side=tk.RIGHT, padx=5)
    
    def on_device_selected(self, event):
        """Handle device selection"""
        selected = self.device_combobox.get()
        if selected:
            device_id = int(selected.split(':')[0])
            try:
                # Update the default device
                sd.default.device = (device_id, sd.default.device[1])
                self.update_status(f"تم اختيار الجهاز: {self.audio_devices[device_id]['name']}", "green")
                
                # Reinitialize recorder with new device
                self.recorder = None
                threading.Thread(target=self.initialize_recorder, daemon=True).start()
            except Exception as e:
                self.logger.error(f"Error setting audio device: {e}")
                self.update_status(f"خطأ في تعيين جهاز الإدخال: {e}", "red")
    
    def set_volume(self, val):
        """Set the playback volume"""
        volume = float(val) / 100.0
        pygame.mixer.music.set_volume(volume)
    
    def update_text(self, message, tag=None):
        """Update the response text area with the given message"""
        self.response_text.config(state=tk.NORMAL)
        if tag:
            self.response_text.insert(tk.END, message + "\n", tag)
        else:
            if message.startswith("صالح:"):
                self.response_text.insert(tk.END, message + "\n", "assistant")
            elif message.startswith("أنت:"):
                self.response_text.insert(tk.END, message + "\n", "user")
            else:
                self.response_text.insert(tk.END, message + "\n", "system")
        self.response_text.see(tk.END)
        self.response_text.config(state=tk.DISABLED)
    
    def update_status(self, message, color="green"):
        """Update the status label with the given message and color"""
        self.status_label.config(text=message, foreground=color)
        
        # Log status changes
        self.logger.info(f"Status update: {message}")
        
        if color == "blue" or color == "purple":
            self.progress.start()
        else:
            self.progress.stop()
    
    def clear_text(self):
        """Clear the response text area"""
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete(1.0, tk.END)
        self.response_text.config(state=tk.DISABLED)
        self.conversation_history = []
    
    def save_conversation(self):
        """Save the current conversation to a file"""
        try:
            # Create directory if it doesn't exist
            save_dir = "conversations"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Generate filename with date and time
            filename = os.path.join(save_dir, f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.response_text.get(1.0, tk.END))
            
            self.update_status(f"تم حفظ المحادثة في: {filename}", "green")
            self.logger.info(f"Conversation saved to {filename}")
        except Exception as e:
            self.update_status(f"خطأ في حفظ المحادثة: {e}", "red")
            self.logger.error(f"Error saving conversation: {e}")
    
    def exit_application(self):
        """Safely exit the application"""
        try:
            # Stop any ongoing processes
            if self.is_listening:
                self.toggle_listening()
            
            # Clean up resources
            pygame.mixer.quit()
            
            self.logger.info("Application exiting normally")
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during exit: {e}")
            self.root.destroy()
    
    def toggle_listening(self):
        """Toggle between listening and not listening states"""
        if not self.recorder:
            self.update_status("نظام التعرف على الكلام غير جاهز بعد", "red")
            return
            
        if self.is_listening:
            self.is_listening = False
            self.listen_button.config(text="بدء الاستماع")
            self.update_status("جاهز", "green")
            self.logger.info("Stopped listening")
        else:
            self.is_listening = True
            self.listen_button.config(text="إيقاف الاستماع")
            
            # Start the listening thread
            threading.Thread(target=self.listen_and_respond, daemon=True).start()
            self.logger.info("Started listening")
    
    def speak(self, text):
        """Convert text to speech and play it immediately"""
        try:
            self.update_status("جاري نطق الرد...", "blue")
            self.logger.info("Converting text to speech")
            
            tts = gTTS(text=text, lang='ar')
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            
            # Apply volume setting
            volume = self.volume_scale.get() / 100.0
            pygame.mixer.music.set_volume(volume)
            
            pygame.mixer.music.load(mp3_fp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            self.update_status("جاهز", "green")
        except Exception as e:
            self.logger.error(f"Text-to-speech error: {e}")
            self.update_status(f"خطأ في تحويل النص إلى كلام: {e}", "red")
    
    def record_and_transcribe(self):
        """Record audio and transcribe using RealtimeSTT"""
        try:
            self.update_status("جاري الاستماع... تحدث الآن", "blue")
            self.logger.info("Recording and transcribing speech")
            
            text = self.recorder.text()
            
            if text:
                self.logger.info(f"Transcription successful: '{text}'")
                
            return text
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
            self.update_status(f"خطأ في التسجيل: {e}", "red")
            return ""
    
    def generate_response(self, prompt):
        """Generate response using Cohere's Arabic model with Chat API"""
        try:
            self.update_status("جاري توليد الرد...", "purple")
            self.logger.info(f"Generating response for prompt: '{prompt[:30]}...'")
            
            # Create chat history for context
            chat_history = []
            for entry in self.conversation_history[-6:]:  # Use last 6 exchanges for context
                if "role" in entry and "message" in entry:
                    chat_history.append({"role": entry["role"], "message": entry["message"]})
            
            response = self.co.chat(
                model="command-r7b-arabic-02-2025",
                message=prompt,
                chat_history=chat_history if chat_history else None,
                max_tokens=self.config.get("max_tokens", 200),
                temperature=self.config.get("temperature", 0.7)
            )
            
            self.logger.info(f"Response generated successfully")
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Response generation error: {e}")
            self.update_status(f"خطأ في توليد الرد: {e}", "red")
            return "عذرًا، حدث خطأ أثناء معالجة طلبك."
    
    def listen_and_respond(self):
        """Main conversation loop"""
        while self.is_listening:
            try:
                # Record and transcribe audio
                user_input = self.record_and_transcribe()
                
                if not user_input or user_input.strip() == "":
                    self.update_text("صالح: لم أسمعك بوضوح، هل يمكنك التكرار؟")
                    self.speak("لم أسمعك بوضوح، هل يمكنك التكرار؟")
                    continue
                    
                self.update_text(f"أنت: {user_input}")
                
                # Add to conversation history
                self.conversation_history.append({"role": "USER", "message": user_input})
                
                # Check for exit commands
                if any(word in user_input.lower() for word in ["وداعا", "مع السلامة", "إنهاء", "توقف", "exit"]):
                    self.update_text("صالح: وداعاً! أتمنى لك يوماً سعيداً.")
                    self.speak("وداعاً! أتمنى لك يوماً سعيداً.")
                    self.toggle_listening()  # Stop listening
                    break
                
                # Generate response with context
                system_prompt = """أنت مساعد عربي ذكي اسمه صالح. أنت لطيف، مهذب، ومفيد. 
                تجيب على أسئلة المستخدم بدقة واحترافية. إجاباتك دائماً باللغة العربية الفصحى السهلة.
                لديك معرفة واسعة وتقدم معلومات صحيحة ومفيدة.
                """
                
                prompt = f"{system_prompt}\nالمستخدم يقول: '{user_input}'"
                ai_response = self.generate_response(prompt)
                
                self.update_text(f"صالح: {ai_response}")
                
                # Add to conversation history
                self.conversation_history.append({"role": "CHATBOT", "message": ai_response})
                
                # Speak response
                self.speak(ai_response)
                
            except Exception as e:
                self.logger.error(f"Unexpected error in conversation loop: {e}")
                self.update_status(f"خطأ غير متوقع: {e}", "red")
                self.update_text(f"خطأ: {e}")
                time.sleep(1)
                
                # If error occurs, stop listening
                if self.is_listening:
                    self.toggle_listening()
                break

if __name__ == "__main__":
    freeze_support()  # Required for Windows multiprocessing
    root = tk.Tk()
    app = ArabicVoiceAssistantApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_application)
    root.mainloop()