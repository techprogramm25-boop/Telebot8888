import sys
import os

# Asosiy papkani yo'lga qo'shish
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel serverless funksiyasi uchun handler
handler = app
