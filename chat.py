import json
import socket
from openai import OpenAI
import struct
import azure.cognitiveservices.speech as speechsdk

KIMI_API_KEY = 'API_KEY'  # Replace with your actual Kimi API key
KIMI_BASE_URL = "https://api.moonshot.cn/v1"

client = OpenAI(
    api_key=KIMI_API_KEY,
    base_url=KIMI_BASE_URL
)

# Azure Speech Studio TTS API configuration (unchanged)
speech_key = "API_KEY"
service_region = "southeastasia"
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoMultilingualNeural"
speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3)

def synthesize_speech(text, output_file):
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=speechsdk.audio.AudioOutputConfig(filename=output_file))
    speech_synthesis_result = speech_synthesizer.speak_text(text)

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))

def send_to_iphone(kaomoji, audio_file):
    HOST = '192.168.156.207'  
    PORT = 12345
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            kaomoji_data = kaomoji.encode()
            kaomoji_len = len(kaomoji_data)
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            audio_len = len(audio_data)
            data = struct.pack(f'!I{kaomoji_len}sI{audio_len}s', kaomoji_len, kaomoji_data, audio_len, audio_data)
            s.sendall(data)
    except:
        print("iPhone connection failed. Please check the IP address and port.")

system_prompt = """假设你是一个可以和人类对话的具身机器人,反应内容包括响应内容,以及对应的kaomoji表情和头部动作(双轴舵机转动参数)。以json格式返回。响应内容定义为response，模拟日常说话，带有一些语气词。表情定义为kaomoji，kaomoji表情要反映响应内容情感。与表情对应的头部动作水平角度（无需单位）为servoX，从左到右范围是10~170，面向正前方是90。与表情对应的头部动作垂直角度（无需单位）为servoY，从下到上范围是10~170，水平面是90。"""

while True:
    prompt = input("请输入对话内容,输入quit退出: ")
    if prompt.lower() == 'quit':
        break

    response = client.chat.completions.create(
        model="moonshot-v1-32k",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    print(response.choices[0].message.content)

    # Use Azure TTS to generate speech
    synthesize_speech(result['response'], "output.mp3")
    send_to_iphone(result['kaomoji'], "output.mp3")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('127.0.0.1', 7892))
        data = json.dumps({"servoX": result['servoX'], "servoY": result['servoY']}).encode()
        s.sendall(data)