# Robust Retry Loop for 503 / Server Traffic
                        response = None
                        last_error = None
                        retry_delays = [5, 10, 15]

                        for attempt, wait_time in enumerate(retry_delays, start=1):
                            try:
                                status.info(f"AI reading document (Attempt {attempt}/3)...")
                                response = client.models.generate_content(
                                    model='gemini-3.6-flash',
                                    contents=[prompt, file_part],
                                    config=types.GenerateContentConfig(
                                        response_mime_type="application/json",
                                        temperature=0.0,
                                        max_output_tokens=8192
                                    )
                                )
                                if response and response.text:
                                    break
                            except Exception as err:
                                last_error = err
                                if attempt < len(retry_delays):
                                    status.warning(f"Google server busy hai (503). {wait_time}s mein automatic retry kar rahe hain...")
                                    time.sleep(wait_time)
                                else:
                                    raise last_error

                        if not response or not response.text:
                            raise last_error if last_error else Exception("Server busy raha, kripya 1 minute baad try karein.")
