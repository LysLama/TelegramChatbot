import google.generativeai as genai

genai.configure(api_key="AIzaSyC44sYMJMpftQSjIP2HoZ-x2RYBAsmc-Ig") #replace with your api key.

for model in genai.list_models():
    print(model)