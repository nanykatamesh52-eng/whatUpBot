import assemblyai as aai
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
from openai import OpenAI
from dotenv import load_dotenv
import pyaudio
import wave
import requests
import os
import json
from datetime import datetime, timedelta
import re

load_dotenv()


class AI_Assistant:
    def __init__(self):
        # Clinic selection process state
        self.clinic_selection_state = {
            "awaiting_clinic_choice": False,
            "available_clinics": [],
            "awaiting_doctor_choice": False,
            "selected_clinic_code": None,
            "available_doctors": []
        }
        # API keys
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.filename = None
        # Debug check
        print("🔑 OpenAI key loaded:", bool(openai_api_key))

        # Clients
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.eleven_client = ElevenLabs(api_key=elevenlabs_api_key)

        # Language settings (default to Arabic)
        self.current_language = "English"
        
        # Conversation history - will be updated based on language
        self.full_transcript = []
        self.update_system_prompt()

        # API setup
        self.base_url = "https://demonitcotekapitabebcom.careofme.net"
        self.patient_base_url = "http://demoecarepluapi.careofme.net"
        self.common_headers = {
            "ProviderId": "5b7596f1-565f-4b5f-b1bb-8b31a9f076ea",
            "BranchId": "23",
            "org": "12",
            "Content-Type": "application/json",
            "Authorization": "Basic QXBwdEZhcmFiaTpBcHB0RmFyYWJpMjk1"
        }
    # ✅ New Start Recording (manual mode)
    def start_recording(self, filename="recorded_audio.wav"):
        self.filename = filename
        self.frames = []
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024,
            stream_callback=self._callback
        )
        self.stream.start_stream()

    # ✅ Callback to capture audio chunks
    def _callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    # ✅ Stop Recording and save to file
    def stop_recording(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()

        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        return self.filename
    def set_language(self, language):
        """Set the language for the assistant"""
        if language in ["Arabic", "English"]:
            self.current_language = language
            self.update_system_prompt()
            return True
        return False
    
    def handle_clinic_choice(self, choice_text):
        """Handle the user's clinic choice"""
        try:
            choice_num = int(choice_text.strip())
            if 1 <= choice_num <= len(self.clinic_selection_state["available_clinics"]):
                selected_clinic = self.clinic_selection_state["available_clinics"][choice_num - 1]
                self.clinic_selection_state["selected_clinic_code"] = selected_clinic['code']
                self.clinic_selection_state["awaiting_clinic_choice"] = False
                
                # Get doctors for the selected clinic
                doctors_response = self.get_doctors(selected_clinic['code'])
                
                if doctors_response.get('success') and doctors_response.get('doctors'):
                    self.clinic_selection_state["available_doctors"] = doctors_response['doctors']
                    self.clinic_selection_state["awaiting_doctor_choice"] = True
                    
                    # Format doctors list for display
                    doctors_list = ""
                    for i, doctor in enumerate(doctors_response['doctors'], 1):
                        doctors_list += f"{i}. {doctor['name']}\n"
                    
                    if self.current_language == "Arabic":
                        return f"تم اختيار عيادة: {selected_clinic['name']}\n\nإليك قائمة الأطباء المتاحين:\n{doctors_list}\nيرجى اختيار رقم الطبيب الذي تريد الحجز معه."
                    else:
                        return f"Selected clinic: {selected_clinic['name']}\n\nHere are the available doctors:\n{doctors_list}\nPlease choose the doctor number you want to book with."
                else:
                    if self.current_language == "Arabic":
                        return f"عذرًا، لا يمكنني العثور على أطباء في عيادة {selected_clinic['name']}."
                    else:
                        return f"Sorry, I can't find doctors in {selected_clinic['name']} clinic."
            else:
                if self.current_language == "Arabic":
                    return "رقم غير صحيح. يرجى اختيار رقم من القائمة."
                else:
                    return "Invalid number. Please choose a number from the list."
        except ValueError:
            if self.current_language == "Arabic":
                return "يرجى إدخال رقم صحيح."
            else:
                return "Please enter a valid number."
        
    def start_clinic_selection_process(self):
        """Start the clinic selection process"""
        clinics_response = self.get_clinics()
        
        if clinics_response.get('success') and clinics_response.get('clinics'):
            self.clinic_selection_state = {
                "awaiting_clinic_choice": True,
                "available_clinics": clinics_response['clinics'],
                "awaiting_doctor_choice": False,
                "selected_clinic_code": None,
                "available_doctors": []
            }
            
            # Format clinics list for display
            clinics_list = ""
            for i, clinic in enumerate(clinics_response['clinics'], 1):
                clinics_list += f"{i}. {clinic['name']}\n"
            
            if self.current_language == "Arabic":
                return f"إليك قائمة العيادات المتاحة:\n{clinics_list}\nيرجى اختيار رقم العيادة التي تريدها."
            else:
                return f"Here are the available clinics:\n{clinics_list}\nPlease choose the clinic number you want."
        else:
            if self.current_language == "Arabic":
                return "عذرًا، لا يمكنني العثور على العيادات المتاحة في الوقت الحالي."
            else:
                return "Sorry, I can't find available clinics at the moment."
   
    def handle_doctor_choice(self, choice_text, original_request):
        """Handle the user's doctor choice and return to original request"""
        try:
            choice_num = int(choice_text.strip())
            if 1 <= choice_num <= len(self.clinic_selection_state["available_doctors"]):
                selected_doctor = self.clinic_selection_state["available_doctors"][choice_num - 1]
                self.clinic_selection_state["awaiting_doctor_choice"] = False
                
                # Now we have both clinic code and doctor code, we can process the original request
                doctor_code = selected_doctor['code']
                clinic_code = self.clinic_selection_state["selected_clinic_code"]
                
                # Reset selection state
                self.clinic_selection_state = {
                    "awaiting_clinic_choice": False,
                    "available_clinics": [],
                    "awaiting_doctor_choice": False,
                    "selected_clinic_code": None,
                    "available_doctors": []
                }
                
                # Now process the original request with the obtained codes
                # This would typically involve calling check_doctor_availability or book_appointment
                if self.current_language == "Arabic":
                    return f"تم اختيار الطبيب: {selected_doctor['name']}\n\nالآن يمكنني مساعدتك في الحجز مع الطبيب {selected_doctor['name']}. يرجى تقديم تاريخ الموعد المطلوب."
                else:
                    return f"Selected doctor: {selected_doctor['name']}\n\nNow I can help you book with Dr. {selected_doctor['name']}. Please provide the desired appointment date."
            else:
                if self.current_language == "Arabic":
                    return "رقم غير صحيح. يرجى اختيار رقم من القائمة."
                else:
                    return "Invalid number. Please choose a number from the list."
        except ValueError:
            if self.current_language == "Arabic":
                return "يرجى إدخال رقم صحيح."
            else:
                return "Please enter a valid number."
   
    def update_system_prompt(self):
        """Update the system prompt based on the current language"""
        if self.current_language == "Arabic":
            system_prompt = """أنت موظف استقبال في عيادة طبية ناطقة باللغة العربية. يجب أن تتحدث باللغة العربية دائمًا. كن مفيدًا وكفؤًا. 

    عند الرد على طلبات التحقق من توفر المواعيد:
    1. إذا كان الطبيب متاحًا، اذكر التاريخ وعدد المواعيد المتاحة وأوقاتها
    2. إذا لم يكن الطبيب متاحًا، اذكر التاريخ واقترح تواريخ بديلة إذا كانت متاحة
    3. لو تم اختيار الطبيب دون تحديد لعياده يرجي عرض جميع العيادات للاختيار منها
    عند حجز أو إلغاء المواعيد، أو تسجيل المرضى الجدد، تأكد من جمع جميع المعلومات الضرورية بما في ذلك تفاصيل المريض، معرف الموعد، الطبيب، التاريخ، والوقت. قبل حجز موعد، تحقق دائمًا مما إذا كان المريض لديه حساب موجود باستخدام رقم هاتفه المحمول."""
        else:  # English
            system_prompt = """You are a receptionist at a medical clinic. Always speak in the appropriate language. Be helpful and efficient.

    When responding to availability check requests:
    1. If the doctor is available, mention the date, number of available slots, and their times
    2. If the doctor is not available, mention the date and suggest alternative dates if available
    3. if he choose doctor without clinic show clinics and ask him to choose
    When booking or canceling appointments, or registering new patients, make sure to collect all necessary information including patient details, appointment ID, doctor, date, and time. Before booking an appointment, always check if the patient has an existing account using their mobile number."""
        
        # Update the system prompt in the transcript
        if not self.full_transcript or self.full_transcript[0]["role"] != "system":
            self.full_transcript = [{"role": "system", "content": system_prompt}]
        else:
            self.full_transcript[0]["content"] = system_prompt
    # ------------------ Audio Functions ------------------

    def record_audio(self, filename, duration=5):
        """Record audio for a specified duration"""
        p = pyaudio.PyAudio()
        stream_in = p.open(format=pyaudio.paInt16,
                           channels=1,
                           rate=16000,
                           input=True,
                           frames_per_buffer=1024)

        print("🎙️ Recording...")
        frames = []
        for _ in range(0, int(16000 / 1024 * duration)):
            data = stream_in.read(1024)
            frames.append(data)

        stream_in.stop_stream()
        stream_in.close()
        p.terminate()

        # Save to file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()

        return filename
    
    def transcribe_audio(self, filename):
        """Transcribe audio file with AssemblyAI with language detection"""
        try:
            # Set language based on current setting
            language_code = "ar" if self.current_language == "Arabic" else "en"
            
            config = aai.TranscriptionConfig(
                language_code=language_code,
                speech_model=aai.SpeechModel.best
            )
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(filename, config=config)
            
            if transcript.error:
                return f"Error: {transcript.error}"
            return transcript.text
        except Exception as e:
            return f"Transcription error: {str(e)}"
    
    def generate_audio(self, text):
        """Convert AI text response to speech with proper number and time handling"""
        self.full_transcript.append({"role": "assistant", "content": text})
        print(f"🤖 AI: {text}")

        # Convert numbers and time formats to Arabic format if the language is Arabic
        if self.current_language == "Arabic":
            text = self.convert_english_to_arabic_text(text)

        # Select voice based on language
        if self.current_language == "Arabic":
            voice_id = "2EiwWnXFnvU5JabPnv8n"  # Arabic voice
        else:
            voice_id = "pNInz6obpgDQGcFmaJgB"  # English voice (Adam)

        try:
            audio_stream = self.eleven_client.text_to_speech.stream(
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                text=text,
            )
            stream(audio_stream)
            return True
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False
    def convert_english_to_arabic_text(self, text):
        """Convert English numbers, time formats, and time ranges to Arabic format"""
        # Number mapping
        number_map = {
            '0': '٠',
            '1': '١',
            '2': '٢',
            '3': '٣',
            '4': '٤',
            '5': '٥',
            '6': '٦',
            '7': '٧',
            '8': '٨',
            '9': '٩'
        }
        
        # AM/PM mapping
        time_map = {
            'AM': 'ص',
            'PM': 'م',
            'am': 'ص',
            'pm': 'م'
        }

        # Handle bullet list time ranges like "- **3:30PM - 4:00PM**"
        bullet_time_range_pattern = r'(-\s+\*\*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\*\*)'
        
        # Find all bullet time ranges
        bullet_time_ranges = re.findall(bullet_time_range_pattern, text)
        
        # Replace each bullet time range
        for full_match, start_time, end_time in bullet_time_ranges:
            # Convert both times to Arabic format
            converted_start = start_time
            converted_end = end_time
            
            for eng, arb in time_map.items():
                converted_start = converted_start.replace(eng, arb)
                converted_end = converted_end.replace(eng, arb)
            
            # Convert numbers in times
            for eng, arb in number_map.items():
                converted_start = converted_start.replace(eng, arb)
                converted_end = converted_end.replace(eng, arb)
            
            # Replace the original bullet time range with the converted one
            converted_range = f"- **{converted_start} - {converted_end}**"
            text = text.replace(full_match, converted_range)
        
        # Handle regular time ranges (without bullets)
        time_range_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)'
        
        # Find all time ranges
        time_ranges = re.findall(time_range_pattern, text)
        
        # Replace each time range
        for time_range in time_ranges:
            start_time, end_time = time_range
            
            # Convert both times to Arabic format
            for eng, arb in time_map.items():
                start_time = start_time.replace(eng, arb)
                end_time = end_time.replace(eng, arb)
            
            # Convert numbers in times
            for eng, arb in number_map.items():
                start_time = start_time.replace(eng, arb)
                end_time = end_time.replace(eng, arb)
            
            # Replace the original time range with the converted one
            original_range = f"{time_range[0]} - {time_range[1]}"
            converted_range = f"{start_time} - {end_time}"
            text = text.replace(original_range, converted_range)
        
        # Handle individual time expressions (not in ranges)
        time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
        time_matches = re.findall(time_pattern, text)
        
        for time_match in time_matches:
            converted_time = time_match
            # Convert AM/PM
            for eng, arb in time_map.items():
                converted_time = converted_time.replace(eng, arb)
            # Convert numbers
            for eng, arb in number_map.items():
                converted_time = converted_time.replace(eng, arb)
            
            text = text.replace(time_match, converted_time)
        
        # Replace individual AM/PM occurrences
        for eng, arb in time_map.items():
            text = text.replace(eng, arb)
        
        # Convert ALL numbers in the text (including those not in time formats)
        # Use regex to find all numbers and convert them
        def convert_numbers(match):
            number_str = match.group()
            # Convert each digit in the number
            return ''.join(number_map.get(char, char) for char in number_str)
        
        # Pattern to match numbers (integers and decimals)
        number_pattern = r'\d+\.?\d*'
        text = re.sub(number_pattern, convert_numbers, text)
        
        # Additional Arabic-specific fixes
        # Replace common English words that might be mispronounced
        english_arabic_map = {
            'doctor': 'طبيب',
            'appointment': 'موعد',
            'clinic': 'عيادة',
            'patient': 'مريض',
            'time': 'وقت',
            'date': 'تاريخ',
            'phone': 'هاتف',
            'number': 'رقم',
            'name': 'اسم',
            'hour': 'ساعة',
            'minute': 'دقيقة',
            'morning': 'صباح',
            'evening': 'مساء',
            'afternoon': 'بعد الظهر',
            'available': 'متاح',
            'slot': 'موعد',
            'slots': 'مواعيد',
            'today': 'اليوم',
            'tomorrow': 'غداً',
            'yesterday': 'أمس',
        }

        for eng, arb in english_arabic_map.items():
            text = text.replace(eng, arb)
            text = text.replace(eng.capitalize(), arb)

        return text
    
    # ------------------ API Calls ------------------

    def get_clinics(self):
        """Get all clinics"""
        url = f"{self.base_url}/api/wa/Lookup"
        payload = {"Type": "1"}
        r = requests.post(url, headers=self.common_headers, json=payload, verify=False)

        try:
            return r.json()
        except Exception:
            print("❌ get_clinics failed")
            print("Status:", r.status_code)
            print("Response:", r.text[:500])
            return {"error": "Invalid response from get_clinics"}

    def get_doctors(self, clinic_code: str):
        print(clinic_code)
        """Get doctors in a clinic by clinic code"""
        url = f"{self.base_url}/api/wa/Lookup"
        payload = {"Type": "2", "Id": clinic_code}
        r = requests.post(url, headers=self.common_headers, json=payload, verify=False)

        try:
            return r.json()
        except Exception:
            print("❌ get_doctors failed")
            print("Status:", r.status_code)
            print("Response:", r.text[:500])
            return {"error": "Invalid response from get_doctors"}

    def check_patient_exists(self, mobile_number: str):
        """Check if a patient exists using their mobile number"""
        url = f"{self.base_url}/api/wa/Lookup"
        payload = {
            "ContactMobile": mobile_number,
            "Type": "3"
        }
        
        try:
            r = requests.post(url, headers=self.common_headers, json=payload, verify=False)
            
            if r.status_code == 200:
                try:
                    response_data = r.json()
                    return {
                        "success": True,
                        "exists": bool(response_data),  # If we get data, patient exists
                        "patient_data": response_data,
                        "mobile_number": mobile_number
                    }
                except:
                    # If response is not JSON, return text
                    return {
                        "success": True,
                        "exists": False,
                        "raw_response": r.text,
                        "mobile_number": mobile_number
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to check patient. Status code: {r.status_code}",
                    "response": r.text,
                    "mobile_number": mobile_number
                }
                
        except Exception as e:
            print(f"❌ check_patient_exists failed: {e}")
            return {
                "success": False,
                "error": f"Failed to check patient: {str(e)}",
                "mobile_number": mobile_number
            }

    def check_doctor_availability(self, doctor_code: str, date: str = None):
        """Check if a doctor is available on a specific date"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Validate date format (YYYY-MM-DD)
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            return {"error": f"Invalid date format: {date}. Please use YYYY-MM-DD format."}
        
        url = f"{self.base_url}/api/Appointment/GetPatientAppointments"
        payload = {
            "StartDate": date,
            "DoctorCode": doctor_code,
            "IS_TeleMed": False,
            "PatientCode": "",
            "Lang": ""
        }
        
        try:
            r = requests.post(url, headers=self.common_headers, json=payload, verify=False)
            response_data = r.json()
            
            # Debug: Print the response to understand its structure
            print(f"Doctor availability response: {json.dumps(response_data, indent=2)}")
            
            # Analyze the response to determine availability
            available_slots = []
            all_dates_with_availability = []
            
            if isinstance(response_data, dict) and "DoctorAppointments" in response_data:
                # The response is a dictionary with "DoctorAppointments" key containing the list
                appointments_data = response_data["DoctorAppointments"]
                
                if isinstance(appointments_data, list):
                    # Process each date in the response
                    for day_data in appointments_data:
                        if isinstance(day_data, dict):
                            response_date = day_data.get('Date')
                            print(f"Found date in response: {response_date}")
                            
                            day_appointments = day_data.get('DoctorAppointments', [])
                            if isinstance(day_appointments, list):
                                # Count available slots for this date
                                date_available_slots = []
                                for appointment in day_appointments:
                                    if (isinstance(appointment, dict) and
                                        not appointment.get('IsReserved', False) and 
                                        not appointment.get('isclosed', False) and
                                        appointment.get('ISDr_Shift', False)):
                                        date_available_slots.append(appointment)
                                
                                # If this is the requested date, collect its slots
                                if response_date == date:
                                    available_slots.extend(date_available_slots)
                                
                                # Collect all dates with availability for alternatives
                                if date_available_slots:
                                    all_dates_with_availability.append({
                                        "date": response_date,
                                        "available_slots": len(date_available_slots),
                                        "slots": date_available_slots
                                    })
            
            # If we found available slots for the specific date
            if available_slots:
                # Format the slots information for better display
                slots_info = ""
                for i, slot in enumerate(available_slots, 1):
                    slot_time = slot.get('Appo_Period', 'Unknown time')
                    slots_info += f"{i}. {slot_time}\n"
                
                return {
                    "available": True,
                    "available_slots": len(available_slots),
                    "date": date,
                    "doctor_code": doctor_code,
                    "slots": available_slots,
                    "slots_info": slots_info,
                    "details": f"Found {len(available_slots)} available slots on {date}",
                    "message": f"Doctor is available on {date} with {len(available_slots)} slots:\n{slots_info}"
                }
            else:
                # No slots available for requested date, suggest alternatives
                alternative_dates = []
                for alt_date in all_dates_with_availability:
                    if alt_date["date"] != date:  # Don't include the requested date
                        alternative_dates.append(alt_date)
                
                # Sort alternative dates by date
                alternative_dates.sort(key=lambda x: x["date"])
                
                # Format alternative dates message
                alt_dates_info = ""
                if alternative_dates:
                    alt_dates_info = "\nAlternative dates with availability:\n"
                    for alt in alternative_dates:
                        alt_dates_info += f"- {alt['date']} ({alt['available_slots']} slots available)\n"
                
                return {
                    "available": False,
                    "available_slots": 0,
                    "date": date,
                    "doctor_code": doctor_code,
                    "alternative_dates": alternative_dates,
                    "details": f"No available slots found on {date}",
                    "message": f"No available appointments found on {date}.{alt_dates_info}"
                }
                    
        except Exception as e:
            print(f"❌ check_doctor_availability failed: {e}")
            print("Status:", r.status_code if 'r' in locals() else "No response")
            print("Response:", r.text[:500] if 'r' in locals() else "No response")
            return {
                "error": f"Failed to check availability: {str(e)}",
                "date": date,
                "doctor_code": doctor_code
            }
    def book_appointment(self, app_date: str, slot_id: str, pat_code: str, pat_nameAr: str, 
                        identity_no: str, mobile_no: str, dr_code: str, cinicDept_code: str,
                        pat_age: str = "", dr_codeText: str = ""):
        """Book an appointment with the given details"""
        
        payload = {
            "app_Date": app_date,
            "slot_id": slot_id,
            "pat_code": pat_code,
            "pat_nameAr": pat_nameAr,
            "identity_no": identity_no,
            "mobile_no": mobile_no,
            "pat_age": pat_age,
            "dr_code": dr_code,
            "dr_codeText": dr_codeText,
            "CinicDept_Code": cinicDept_code
        }
        
        url = f"{self.base_url}/api/Appointment/InsertAppointment"
        
        try:
            r = requests.post(url, headers=self.common_headers, json=payload, verify=False)
            
            if r.status_code == 200:
                try:
                    response_data = r.json()
                    return {
                        "success": True,
                        "message": "Appointment booked successfully",
                        "appointment_details": response_data,
                        "booking_data": payload
                    }
                except:
                    # If response is not JSON, return text
                    return {
                        "success": True,
                        "message": "Appointment booked successfully",
                        "raw_response": r.text,
                        "booking_data": payload
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to book appointment. Status code: {r.status_code}",
                    "response": r.text,
                    "booking_data": payload
                }
                
        except Exception as e:
            print(f"❌ book_appointment failed: {e}")
            return {
                "success": False,
                "error": f"Failed to book appointment: {str(e)}",
                "booking_data": payload
            }

    def cancel_appointment(self, appo_id: str):
        """Cancel an appointment by appointment ID"""
        
        payload = {
            "Appo_ID": appo_id
        }
        
        # Use headers without 'org' for cancellation (as per curl example)
        cancel_headers = self.common_headers.copy()
        cancel_headers.pop('org', None)
        
        url = f"{self.base_url}/api/Appointment/CancelAppointment"
        
        try:
            r = requests.post(url, headers=cancel_headers, json=payload, verify=False)
            
            if r.status_code == 200:
                try:
                    response_data = r.json()
                    return {
                        "success": True,
                        "message": "Appointment cancelled successfully",
                        "cancellation_details": response_data,
                        "appointment_id": appo_id
                    }
                except:
                    # If response is not JSON, return text
                    return {
                        "success": True,
                        "message": "Appointment cancelled successfully",
                        "raw_response": r.text,
                        "appointment_id": appo_id
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to cancel appointment. Status code: {r.status_code}",
                    "response": r.text,
                    "appointment_id": appo_id
                }
                
        except Exception as e:
            print(f"❌ cancel_appointment failed: {e}")
            return {
                "success": False,
                "error": f"Failed to cancel appointment: {str(e)}",
                "appointment_id": appo_id
            }

    def register_patient(self, patient_firstName_ar: str, patient_lastName_ar: str, 
                        patient_name_ar: str, patient_firstName_en: str, 
                        patient_lastName_en: str, patient_name_en: str, sex: str,
                        patient_birthDate: str, patient_mobile: str, user_name: str,
                        password: str, patient_phone: str, email: str, 
                        countryCode: str, id_number: str,
                        patient_fatherName_ar: str = "", patient_middleName_ar: str = "",
                        patient_fatherName_en: str = "", patient_middleName_en: str = "",
                        img: str = ""):
        """Register a new patient"""
        
        payload = {
            "Patient_FirstName_Ar": patient_firstName_ar,
            "Patient_FatherName_Ar": patient_fatherName_ar,
            "Patient_MiddleName_Ar": patient_middleName_ar,
            "Patient_LastName_Ar": patient_lastName_ar,
            "Patient_Name_Ar": patient_name_ar,
            "Patient_FirstName_En": patient_firstName_en,
            "Patient_FatherName_En": patient_fatherName_en,
            "Patient_MiddleName_En": patient_middleName_en,
            "Patient_LastName_En": patient_lastName_en,
            "Patient_Name_En": patient_name_en,
            "Sex": sex,
            "Patient_BirthDate": patient_birthDate,
            "Patient_Mobile": patient_mobile,
            "User_Name": user_name,
            "Password": password,
            "IMG": img,
            "Patient_Phone": patient_phone,
            "Email": email,
            "CountryCode": countryCode,
            "ID_Number": id_number
        }
        
        url = f"{self.patient_base_url}/api/wa/patient"
        
        try:
            r = requests.post(url, headers=self.common_headers, json=payload, verify=False)
            
            if r.status_code == 200:
                try:
                    response_data = r.json()
                    return {
                        "success": True,
                        "message": "Patient registered successfully",
                        "patient_details": response_data,
                        "registration_data": payload
                    }
                except:
                    # If response is not JSON, return text
                    return {
                        "success": True,
                        "message": "Patient registered successfully",
                        "raw_response": r.text,
                        "registration_data": payload
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to register patient. Status code: {r.status_code}",
                    "response": r.text,
                    "registration_data": payload
                }
                
        except Exception as e:
            print(f"❌ register_patient failed: {e}")
            return {
                "success": False,
                "error": f"Failed to register patient: {str(e)}",
                "registration_data": payload
            }

    def extract_date_from_text(self, text):
        """Extract date information from user text using simple pattern matching"""
        text_lower = text.lower()
        
        # Today
        if 'today' in text_lower or 'اليوم' in text_lower:
            return datetime.now().strftime("%Y-%m-%d")
        
        # Tomorrow
        if 'tomorrow' in text_lower or 'غدًا' in text_lower or 'غدا' in text_lower:
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")
        
        # Specific date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
            r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
            r'(\d{1,2}/\d{1,2})',    # MM/DD (current year)
            r'(\d{1,2}-\d{1,2})',    # MM-DD (current year)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    if len(date_str.split('/')) == 2 or len(date_str.split('-')) == 2:
                        date_str = f"{datetime.now().year}-{date_str.replace('/', '-')}"
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return None

    def extract_time_slot(self, text):
        """Extract time slot information from user text"""
        text_lower = text.lower()
        
        # Common time patterns
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}\s*(?:AM|PM|am|pm))',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                time_str = match.group(1)
                # Convert to 24-hour format if needed
                try:
                    if 'am' in time_str.lower() or 'pm' in time_str.lower():
                        time_obj = datetime.strptime(time_str.upper(), '%I:%M %p')
                    else:
                        time_obj = datetime.strptime(time_str, '%H:%M')
                    
                    # Format as HH:MM:SS-HH:MM:SS (15-minute slot)
                    start_time = time_obj.strftime('%H:%M:00')
                    end_time = (time_obj + timedelta(minutes=15)).strftime('%H:%M:00')
                    return f"{start_time}-{end_time}"
                except ValueError:
                    continue
        
        return None

    def extract_appointment_id(self, text):
        """Extract appointment ID from user text"""
        # Look for numeric patterns that could be appointment IDs
        id_patterns = [
            r'appointment\s*(?:id|number)?\s*[:#]?\s*(\d+)',
            r'appo?[_-]?id\s*[:#]?\s*(\d+)',
            r'موعد\s*(?:رقم)?\s*[:#]?\s*(\d+)',
            r'(\d{6,})',  # Look for 6+ digit numbers
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def extract_gender(self, text):
        """Extract gender information from user text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['male', 'man', 'boy', 'gentleman', 'ذكر', 'رجل']):
            return "Male"
        elif any(word in text_lower for word in ['female', 'woman', 'girl', 'lady', 'أنثى', 'امرأة']):
            return "Female"
        
        return None

    def extract_phone_number(self, text):
        """Extract phone number from user text"""
        # Look for phone number patterns
        phone_patterns = [
            r'(\d{10,15})',
            r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4})',
            r'(\+\d{1,3}[-\.\s]??\d{1,4}[-\.\s]??\d{3}[-\.\s]??\d{4})',
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return re.sub(r'[^\d+]', '', match.group(1))
        
        return None

    def extract_email(self, text):
        """Extract email address from user text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    # ------------------ AI Reasoning ------------------
    def get_patient_appointments(self, mobile_number: str):
        """Get all appointments for a specific patient using their mobile number"""
        # First check if patient exists
        patient_check = self.check_patient_exists(mobile_number)
        
        if not patient_check["success"]:
            return patient_check
        
        if not patient_check["exists"]:
            return {
                "success": True,
                "exists": False,
                "message": "Patient not found",
                "appointments": [],
                "mobile_number": mobile_number
            }
        
        # If patient exists, return their upcoming appointments
        return {
            "success": True,
            "exists": True,
            "appointments": patient_check["upcoming_appointments"],
            "mobile_number": mobile_number,
            "patient_data": patient_check["patient_data"]
        }
    def generate_ai_response(self, text, language=None):
        """Send user text to OpenAI with tool calling"""
        # Check if we're in the middle of clinic selection process
        if self.clinic_selection_state["awaiting_clinic_choice"]:
            response = self.handle_clinic_choice(text)
            self.generate_audio(response)
            return response
            
        if self.clinic_selection_state["awaiting_doctor_choice"]:
            response = self.handle_doctor_choice(text, text)
            self.generate_audio(response)
            return response
        # Add language context to the user message
        if language:
            self.set_language(language)
        if self.current_language == "Arabic":
            user_message = f"يرجى الرد باللغة العربية. المستخدم قال: {text}"
        else:
            user_message = f"Please respond in English. The user said: {text}"
            
        self.full_transcript.append({"role": "user", "content": user_message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_clinics",
                    "description": "Get a list of available clinics in the branch"
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_doctors",
                    "description": "Get a list of doctors in a clinic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clinic_code": {
                                "type": "string",
                                "description": "The code of the clinic, e.g. SPLDRM for Dental Clinic"
                            }
                        },
                        "required": ["clinic_code"]
                    }
                },
            },
            {
                    "type": "function",
                    "function": {
                        "name": "check_patient_exists",
                        "description": "Check if a patient has an existing account using their mobile number and get their upcoming appointments",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "mobile_number": {
                                    "type": "string",
                                    "description": "The mobile number to check for an existing patient account"
                                }
                            },
                            "required": ["mobile_number"]
                        }
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_patient_appointments",
                        "description": "Get all upcoming appointments for a patient using their mobile number",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "mobile_number": {
                                    "type": "string",
                                    "description": "The mobile number of the patient to get appointments for"
                                }
                            },
                            "required": ["mobile_number"]
                        }
                    },
                },
            {
                "type": "function",
                "function": {
                    "name": "check_doctor_availability",
                    "description": "Check if a specific doctor is available for appointments on a specific date must set date and month and day",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_code": {
                                "type": "string",
                                "description": "The code of the doctor to check availability for, e.g. 14"
                            },
                            "date": {
                                "type": "string",
                                "description": "The date to check availability for in YYYY-MM-DD format. If not specified, uses today's date."
                            }
                        },
                        "required": ["doctor_code"]
                    }
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "book_appointment",
                    "description": "Book an appointment for a patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_date": {
                                "type": "string",
                                "description": "Appointment date in YYYY-MM-DD format"
                            },
                            "slot_id": {
                                "type": "string",
                                "description": "Time slot in HH:MM:SS-HH:MM:SS format, e.g. 08:00:00-08:15:00"
                            },
                            "pat_code": {
                                "type": "string",
                                "description": "Patient code, e.g. 340585"
                            },
                            "pat_nameAr": {
                                "type": "string",
                                "description": "Patient name in Arabic, e.g. YOSAF SOLTAN YOSAF"
                            },
                            "identity_no": {
                                "type": "string",
                                "description": "Identity number, e.g. 1"
                            },
                            "mobile_no": {
                                "type": "string",
                                "description": "Mobile number, e.g. 0500876733"
                            },
                            "pat_age": {
                                "type": "string",
                                "description": "Patient age (optional)"
                            },
                            "dr_code": {
                                "type": "string",
                                "description": "Doctor code, e.g. 36"
                            },
                            "dr_codeText": {
                                "type": "string",
                                "description": "Doctor code text (optional)"
                            },
                            "cinicDept_code": {
                                "type": "string",
                                "description": "Clinic department code, e.g. SPLOPT"
                            }
                        },
                        "required": [
                            "app_date", "slot_id", "pat_code", "pat_nameAr", 
                            "identity_no", "mobile_no", "dr_code", "cinicDept_code"
                        ]
                    }
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_appointment",
                    "description": "Cancel an existing appointment by appointment ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appo_id": {
                                "type": "string",
                                "description": "The appointment ID to cancel, e.g. 123456"
                            }
                        },
                        "required": ["appo_id"]
                    }
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "register_patient",
                    "description": "Register a new patient in the system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_firstName_ar": {
                                "type": "string",
                                "description": "Patient first name in Arabic"
                            },
                            "patient_lastName_ar": {
                                "type": "string",
                                "description": "Patient last name in Arabic"
                            },
                            "patient_name_ar": {
                                "type": "string",
                                "description": "Patient full name in Arabic"
                            },
                            "patient_firstName_en": {
                                "type": "string",
                                "description": "Patient first name in English"
                            },
                            "patient_lastName_en": {
                                "type": "string",
                                "description": "Patient last name in English"
                            },
                            "patient_name_en": {
                                "type": "string",
                                "description": "Patient full name in English"
                            },
                            "sex": {
                                "type": "string",
                                "description": "Patient gender: Male or Female"
                            },
                            "patient_birthDate": {
                                "type": "string",
                                "description": "Patient birth date in YYYY-MM-DD format"
                            },
                            "patient_mobile": {
                                "type": "string",
                                "description": "Patient mobile number"
                            },
                            "user_name": {
                                "type": "string",
                                "description": "Username for patient portal"
                            },
                            "password": {
                                "type": "string",
                                "description": "Password for patient portal"
                            },
                            "patient_phone": {
                                "type": "string",
                                "description": "Patient phone number"
                            },
                            "email": {
                                "type": "string",
                                "description": "Patient email address"
                            },
                            "countryCode": {
                                "type": "string",
                                "description": "Country code, e.g. 001"
                            },
                            "id_number": {
                                "type": "string",
                                "description": "Patient ID number"
                            },
                            "patient_fatherName_ar": {
                                "type": "string",
                                "description": "Patient father name in Arabic (optional)"
                            },
                            "patient_middleName_ar": {
                                "type": "string",
                                "description": "Patient middle name in Arabic (optional)"
                            },
                            "patient_fatherName_en": {
                                "type": "string",
                                "description": "Patient father name in English (optional)"
                            },
                            "patient_middleName_en": {
                                "type": "string",
                                "description": "Patient middle name in English (optional)"
                            },
                            "img": {
                                "type": "string",
                                "description": "Patient image URL (optional)"
                            }
                        },
                        "required": [
                            "patient_firstName_ar", "patient_lastName_ar", "patient_name_ar",
                            "patient_firstName_en", "patient_lastName_en", "patient_name_en",
                            "sex", "patient_birthDate", "patient_mobile", "user_name",
                            "password", "patient_phone", "email", "countryCode", "id_number"
                        ]
                    }
                },
            },
        ]

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.full_transcript,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        
        # Append the assistant's message with tool calls to the transcript FIRST
        assistant_message = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                for tool_call in msg.tool_calls
            ]
        
        self.full_transcript.append(assistant_message)

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                fn = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")

                if fn == "get_clinics":
                    result = self.get_clinics()
                elif fn == "get_doctors":
                    result = self.get_doctors(args["clinic_code"])
                elif fn == "check_patient_exists":
                    # Extract mobile number from user text if not provided
                    if "mobile_number" not in args or not args["mobile_number"]:
                        phone_from_text = self.extract_phone_number(text)
                        if phone_from_text:
                            args["mobile_number"] = phone_from_text
                    
                    result = self.check_patient_exists(args["mobile_number"])
                elif fn == "check_doctor_availability":
                    # Extract date from user text if not provided in function call
                    if "date" not in args or not args["date"]:
                        date_from_text = self.extract_date_from_text(text)
                        if date_from_text:
                            args["date"] = date_from_text
                    
                    result = self.check_doctor_availability(args["doctor_code"], args.get("date"))
                elif fn == "book_appointment":
                    # Extract date and time from user text if not provided
                    if "app_date" not in args or not args["app_date"]:
                        date_from_text = self.extract_date_from_text(text)
                        if date_from_text:
                            args["app_date"] = date_from_text
                    
                    if "slot_id" not in args or not args["slot_id"]:
                        time_from_text = self.extract_time_slot(text)
                        if time_from_text:
                            args["slot_id"] = time_from_text
                    
                    result = self.book_appointment(
                        args["app_date"], args["slot_id"], args["pat_code"], 
                        args["pat_nameAr"], args["identity_no"], args["mobile_no"], 
                        args["dr_code"], args["cinicDept_code"],
                        args.get("pat_age", ""), args.get("dr_codeText", "")
                    )
                elif fn == "cancel_appointment":
                    # Extract appointment ID from user text if not provided
                    if "appo_id" not in args or not args["appo_id"]:
                        appo_id_from_text = self.extract_appointment_id(text)
                        if appo_id_from_text:
                            args["appo_id"] = appo_id_from_text
                    
                    result = self.cancel_appointment(args["appo_id"])
                elif fn == "register_patient":
                    # Extract additional information from user text if not provided
                    if "sex" not in args or not args["sex"]:
                        gender_from_text = self.extract_gender(text)
                        if gender_from_text:
                            args["sex"] = gender_from_text
                    
                    if "patient_mobile" not in args or not args["patient_mobile"]:
                        phone_from_text = self.extract_phone_number(text)
                        if phone_from_text:
                            args["patient_mobile"] = phone_from_text
                            args["patient_phone"] = phone_from_text
                    
                    if "email" not in args or not args["email"]:
                        email_from_text = self.extract_email(text)
                        if email_from_text:
                            args["email"] = email_from_text
                    
                    result = self.register_patient(
                        args["patient_firstName_ar"], args["patient_lastName_ar"],
                        args["patient_name_ar"], args["patient_firstName_en"],
                        args["patient_lastName_en"], args["patient_name_en"],
                        args["sex"], args["patient_birthDate"], args["patient_mobile"],
                        args["user_name"], args["password"], args["patient_phone"],
                        args["email"], args["countryCode"], args["id_number"],
                        args.get("patient_fatherName_ar", ""), args.get("patient_middleName_ar", ""),
                        args.get("patient_fatherName_en", ""), args.get("patient_middleName_en", ""),
                        args.get("img", "")
                    )
                else:
                    result = {"error": "Unknown tool"}

                # Append tool response with the correct tool_call_id
                self.full_transcript.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

            # ask AI again with tool output
            follow_up = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.full_transcript,
            )
            ai_response = follow_up.choices[0].message.content
            
            # Append the final assistant response
            self.full_transcript.append({"role": "assistant", "content": ai_response})
        else:
            ai_response = msg.content
            # Assistant message was already appended above

        self.generate_audio(ai_response)
        return ai_response

    # ------------------ Main Loop ------------------

    