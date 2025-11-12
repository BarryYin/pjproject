

import dashscope
from dashscope.audio.tts import SpeechSynthesizer

# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
dashscope.api_key = "sk-ebf86b67058945fa827863a3742df0b0"
result = SpeechSynthesizer.call(model='sambert-indah-v1',
                                # 当text内容的语种发生变化时，请确认model是否匹配。不同model支持不同的语种，详情请参见Sambert音色列表中的“语言”列。
                                text='Mohon maaf atas kendala. Jika ada penagihan tidak sesuai',
                                sample_rate=48000,
                                format='wav')
print('requestId: ', result.get_response()['request_id'])
if result.get_audio_data() is not None:
    with open('output.wav', 'wb') as f:
        f.write(result.get_audio_data())
print(' get response: %s' % (result.get_response()))
