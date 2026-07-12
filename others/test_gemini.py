import google.generativeai as genai
import os

# Reemplaza con tu API KEY real
genai.configure(api_key=os.getenv("GENAI_APIKEY"))

print("--- Modelos disponibles en tu cuenta ---")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Modelo encontrado: {m.name}")
except Exception as e:
    print(f"Ocurrió un error al listar los modelos: {e}")